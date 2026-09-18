"""
Configuration & database wiring tests — no real MongoDB server required.

Covers:
  - configuration loading (defaults, env overrides, legacy MONGODB_URL alias)
  - Database.connect() uses the configured URI/db name and pings before indexes
  - get_database() connection guard
  - no hardcoded MongoDB credentials in app/database.py or .env.example
  - existing /predict persistence behavior (insert + failure tolerance, mocked)
"""
import io
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.config as config_module
import app.database as database_module
from app.database import Database, get_database


APP_DIR = Path(__file__).resolve().parent.parent / "app"
BACKEND_DIR = APP_DIR.parent

PREDICTION_COLLECTIONS = (
    "users", "farms", "fields", "uploads",
    "analysis_results", "jobs", "predictions",
)


def _fresh_settings(monkeypatch, **env):
    """Build a Settings instance without reading the developer's real .env."""
    for key in ("MONGODB_URI", "MONGODB_DB_NAME", "MONGODB_URL", "JWT_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return config_module.Settings(_env_file=None)


# ── Configuration loading ────────────────────────────────────────────────

def test_settings_defaults_use_local_mongodb(monkeypatch):
    s = _fresh_settings(monkeypatch)
    assert s.MONGODB_URI == "mongodb://localhost:27017"
    assert s.MONGODB_DB_NAME == "agriscan"


def test_settings_read_env_override(monkeypatch):
    s = _fresh_settings(
        monkeypatch,
        MONGODB_URI="mongodb://envhost:27017",
        MONGODB_DB_NAME="envdb",
    )
    assert s.MONGODB_URI == "mongodb://envhost:27017"
    assert s.MONGODB_DB_NAME == "envdb"


def test_legacy_mongodb_url_env_still_supported(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://legacy:27017")
    monkeypatch.delenv("MONGODB_URI", raising=False)
    s = config_module.Settings(_env_file=None)
    assert s.MONGODB_URI == "mongodb://legacy:27017"


def test_settings_lowercase_accessors(monkeypatch):
    s = _fresh_settings(
        monkeypatch,
        MONGODB_URI="mongodb://acc:27017",
        MONGODB_DB_NAME="accd",
    )
    assert s.mongodb_uri == "mongodb://acc:27017"
    assert s.mongodb_db_name == "accd"


# ── Database connection configuration ────────────────────────────────────

def _fake_motor_client():
    """Motor client stand-in: ping + per-collection create_indexes."""
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    database = MagicMock()
    for name in PREDICTION_COLLECTIONS:
        getattr(database, name).create_indexes = AsyncMock()
    client.__getitem__ = MagicMock(return_value=database)
    return client, database


@pytest.mark.asyncio
async def test_connect_uses_config_and_creates_indexes(monkeypatch):
    settings = _fresh_settings(
        monkeypatch,
        MONGODB_URI="mongodb://cfg-host:27017",
        MONGODB_DB_NAME="cfg-db",
    )
    monkeypatch.setattr(database_module, "get_settings", lambda: settings)

    client, database = _fake_motor_client()
    db_obj = Database()
    with patch.object(database_module, "AsyncIOMotorClient", return_value=client) as ctor:
        await db_obj.connect()

    ctor.assert_called_once()
    args, kwargs = ctor.call_args
    assert args[0] == "mongodb://cfg-host:27017"
    assert kwargs["maxPoolSize"] == 50
    client.__getitem__.assert_called_once_with("cfg-db")
    client.admin.command.assert_awaited_once_with("ping")
    for name in PREDICTION_COLLECTIONS:
        getattr(database, name).create_indexes.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_skips_indexes_if_ping_fails(monkeypatch):
    settings = _fresh_settings(monkeypatch, MONGODB_URI="mongodb://bad:27017")
    monkeypatch.setattr(database_module, "get_settings", lambda: settings)

    client, database = _fake_motor_client()
    client.admin.command = AsyncMock(side_effect=RuntimeError("connection refused"))
    db_obj = Database()
    with patch.object(database_module, "AsyncIOMotorClient", return_value=client):
        with pytest.raises(RuntimeError):
            await db_obj.connect()
    database.users.create_indexes.assert_not_awaited()


@pytest.mark.asyncio
async def test_close_disposes_client():
    db_obj = Database()
    client = MagicMock()
    db_obj.client = client
    db_obj.database = object()
    await db_obj.close()
    client.close.assert_called_once()
    assert db_obj.client is None
    assert db_obj.database is None


def test_get_database_requires_connection(monkeypatch):
    monkeypatch.setattr(database_module.db, "database", None)
    with pytest.raises(RuntimeError):
        get_database()


def test_get_database_returns_connected_db(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(database_module.db, "database", sentinel)
    assert get_database() is sentinel


# ── No hardcoded credentials ─────────────────────────────────────────────

def test_no_hardcoded_mongodb_credentials_in_database_py():
    src = (APP_DIR / "database.py").read_text(encoding="utf-8")
    assert "mongodb+srv://" not in src
    assert "MONGODB_URI =" not in src
    assert "MONGODB_DB_NAME =" not in src
    assert re.search(r"[?&]appName=", src) is None


def test_env_example_contains_only_placeholders():
    text = (BACKEND_DIR / ".env.example").read_text(encoding="utf-8")
    assert "<username>" in text and "<password>" in text
    assert "replace-with-a-long-random-secret" in text
    # No real-looking credentials (user:password with a non-placeholder secret).
    assert not re.search(r"mongodb\+srv://[A-Za-z0-9_.-]+:[^<@\s]+@", text)


# ── Prediction persistence (existing flow, mocked) ───────────────────────

@pytest.fixture
def stub_predictor(monkeypatch):
    import app.routers.predict as predict_router

    class _StubPredictor:
        def predict(self, image_bytes):
            return {
                "disease": "Early blight",
                "crop": "Potato",
                "confidence": 91.5,
                "is_healthy": False,
                "class_name": "Potato___Early_blight",
            }

    monkeypatch.setattr(predict_router, "predictor", _StubPredictor())


def _mock_predictions_collection(monkeypatch):
    collection = MagicMock()
    collection.insert_one = AsyncMock(return_value=AsyncMock(inserted_id=None))
    database = MagicMock()
    database.__getitem__ = MagicMock(return_value=collection)
    monkeypatch.setattr(database_module.db, "database", database)
    return collection


@pytest.mark.asyncio
async def test_predict_persists_to_mongodb(monkeypatch, stub_predictor):
    from bson import ObjectId
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    collection = _mock_predictions_collection(monkeypatch)
    collection.insert_one = AsyncMock(return_value=AsyncMock(inserted_id=ObjectId()))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("leaf.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["saved_to_db"] is True
    assert body["prediction_id"]
    assert body["data"]["crop"] == "Potato"

    collection.insert_one.assert_awaited_once()
    saved = collection.insert_one.await_args.args[0]
    assert saved["crop"] == "Potato"
    assert saved["disease"] == "Early blight"
    assert saved["confidence"] == 91.5
    assert saved["is_healthy"] is False
    assert isinstance(saved["created_at"], datetime)


@pytest.mark.asyncio
async def test_predict_survives_db_save_failure(monkeypatch, stub_predictor):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    collection = _mock_predictions_collection(monkeypatch)
    collection.insert_one = AsyncMock(side_effect=RuntimeError("mongo down"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("leaf.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["saved_to_db"] is False
    assert body["prediction_id"] is None
