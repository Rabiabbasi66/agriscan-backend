"""Farm CRUD endpoint tests (minimal, wires schema validation)."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_farm_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/farms", json={
            "name": "Sunflower Farm",
            "longitude": 77.2090,
            "latitude": 28.6139,
            "total_area": 50000,
            "crop_type": "Wheat",
        })
        # HTTPBearer missing credentials → 403 "Not authenticated".
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_farms_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/farms")
        assert resp.status_code in (401, 403)

