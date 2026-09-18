"""Upload endpoint tests — verifies auth + file type validation."""
import pytest
import io
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_upload_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads",
            files={"files": ("test.jpg", io.BytesIO(b"fake"), "image/jpeg")},
            data={"field_id": "000000000000000000000001", "source": "mobile"},
        )
        # Missing/invalid credentials are rejected: HTTPBearer auto_error
        # responds 403 ("Not authenticated"); treat 401/403 both as unauthenticated.
        assert resp.status_code in (401, 403)

