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
    new_item = {"name": "Test", "description": "For testing", "price": 10.0, "quantity": 1}
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
