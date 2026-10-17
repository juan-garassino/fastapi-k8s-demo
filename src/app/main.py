import random
from datetime import UTC, datetime
from itertools import count
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

app = FastAPI(
    title="FastAPI CI/CD Demo",
    description="Simple FastAPI app showcasing CI/CD deployment with GET, POST, PUT, DELETE endpoints.",
    version="1.1.0"
)


# --- Models ---
class Item(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: float = Field(ge=0, allow_inf_nan=False)
    quantity: int = Field(ge=0)


# Mock in-memory store, capped so unauthenticated clients
# cannot exhaust memory.
MAX_ITEMS = 10_000
MAX_ECHO_LENGTH = 1000
items_db: dict[int, dict] = {}
# Monotonic ID source: never reuses an ID after a delete.
_next_id = count(1)

# --- Endpoints ---


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI CI/CD Demo!", "timestamp": datetime.now(UTC)}


@app.get("/healthz")
def health_check():
    """Health check endpoint for CI/CD smoke tests."""
    return {"status": "healthy", "timestamp": datetime.now(UTC)}


@app.get("/items")
def list_items():
    """List all items."""
    return {"items": list(items_db.values()), "count": len(items_db)}


@app.get("/items/{item_id}")
def read_item(item_id: int):
    """Retrieve a single item by ID."""
    item = items_db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": item, "timestamp": datetime.now(UTC)}


@app.post("/items")
def create_item(item: Item):
    """Create a new item."""
    if len(items_db) >= MAX_ITEMS:
        raise HTTPException(status_code=507, detail="Item store is full")
    item_id = next(_next_id)
    items_db[item_id] = item.model_dump()
    return {"message": "Item created", "item_id": item_id, "timestamp": datetime.now(UTC)}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    """Update an existing item."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item.model_dump()
    return {"message": "Item updated", "item_id": item_id, "timestamp": datetime.now(UTC)}


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    """Delete an item."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    deleted = items_db.pop(item_id)
    return {"message": "Item deleted", "deleted": deleted, "timestamp": datetime.now(UTC)}


@app.get("/random")
def get_random_number():
    """Simple random number generator for testing variability."""
    return {"random_number": random.randint(1, 100), "timestamp": datetime.now(UTC)}


@app.get("/echo/{text}")
def echo_text(text: Annotated[str, Path(max_length=MAX_ECHO_LENGTH)]):
    """Echo back any text."""
    return {"echo": text, "timestamp": datetime.now(UTC)}


@app.get("/status")
def service_status():
    """Returns metadata about the service."""
    return {
        "service": "FastAPI CI/CD Demo",
        "version": "1.1.0",
        "status": "running",
        "region": "europe-west1",
        "timestamp": datetime.now(UTC)
    }
