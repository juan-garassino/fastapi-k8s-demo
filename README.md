# FastAPI Kubernetes CI/CD Demo

This project demonstrates a complete CI/CD pipeline for FastAPI with Kubernetes deployment.

## Project Structure
- FastAPI application in `src/app`
- Kubernetes manifests in `kubernetes/`
- GitHub Actions CI/CD pipeline
- Docker containerization

## Pipeline Features:
1. **Test**: Runs tests on PRs and pushes to main
2. **Build**: Builds Docker image on successful tests
3. **Push**: Pushes to GitHub Container Registry with:
   - `latest` tag
   - Commit SHA tag
4. **Deploy**: Updates Kubernetes manifests with your GitHub username

## Kubernetes Deployment
To deploy to a Kubernetes cluster:

1. Update `kubernetes/deployment.yaml` with your GitHub username
2. Apply manifests:
```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

## Local Development
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run locally
uvicorn app.main:app --app-dir src --reload

# Run tests
pytest

# Build Docker image
docker build -t fastapi-demo .

# Run container
docker run -p 8080:8080 fastapi-demo
```

## Access the API
- Local: http://localhost:8000 (uvicorn) / http://localhost:8080 (Docker)
- Kubernetes: Get external IP with `kubectl get svc fastapi-demo-service`
