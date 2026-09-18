"""
Auth endpoint tests — uses httpx AsyncClient against the FastAPI app.
Run: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
from unittest.mock import AsyncMock

from app.main import app
from app.dependencies import get_db
from app.utils.security import hash_password

BASE = "/api/v1/auth"


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.users.find_one = AsyncMock(return_value=None)
    db.users.insert_one = AsyncMock(return_value=AsyncMock(inserted_id=ObjectId()))
    db.users.update_one = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_register_success(mock_db):
    # Register the fake DB through FastAPI's dependency override mechanism —
    # the register route resolves its DB via Depends(get_db).
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"{BASE}/register", json={
                "email": "new@agriscan.io",
                "password": "Strong@1234",
                "full_name": "New Farmer",
                "role": "farmer",
            })
            assert resp.status_code == 201
            body = resp.json()
            assert body["data"]["email"] == "new@agriscan.io"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_weak_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"{BASE}/register", json={
            "email": "bad@agriscan.io",
            "password": "weak",
            "full_name": "Bad User",
            "role": "farmer",
        })
        assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        # Contract of the live /health endpoint (app/main.py).
        assert data["status"] == "healthy"
        assert data["service"] == "agriscan-api"
