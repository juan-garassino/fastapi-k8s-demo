# GUARDIAN

Automated security & bug guardian ledger for this repo. Branch: `claude/guardian`.

## Checks

- Dependencies: `pip-audit -r requirements.txt`
- Static analysis: `bandit -r src`; manual grep for eval/exec, pickle, yaml.load, `shell=True`, SQL formatting, path traversal, SSRF, `verify=False`, permissive CORS, debug servers
- Secrets: `gitleaks detect --log-opts=--all --redact` (full history), `detect-secrets scan --all-files`, manual history grep
- GitHub Actions: action pinning, `permissions:` scope, `${{ github.event.* }}` in `run:`, deploy triggers
- Dockerfile: non-root `USER`, base-image pinning, build context hygiene; `hadolint Dockerfile` (v2.12.0 static binary from the GitHub release) must report 0 findings
- Kubernetes manifests: probe paths/ports vs. the app
- Tests: `pytest` (plain, as CI runs it); lint: ruff (defaults), flake8, mypy

## Findings ledger

| id | severity | type | file | status | date |
|----|----------|------|------|--------|------|
| G-001 | high | vuln: starlette 0.38.6 (7 advisories incl. CVE-2024-47874 multipart DoS, Host-header URL reconstruction) | requirements.txt | fixed (fastapi 0.143.2, starlette>=1.3.1) | 2026-10-15 |
| G-002 | high | vuln: python-multipart 0.0.9 (7 advisories incl. CVE-2024-53981 DoS) | requirements.txt | fixed (0.0.32) | 2026-10-15 |
| G-003 | medium | vuln: requests 2.32.3 (CVE-2024-47081 .netrc leak, CVE-2026-25645) | requirements.txt | fixed (2.33.0) | 2026-10-15 |
| G-004 | low | vuln: pytest 8.3.3 (CVE-2025-71176, dev-only) | requirements.txt | fixed (9.0.3) | 2026-10-15 |
| G-005 | low | vuln: black 24.10.0 (CVE-2026-32274, CVE-2026-31900, dev-only) | requirements.txt | fixed (26.3.1) | 2026-10-15 |
| G-006 | high | bug: item IDs `len(db)+1` reused after delete -> silent overwrite of a live item | src/app/main.py | fixed | 2026-10-15 |
| G-007 | medium | bug: `description: str = None` rejects explicit `null` (422) | src/app/main.py | fixed | 2026-10-15 |
| G-008 | high | bug: CI `pytest` fails at collection (`from src.app...` not importable with pythonpath=src) | tests/test_api.py | fixed | 2026-10-15 |
| G-009 | high | bug: k8s probes hit `/health` on port 8000; app serves `/healthz` on 8080 -> pods never Ready | kubernetes/*.yaml | fixed | 2026-10-15 |
| G-010 | medium | CI: deploy job ran on `pull_request` events (unreviewed branch -> prod) | .github/workflows/ci-cd.yml | open (push token lacks `workflow` scope; patch in PR body) | 2026-10-15 |
| G-011 | low | CI: `id-token: write` granted workflow-wide incl. test job | .github/workflows/ci-cd.yml | open (same reason) | 2026-10-15 |
| G-012 | medium | Docker: container ran as root | Dockerfile | fixed (USER appuser) | 2026-10-15 |
| G-013 | medium | Docker: no committed `.dockerignore` (was gitignored) -> `COPY . .` could bake `.env`/`.git` into a public image | .dockerignore, .gitignore | fixed | 2026-10-15 |
| G-014 | low | CI: actions pinned by tag, not commit SHA | .github/workflows/* | open | 2026-10-15 |
| G-015 | low | Docker: base image `python:3.11-slim` not pinned by digest | Dockerfile | open | 2026-10-15 |
| G-016 | low | quality: debug `print` at import, deprecated `utcnow()` / `.dict()` | src/app/main.py | fixed | 2026-10-15 |
| G-017 | info | bandit B311 (`random` for non-crypto demo endpoint) | src/app/main.py | wontfix | 2026-10-15 |
| G-018 | medium | bug: HPA scales on CPU utilization but the Deployment had no `resources.requests.cpu` -> HPA "missing request for cpu", never scales; no memory limit | kubernetes/deployment.yaml | fixed | 2026-10-17 |
| G-019 | medium | k8s: pod had no securityContext (runAsNonRoot, allowPrivilegeEscalation, capabilities) | kubernetes/deployment.yaml | fixed | 2026-10-17 |
| G-020 | medium | DoS: unbounded in-memory item store on a public `--allow-unauthenticated` service (memory exhaustion) | src/app/main.py | fixed (MAX_ITEMS=10000 -> 507) | 2026-10-17 |
| G-021 | low | validation: Item accepted negative price/quantity, empty or unbounded name/description; `/echo` path unbounded | src/app/main.py | fixed (Field bounds, echo max 1000) | 2026-10-17 |
| G-022 | low | Docker: test/lint tools (pytest, black, flake8, mypy, bandit) installed into the production image | requirements.txt, requirements-dev.txt | fixed (split dev deps) | 2026-10-17 |
| G-023 | low | docs: README local run (`uvicorn app.main:app` from repo root) and `docker run -p 8000:8000` (image listens on 8080) were wrong | README.md | fixed | 2026-10-17 |
| G-025 | low | Docker: unpinned `pip install --upgrade pip` (hadolint DL3013) | Dockerfile | fixed (pip==26.2.1) | 2026-10-17 |
| G-026 | low | Docker: shell-form CMD (hadolint DL3025) | Dockerfile | fixed (JSON form, `sh -c "exec ..."` keeps `$PORT`) | 2026-10-17 |
| G-027 | low | tests: no checks tying Dockerfile port/user and Service selector/targetPort to the Deployment | tests/test_manifests.py | fixed (6 tests) | 2026-10-17 |
| G-024 | info | pip-audit of the environment flags pip 24.0 (venv bootstrap only; the Dockerfile upgrades pip) | - | n/a | 2026-10-17 |

Secrets: gitleaks (31 commits, all refs) and detect-secrets found nothing (run 1). Run 2: gitleaks 8.21.2 over 32 commits, all refs, plus manual `git log -p --all` grep: nothing.

## Metrics

| metric | run 1 before | run 1 after | run 2 after |
|--------|--------|-------|-------|
| open vulns/issues (crit/high/med/low) | 0/2/1/2 packages (18 advisories) | deps 0/0/0/0; config 0/0/1/3 | deps 0/0/0/0; open 0/0/1/3 (G-010 med; G-011, G-014, G-015 low). Run 2 found and fixed 0/0/3/6 |
| tests passing (plain `pytest`, as CI) | 0 (collection error) | 6/6 | 18/18 (12 after pass 1) |
| test count | 3 | 6 | 18 |
| ruff | 11 | 0 | 0 |
| flake8 (default 79 cols, no config) | 24 | 22 | 0 (7 after pass 1) |
| mypy errors | 2 | 0 | 0 |
| bandit (high/med/low) | 0/0/1 | 0/0/1 | 0/0/1 |
| hadolint | - | - | 0 (2 before pass 2) |

## Backlog

- Apply the CI patch for G-010/G-011 by hand (guardian token cannot edit workflows).
- Pin GitHub Actions to commit SHAs (G-014) and base image by digest (G-015).
- `.sample` workflows grant `contents: write`/`packages: write` workflow-wide; scope per job before enabling them.
- k8s: consider `readOnlyRootFilesystem: true` after verifying the image starts with it (no cluster available to the guardian).
- Make `MAX_ITEMS` / echo limit env-configurable (needs an app factory or reset hook so tests can rebuild state).
- Optional CI patch: install `-r requirements-dev.txt` instead of `requirements.txt pytest httpx` so CI uses the pinned test tools (workflow edit, owner only).
- Image tag `:latest` in kubernetes/deployment.yaml; pin to a commit-SHA tag or digest when the deploy flow writes manifests.
- Consider pinning transitive deps (lock file) and adding Dependabot.

## Log

- Run 1 — 2026-10-15: baseline scan; bumped 5 vulnerable deps (pip-audit now clean); fixed ID-reuse overwrite, nullable description, broken CI test import, k8s probe path/port mismatch; CI hardening (deploy-on-PR, OIDC scope) blocked: push token lacks `workflow` scope, left open; non-root Docker user + committed .dockerignore. 3 regression tests added (3 -> 6 tests, all passing).

- Run 2 — 2026-10-17: no PR review comments; deps and secrets still clean (gitleaks 32 commits). Fixed HPA without CPU requests (never scales), added pod securityContext, capped the public in-memory store (507 when full), bounded Item fields and `/echo`, moved test/lint tools out of the production image (requirements-dev.txt), fixed README run commands. 6 regression tests, each failing before its fix (6 -> 12 tests, all passing). Workflow items G-010/G-011/G-014 still need the owner. Pass 2: hadolint added to Checks (DL3013 unpinned pip upgrade, DL3025 shell-form CMD fixed, now 0); new tests/test_manifests.py (6 consistency tests: Dockerfile USER/pins/CMD form/port vs containerPort, Service selector/targetPort, HPA target); flake8 7 -> 0 by wrapping lines (no config loosened). 12 -> 18 tests.

## Learnings

- The guardian push token cannot modify `.github/workflows/*`; workflow fixes must be proposed as patches for the owner.

- `python -m pytest` hides import-path bugs that plain `pytest` (what CI runs) exposes; verify with the CI command.
- Recent FastAPI has no upper bound on starlette, so starlette security floors must be pinned explicitly.
- An HPA on `targetCPUUtilizationPercentage` silently does nothing without `resources.requests.cpu`; check every HPA's target for requests.
- `uvicorn[standard]` pulls in PyYAML, so manifest tests can `yaml.safe_load_all` without a new dependency.
- hadolint ships as a single static binary on GitHub releases; it installs in seconds without Docker.
- Both workflows install `pytest httpx` explicitly, so dev tools could leave requirements.txt without a workflow edit.

## Ideas

1. Add a CI step running `pip-audit` and `bandit` on every PR.
2. Add a manifest-vs-app consistency check (probes/ports) for all k8s files.
3. Replace the in-memory dict with a small repository class so tests can reset state between cases.
4. Run `kubeconform`/`kube-linter` on `kubernetes/` in CI to catch missing requests/securityContext.
5. Read `MAX_ITEMS` and the echo limit from env vars so Cloud Run can tune them without a rebuild.
6. Add a Docker build plus `trivy image` scan job once the workflow scope is available.
