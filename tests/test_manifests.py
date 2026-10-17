"""Consistency checks between the app, Dockerfile and k8s manifests."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text()


def _docs(name):
    text = (ROOT / "kubernetes" / name).read_text()
    return [d for d in yaml.safe_load_all(text) if d]


def _deployment():
    docs = _docs("deployment.yaml")
    return next(d for d in docs if d["kind"] == "Deployment")


def _container_ports():
    containers = _deployment()["spec"]["template"]["spec"]["containers"]
    return {p["containerPort"] for c in containers for p in c.get("ports", [])}


def test_dockerfile_runs_as_non_root_user():
    users = re.findall(r"^USER\s+(\S+)", DOCKERFILE, re.MULTILINE)
    assert users and users[-1] not in ("root", "0")


def test_dockerfile_pip_installs_are_pinned():
    # hadolint DL3013: `pip install --upgrade pip` pulls whatever is latest.
    for line in re.findall(r"pip install[^\n&]*", DOCKERFILE):
        assert "-r " in line or "==" in line, line


def test_dockerfile_cmd_uses_exec_form():
    # hadolint DL3025: JSON form makes the shell wrapper explicit; `exec`
    # inside it keeps uvicorn as PID 1 so it receives SIGTERM.
    cmd = re.findall(r"^CMD\s+(.*)$", DOCKERFILE, re.MULTILINE)
    assert cmd and cmd[-1].startswith("[")


def test_dockerfile_port_matches_k8s_container_port():
    found = re.findall(r"^EXPOSE\s+(\d+)", DOCKERFILE, re.MULTILINE)
    exposed = {int(p) for p in found}
    default = re.search(r"PORT:-(\d+)", DOCKERFILE)
    assert default
    assert {int(default.group(1))} == exposed == _container_ports()


def test_service_targets_deployment_pods_and_port():
    dep = _deployment()
    labels = dep["spec"]["template"]["metadata"]["labels"]
    svc = next(d for d in _docs("service.yaml") if d["kind"] == "Service")
    assert svc["spec"]["selector"].items() <= labels.items()
    assert dep["spec"]["selector"]["matchLabels"].items() <= labels.items()
    targets = {p["targetPort"] for p in svc["spec"]["ports"]}
    assert targets <= _container_ports()


def test_hpa_targets_existing_deployment():
    docs = _docs("deployment.yaml")
    hpa = next(d for d in docs if d["kind"] == "HorizontalPodAutoscaler")
    ref = hpa["spec"]["scaleTargetRef"]
    assert ref["name"] == _deployment()["metadata"]["name"]
    assert hpa["spec"]["minReplicas"] <= hpa["spec"]["maxReplicas"]


def test_container_root_filesystem_is_read_only_with_writable_tmp():
    pod = _deployment()["spec"]["template"]["spec"]
    volumes = {v["name"] for v in pod.get("volumes", []) if "emptyDir" in v}
    for c in pod["containers"]:
        assert c["securityContext"].get("readOnlyRootFilesystem") is True
        mounts = {m["mountPath"]: m["name"] for m in c.get("volumeMounts", [])}
        assert mounts.get("/tmp") in volumes


def test_dependabot_covers_pip_docker_and_actions():
    cfg = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text())
    ecosystems = {u["package-ecosystem"] for u in cfg["updates"]}
    assert {"pip", "docker", "github-actions"} <= ecosystems
