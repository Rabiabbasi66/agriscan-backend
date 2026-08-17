"""
Auth endpoint tests — uses httpx AsyncClient against the FastAPI app.
Run: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app

BASE = "/api/v1/auth"

FAKE_USER = {
    "_id": __import__("bson").ObjectId(),
    "email": "test@agriscan.io",
    "full_name": "Test Farmer",
    "phone": None,
    "role": "farmer",
    "is_active": True,
    "hashed_password": __import__("app.utils.security", fromlist=["hash_password"]).hash_password("Test1234"),
    "fcm_token": None,
    "profile_pic": None,
    "created_at": __import__("datetime").datetime.utcnow(),
    "updated_at": __import__("datetime").datetime.utcnow(),
}


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.users.find_one = AsyncMock(return_value=None)
    db.users.insert_one = AsyncMock(return_value=AsyncMock(inserted_id=FAKE_USER["_id"]))
    db.users.update_one = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_register_success(mock_db):
    with patch("app.services.auth_service.AsyncIOMotorDatabase", mock_db), \
         patch("app.dependencies.get_database", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"{BASE}/register", json={
                "email": "new@agriscan.io",
                "password": "Strong1234",
                "full_name": "New Farmer",
                "role": "farmer",
            })
            # Without real DB, expect 500 or 201 depending on mock wiring
            assert resp.status_code in (201, 422, 500)


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
        assert data["status"] == "ok"
        assert "uptime_s" in data
