from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_create_and_read_item():
    # First create an item
    new_item = {
        "name": "Test",
        "description": "For testing",
        "price": 10.0,
        "quantity": 1,
    }
    post_response = client.post("/items", json=new_item)
    assert post_response.status_code == 200
    item_id = post_response.json()["item_id"]

    # Then read the item
    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert "item" in data
    assert data["item"]["name"] == "Test"


def test_healthz_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_after_delete_does_not_overwrite_existing_item():
    # Regression: IDs were len(items_db) + 1, so after a delete the next
    # create reused the ID of a live item and silently overwrote it.
    base = {"description": "x", "price": 1.0, "quantity": 1}
    id_a = client.post("/items", json={"name": "A", **base}).json()["item_id"]
    id_b = client.post("/items", json={"name": "B", **base}).json()["item_id"]
    assert client.delete(f"/items/{id_a}").status_code == 200
    id_c = client.post("/items", json={"name": "C", **base}).json()["item_id"]
    assert id_c not in (id_a, id_b)
    assert client.get(f"/items/{id_b}").json()["item"]["name"] == "B"
    assert client.get(f"/items/{id_c}").json()["item"]["name"] == "C"


def test_description_is_optional_and_nullable():
    item = {"name": "NoDesc", "price": 2.5, "quantity": 3}
    assert client.post("/items", json=item).status_code == 200
    resp = client.post("/items", json={**item, "description": None})
    assert resp.status_code == 200


def test_k8s_probe_paths_and_ports_match_app():
    # Regression: probes hit /health (app serves /healthz) on port 8000
    # (the image listens on 8080), so pods never became Ready.
    import re
    from pathlib import Path

    manifest = (
        Path(__file__).resolve().parents[1] / "kubernetes" / "deployment.yaml"
    ).read_text()
    routes = {r.path for r in app.routes}
    paths = re.findall(r"path:\s*(\S+)", manifest)
    assert paths and all(p in routes for p in paths)
    ports = set(re.findall(r"(?:containerPort|port):\s*(\d+)", manifest))
    assert ports == {"8080"}


def _k8s_docs(name):
    from pathlib import Path

    import yaml

    path = Path(__file__).resolve().parents[1] / "kubernetes" / name
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_hpa_target_declares_cpu_requests():
    # Regression: the HPA scales on CPU utilization, which is computed against
    # resources.requests.cpu; without it the HPA reports "missing request for
    # cpu" and never scales.
    docs = _k8s_docs("deployment.yaml")
    hpa = next(d for d in docs if d["kind"] == "HorizontalPodAutoscaler")
    target = hpa["spec"]["scaleTargetRef"]["name"]
    dep = next(
        d for d in docs
        if d["kind"] == "Deployment" and d["metadata"]["name"] == target
    )
    for c in dep["spec"]["template"]["spec"]["containers"]:
        res = c.get("resources", {})
        assert res.get("requests", {}).get("cpu")
        assert res.get("limits", {}).get("memory")


def test_k8s_pod_runs_non_root_without_privilege_escalation():
    docs = _k8s_docs("deployment.yaml")
    dep = next(d for d in docs if d["kind"] == "Deployment")
    pod = dep["spec"]["template"]["spec"]
    assert pod.get("securityContext", {}).get("runAsNonRoot") is True
    for c in pod["containers"]:
        ctx = c.get("securityContext", {})
        assert ctx.get("allowPrivilegeEscalation") is False


def test_item_rejects_negative_and_oversized_values():
    ok = {"name": "N", "price": 1.0, "quantity": 1}
    bad = [
        {"price": -1.0},
        {"quantity": -5},
        {"name": ""},
        {"name": "x" * 10_000},
        {"description": "x" * 100_000},
    ]
    for override in bad:
        resp = client.post("/items", json={**ok, **override})
        assert resp.status_code == 422, override
    item_id = client.post("/items", json=ok).json()["item_id"]
    resp = client.put(f"/items/{item_id}", json={**ok, "price": -1})
    assert resp.status_code == 422


def test_echo_rejects_oversized_text():
    assert client.get("/echo/hello").json()["echo"] == "hello"
    assert client.get("/echo/" + "x" * 5_000).status_code == 422


def test_item_store_is_capped(monkeypatch):
    # The service is deployed --allow-unauthenticated; an unbounded in-memory
    # store lets anyone grow memory until the instance is OOM-killed.
    from app import main

    monkeypatch.setattr(main, "items_db", {})
    monkeypatch.setattr(main, "MAX_ITEMS", 2)
    body = {"name": "C", "price": 1.0, "quantity": 1}
    assert client.post("/items", json=body).status_code == 200
    assert client.post("/items", json=body).status_code == 200
    assert client.post("/items", json=body).status_code == 507


def test_runtime_requirements_exclude_dev_tools():
    # The Dockerfile installs requirements.txt into the production image;
    # test/lint tools there only add attack surface.
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    names = {
        line.split("==")[0].split(">=")[0].split("[")[0].strip().lower()
        for line in (root / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert names.isdisjoint({"pytest", "black", "flake8", "mypy", "bandit"})


def test_update_does_not_resurrect_concurrently_deleted_item(monkeypatch):
    # Regression: update_item checked `item_id in items_db` and then wrote
    # it. Sync endpoints run in a threadpool, so a DELETE landing between the
    # check and the write was undone: the "deleted" item came back.
    import threading

    from app import main

    threads = []

    class RacyDict(dict):
        armed = True

        def __contains__(self, key):
            found = dict.__contains__(self, key)
            if self.armed:
                self.armed = False
                t = threading.Thread(target=main.delete_item, args=(key,))
                t.start()
                t.join(timeout=0.2)  # let the delete run "in between"
                threads.append(t)
            return found

    body = {"name": "R", "price": 1.0, "quantity": 1}
    monkeypatch.setattr(main, "items_db", RacyDict({1: body}))
    main.update_item(1, main.Item(**body))
    for t in threads:
        t.join(timeout=2)
    assert 1 not in dict.keys(main.items_db)


def test_limits_are_configurable_from_env(monkeypatch):
    import pytest

    from app import main

    monkeypatch.setenv("GUARDIAN_TEST_LIMIT", "42")
    assert main._env_int("GUARDIAN_TEST_LIMIT", 7) == 42
    monkeypatch.delenv("GUARDIAN_TEST_LIMIT")
    assert main._env_int("GUARDIAN_TEST_LIMIT", 7) == 7
    for bad in ("0", "-3", "abc"):
        monkeypatch.setenv("GUARDIAN_TEST_LIMIT", bad)
        with pytest.raises(ValueError):
            main._env_int("GUARDIAN_TEST_LIMIT", 7)
