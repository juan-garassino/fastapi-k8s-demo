# GUARDIAN

Automated security & bug guardian ledger for this repo. Branch: `claude/guardian`.

## Checks

- Dependencies: `pip-audit -r requirements.txt`
- Static analysis: `bandit -r src`; manual grep for eval/exec, pickle, yaml.load, `shell=True`, SQL formatting, path traversal, SSRF, `verify=False`, permissive CORS, debug servers
- Secrets: `gitleaks detect --log-opts=--all --redact` (full history), `detect-secrets scan --all-files`, manual history grep
- GitHub Actions: action pinning, `permissions:` scope, `${{ github.event.* }}` in `run:`, deploy triggers
- Dockerfile: non-root `USER`, base-image pinning, build context hygiene
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

Secrets: gitleaks (31 commits, all refs) and detect-secrets found nothing.

## Metrics

| metric | before | after |
|--------|--------|-------|
| open vulns (crit/high/med/low) | 0/2/1/2 packages (18 advisories) | 0/0/0/0 deps; config items open: 1 med (G-010), 3 low |
| tests passing (plain `pytest`, as CI) | 0 (collection error) | 6/6 |
| test count | 3 | 6 |
| ruff (defaults) | 11 | 0 |
| flake8 | 24 | 22 |
| mypy errors | 2 | 0 |
| bandit (high/med/low) | 0/0/1 | 0/0/1 |

## Backlog

- Apply the CI patch for G-010/G-011 by hand (guardian token cannot edit workflows).
- Pin GitHub Actions to commit SHAs (G-014) and base image by digest (G-015).
- `.sample` workflows grant `contents: write`/`packages: write` workflow-wide; scope per job before enabling them.
- `/echo/{text}` and the in-memory store have no size limits; fine for a demo, add limits before real use.
- Consider pinning transitive deps (lock file) and adding Dependabot.

## Log

- Run 1 — 2026-10-15: baseline scan; bumped 5 vulnerable deps (pip-audit now clean); fixed ID-reuse overwrite, nullable description, broken CI test import, k8s probe path/port mismatch; CI hardening (deploy-on-PR, OIDC scope) blocked: push token lacks `workflow` scope, left open; non-root Docker user + committed .dockerignore. 3 regression tests added (3 -> 6 tests, all passing).

## Learnings

- The guardian push token cannot modify `.github/workflows/*`; workflow fixes must be proposed as patches for the owner.

- `python -m pytest` hides import-path bugs that plain `pytest` (what CI runs) exposes; verify with the CI command.
- Recent FastAPI has no upper bound on starlette, so starlette security floors must be pinned explicitly.

## Ideas

1. Add a CI step running `pip-audit` and `bandit` on every PR.
2. Add a manifest-vs-app consistency check (probes/ports) for all k8s files.
3. Replace the in-memory dict with a small repository class so tests can reset state between cases.
