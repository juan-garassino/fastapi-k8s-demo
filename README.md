# fastapi-k8s-demo

A small FastAPI service with a Dockerfile, Kubernetes manifests and a GitHub Actions pipeline that tests, builds and deploys it to Google Cloud Run.

## What and why

A compact reference for taking a Python API from code to a running container: an in-memory CRUD API, tests, a container image, and CI/CD. The app is deliberately trivial so the delivery path is the point. It was built as a teaching/demo project.

## Highlights

- FastAPI app with health, CRUD (`/items`), and utility endpoints (`/random`, `/echo/{text}`, `/status`), plus auto-generated docs at `/docs`.
- Dockerfile on `python:3.11-slim` that binds uvicorn to `${PORT:-8080}`, the contract Cloud Run expects (see the "PORT binding" commits in `git log`).
- GitHub Actions workflow: run pytest on push/PR to `main`, then build, push to Artifact Registry and deploy to Cloud Run. Auth uses Workload Identity Federation, so no long-lived keys.
- Kubernetes `Deployment` (3 replicas), `HorizontalPodAutoscaler` (3 to 10 pods at 80% CPU) and a `LoadBalancer` `Service`.
- Alternative workflows kept as `.sample` files for Cloud Run-only and dual-registry setups.

## Quickstart

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Tests (use `python -m pytest`: the tests import `src.app.main`, which needs the repo root on the path)
python -m pytest -q

# Run the API
uvicorn src.app.main:app --port 8080
curl localhost:8080/healthz
curl -X POST localhost:8080/items -H 'content-type: application/json' \
     -d '{"name":"widget","price":1.5,"quantity":2}'
curl localhost:8080/items
```

Interactive docs: http://localhost:8080/docs

Container (needs Docker):

```bash
docker build -t fastapi-demo .
docker run -p 8080:8080 fastapi-demo
```

Kubernetes (needs a cluster and `kubectl`): the manifests reference `ghcr.io/juan-garassino/fastapi-demo:latest` and port 8000. See Status below for mismatches to fix before applying.

```bash
kubectl apply -f kubernetes/deployment.yaml -f kubernetes/service.yaml
```

Copy `.env.sample` to a local env file to see which GCP/GHCR values the pipeline expects. It contains keys only.

## Project structure

```
src/app/main.py            FastAPI app (in-memory item store, all endpoints)
tests/test_api.py          3 tests: root, create+read item, /healthz
Dockerfile                 python:3.11-slim, uvicorn on ${PORT:-8080}
requirements.txt           pinned runtime and dev/lint dependencies
pyproject.toml             package metadata
kubernetes/deployment.yaml Deployment + HorizontalPodAutoscaler
kubernetes/service.yaml    LoadBalancer Service (80 -> 8000)
.github/workflows/         ci-cd.yml (active) and two .sample variants
.env.sample                variable names used by the pipeline (no values)
```

## Results

Checked locally on 2026-10-15: the 3 tests pass, the server starts, and `/healthz`, `POST /items` and `GET /items` respond as expected. The Docker build, the Kubernetes apply and the CI/CD deploy were not run for this README.

## Tech stack

Python 3.11, FastAPI, Uvicorn, pytest + httpx, Docker, Kubernetes, GitHub Actions, Google Cloud Run and Artifact Registry.

## Status and roadmap

Demo-quality; known rough edges:

- The Kubernetes probes call `/health`, but the app serves `/healthz`, so the probes would fail as written.
- The manifests use container port 8000, while the Dockerfile listens on `${PORT:-8080}`. Set `PORT=8000` or align the manifests.
- The manifests pull from GHCR, but the active workflow pushes to Artifact Registry and deploys to Cloud Run; the Kubernetes path is not wired into CI.
- Data lives in process memory and is lost on restart. `item_id` is `len(items_db) + 1`, so IDs can collide after a delete.
- `main.py` prints a leftover "DEPLOY TEST" line on import.
- Only 3 tests; PUT, DELETE and 404 paths are untested. Linters in `requirements.txt` are not run in CI.

## License

No license file is present in the repository.
