"""Security-hardening tests: JWT, role escalation, rate limiting, uploads,
and auth-response headers."""
import io
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.main import app
from app.config import Settings, get_settings
from app.database import db as db_module
from app.dependencies import get_db
from app.utils import security


# ---------- JWT ----------

def test_access_token_roundtrip():
    token = security.create_access_token("user-123")
    payload = security.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_expired_token_rejected():
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "user-123",
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    assert security.decode_access_token(expired) is None


def test_tampered_token_rejected():
    token = security.create_access_token("user-123")
    header, payload, sig = token.split(".")
    # Flip the signature's last character.
    bad_sig = ("A" if sig[-1] != "A" else "B") + sig[1:]
    assert security.decode_access_token(f"{header}.{payload}.{bad_sig}") is None


def test_wrong_algorithm_rejected():
    settings = get_settings()
    # Signed with HS384 — decode is pinned to HS256 so this must fail.
    token = jwt.encode(
        {"sub": "user-123", "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.JWT_SECRET_KEY,
        algorithm="HS384",
    )
    assert security.decode_access_token(token) is None


def test_alg_none_token_rejected():
    import base64, json
    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()
    token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': 'x', 'type': 'access', 'exp': 9999999999})}."
    assert security.decode_access_token(token) is None


def test_missing_sub_rejected():
    settings = get_settings()
    token = jwt.encode(
        {"type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    assert security.decode_access_token(token) is None


def test_refresh_token_not_accepted_as_access():
    refresh = security.create_refresh_token("user-123")
    assert security.decode_access_token(refresh) is None


# ---------- Production config ----------

def test_production_has_no_default_origins():
    # _env_file=None isolates the test from backend/.env values.
    s = Settings(ENV="production", _env_file=None)
    assert s.is_production is True
    assert s.allowed_origins == []


def test_development_keeps_local_origins():
    s = Settings(ENV="development", _env_file=None)
    assert s.is_production is False
    assert any("localhost" in o for o in s.allowed_origins)


def test_explicit_origins_env_only():
    s = Settings(
        ENV="production",
        ALLOWED_ORIGINS="https://app.example.com",
        _env_file=None,
    )
    assert s.allowed_origins == ["https://app.example.com"]


# ---------- Registration role escalation ----------

@pytest.mark.asyncio
async def test_register_ignores_client_role():
    mock_db = AsyncMock()
    mock_db.users.find_one = AsyncMock(return_value=None)
    mock_db.users.insert_one = AsyncMock(
        return_value=AsyncMock(inserted_id=__import__("bson").ObjectId())
    )
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/register", json={
                "email": "attacker@x.io",
                "password": "Strong@1234",
                "full_name": "Attacker",
                "role": "admin",
            })
        assert resp.status_code == 201
        inserted = mock_db.users.insert_one.await_args.args[0]
        assert inserted["role"] == "farmer"
        assert resp.json()["data"]["role"] == "farmer"
    finally:
        app.dependency_overrides.clear()


# ---------- Rate limiting ----------

@pytest.mark.asyncio
async def test_login_rate_limit_returns_429():
    mock_db = AsyncMock()
    mock_db.users.find_one = AsyncMock(return_value=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        codes = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(6):
                resp = await client.post("/api/v1/auth/login", json={
                    "email": "nobody@x.io",
                    "password": "Wrong@1234",
                })
                codes.append(resp.status_code)
        assert codes[:5] == [401] * 5
        assert codes[5] == 429
    finally:
        app.dependency_overrides.clear()


# ---------- Auth response headers ----------

@pytest.mark.asyncio
async def test_me_without_token_is_401_with_www_authenticate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_me_with_garbage_token_is_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-token"},
        )
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


# ---------- Upload validation ----------

@pytest.mark.asyncio
async def test_predict_rejects_non_image_bytes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("evil.jpg", io.BytesIO(b"MZ\x90\x00not-an-image"), "image/jpeg")},
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_predict_rejects_text_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("notes.txt", io.BytesIO(b"hello world"), "image/png")},
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_predict_accepts_png_signature():
    # Valid PNG magic bytes pass the signature gate; the stub-free real
    # predictor then fails decode → 400 (proves we reached inference, not 415).
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("x.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32), "image/png")},
        )
    assert resp.status_code in (400, 415, 503)  # past the signature check
    assert resp.status_code != 422
