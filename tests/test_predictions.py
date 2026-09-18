"""
Prediction History endpoint tests — mocked MongoDB (no real server needed).

Covers: authentication required, user isolation, empty history, newest-first
ordering, single-prediction retrieval, ownership protection, invalid IDs,
pagination bounds, and the unchanged anonymous POST /predict flow.
Run: pytest tests/test_predictions.py -v
"""
import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.database import db as db_singleton
from app.dependencies import get_db, get_current_active_user, get_optional_current_user

BASE = "/api/v1/predictions"

USER_A = {"_id": ObjectId(), "email": "a@agriscan.io", "full_name": "Farmer A",
          "role": "farmer", "is_active": True, "created_at": datetime.utcnow()}
USER_B = {"_id": ObjectId(), "email": "b@agriscan.io", "full_name": "Farmer B",
          "role": "farmer", "is_active": True, "created_at": datetime.utcnow()}


def _prediction_doc(user, i=0, disease="Tomato Early blight", crop="Tomato"):
    return {
        "_id": ObjectId(),
        "user_id": str(user["_id"]),
        "image_url": "/test_images/x.jpg",
        "crop": crop,
        "disease": disease,
        "confidence": 50.0 + i,
        "is_healthy": False,
        "class_name": f"{crop}___{disease}".replace(" ", "_"),
        "inference_time_ms": 12.3,
        "created_at": datetime.utcnow() - timedelta(minutes=i),
    }


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.predictions.find = MagicMock()
    db.predictions.count_documents = AsyncMock(return_value=0)
    db.predictions.find_one = AsyncMock(return_value=None)
    return db


def _cursor(docs):
    """Chainable find() cursor stand-in supporting sort/skip/limit."""
    cur = MagicMock()
    cur.sort.return_value = cur
    cur.skip.return_value = cur
    cur.limit.return_value = cur
    cur.to_list = AsyncMock(return_value=docs)
    return cur


# ── Authentication ────────────────────────────────────────────────────────

async def test_history_requires_auth(mock_db):
    """No token → rejected by the real HTTPBearer dependency (no override)."""
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(BASE)
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


async def test_detail_requires_auth(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"{BASE}/{ObjectId()}")
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


# ── History list ──────────────────────────────────────────────────────────

async def test_empty_history_returns_valid_response(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    mock_db.predictions.find.return_value = _cursor([])
    mock_db.predictions.count_documents.return_value = 0
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(BASE)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["total"] == 0
        assert body["total_pages"] == 0
    finally:
        app.dependency_overrides.clear()


async def test_history_user_isolation(mock_db):
    """User A's token yields only A's documents — enforced by the query
    itself (captured here) and never by post-filtering."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    a_docs = [_prediction_doc(USER_A, i) for i in range(2)]
    mock_db.predictions.find.return_value = _cursor(a_docs)
    mock_db.predictions.count_documents.return_value = 2
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(BASE)
        assert resp.status_code == 200
        # The DB query itself was scoped to user A.
        assert mock_db.predictions.find.call_args[0][0]["user_id"] == str(USER_A["_id"])
        body = resp.json()
        assert [d["user_id"] for d in body["data"]] == [str(USER_A["_id"])] * 2
        assert all(d["user_id"] != str(USER_B["_id"]) for d in body["data"])
    finally:
        app.dependency_overrides.clear()


async def test_history_newest_first(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    docs = [_prediction_doc(USER_A, i) for i in range(3)]
    mock_db.predictions.find.return_value = _cursor(docs)
    mock_db.predictions.count_documents.return_value = 3
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(BASE)
        assert resp.status_code == 200
        # The sort directive requests descending created_at (newest first).
        assert mock_db.predictions.find.return_value.sort.call_args[0] == ("created_at", -1)
        stamps = [d["created_at"] for d in resp.json()["data"]]
        assert stamps == sorted(stamps, reverse=True)
    finally:
        app.dependency_overrides.clear()


async def test_history_pagination_bounds(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r_zero = await c.get(f"{BASE}?page=0")
            r_over = await c.get(f"{BASE}?page_size=1000")
        assert r_zero.status_code == 422
        assert r_over.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ── Single prediction ─────────────────────────────────────────────────────

async def test_get_own_prediction(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    doc = _prediction_doc(USER_A)
    mock_db.predictions.find_one.return_value = dict(doc)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"{BASE}/{doc['_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == str(doc["_id"])
        assert body["data"]["disease"] == "Tomato Early blight"
        # Ownership is part of the query.
        q = mock_db.predictions.find_one.call_args[0][0]
        assert q["user_id"] == str(USER_A["_id"]) and q["_id"] == doc["_id"]
    finally:
        app.dependency_overrides.clear()


async def test_cannot_view_other_users_prediction(mock_db):
    """B owns the doc but the request carries A's identity → the
    ownership-scoped query misses and the API answers 404 (no leak)."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    mock_db.predictions.find_one.return_value = None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"{BASE}/{ObjectId()}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_invalid_prediction_id_rejected(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_active_user] = lambda: dict(USER_A)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"{BASE}/not-a-valid-objectid")
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ── Existing predict flow (unchanged contract) ────────────────────────────

def _install_fake_predict_stack(monkeypatch, user=None):
    """Fake predictor + fake db.database['predictions'] for POST /predict."""

    class _FakePredictor:
        def predict(self, b):
            # Mirrors the real classifier's output shape (Phase 6 adds the
            # genuine top-1 class_index from the YOLOv8 probs tensor).
            return {"crop": "Tomato", "disease": "Early blight", "confidence": 91.5,
                    "is_healthy": False, "class_name": "Tomato___Early_blight",
                    "class_index": 28}

    # JWT payload that a hypothetical client could try to pass along (it must
    # be ignored — identity comes from the verified token only).

    import app.routers.predict as predict_module
    monkeypatch.setattr(predict_module, "predictor", _FakePredictor())

    collection = MagicMock()
    collection.insert_one = AsyncMock(return_value=AsyncMock(inserted_id=ObjectId()))
    fake_database = MagicMock()
    fake_database.__getitem__.return_value = collection
    monkeypatch.setattr(db_singleton, "database", fake_database)

    if user is not None:
        app.dependency_overrides[get_optional_current_user] = lambda: dict(user)
    else:
        app.dependency_overrides[get_optional_current_user] = lambda: None
    return collection


async def test_predict_still_works_anonymous(monkeypatch):
    """POST /predict without auth still persists and responds identically
    (user_id stays 'anonymous' when no token is supplied)."""
    collection = _install_fake_predict_stack(monkeypatch, user=None)

    # A legacy client impersonation attempt: ?user_id=<someone else> must be
    # ignored — there is no user_id parameter at all anymore.
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/predict",
                params={"user_id": str(USER_B["_id"])},  # impersonation attempt
                files={"file": ("leaf.jpg", b"fake", "image/jpeg")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["saved_to_db"] is True
        assert body["prediction_id"] is not None
        assert body["data"]["crop"] == "Tomato"
        # Phase 6: real model fields surface in the response and the persisted doc.
        assert body["data"]["class_index"] == 28
        assert isinstance(body["inference_time_ms"], float)
        persisted = collection.insert_one.call_args[0][0]
        assert persisted["class_index"] == 28
        assert persisted["inference_time_ms"] == body["inference_time_ms"]
        # 422 would also prove the parameter is gone; 200 + 'anonymous' proves
        # it is gone AND ignored. Either way impersonation is impossible.
        assert collection.insert_one.call_args[0][0]["user_id"] in ("anonymous",)
        assert collection.insert_one.call_args[0][0]["user_id"] != str(USER_B["_id"])
    finally:
        app.dependency_overrides.clear()


async def test_predict_attributed_to_authenticated_user(monkeypatch):
    """With a valid token, the persisted user_id is the JWT subject."""
    collection = _install_fake_predict_stack(monkeypatch, user=USER_A)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/predict",
                files={"file": ("leaf.jpg", b"fake", "image/jpeg")},
            )
        assert resp.status_code == 200
        assert collection.insert_one.call_args[0][0]["user_id"] == str(USER_A["_id"])
        # Authenticated attribution + persistence of the structured fields.
        assert collection.insert_one.call_args[0][0]["class_index"] == 28
        assert "prediction_id" in resp.json()
    finally:
        app.dependency_overrides.clear()


# ── Phase 12: hardening behavior ──────────────────────────────────────────

async def test_cors_configured_origins_only():
    """Wildcard CORS is gone: known frontend origins are allowed, unknown
    origins get no Access-Control-Allow-Origin header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        allowed = await c.options(
            "/api/v1/predictions",
            headers={
                "Origin": "https://agriscan-3d.netlify.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = await c.options(
            "/api/v1/predictions",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert allowed.headers.get("access-control-allow-origin") == "https://agriscan-3d.netlify.app"
    assert denied.headers.get("access-control-allow-origin") is None


async def test_predict_rejects_non_image(monkeypatch):
    collection = _install_fake_predict_stack(monkeypatch, user=None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/predict",
                files={"file": ("notes.txt", b"not an image", "text/plain")},
            )
        assert resp.status_code == 415
        # Nothing was inferred or persisted.
        collection.insert_one.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()


async def test_predict_rejects_oversized_image(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_SIZE", 8)  # bytes
    collection = _install_fake_predict_stack(monkeypatch, user=None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/predict",
                files={"file": ("big.jpg", b"x" * 64, "image/jpeg")},
            )
        assert resp.status_code == 413
        collection.insert_one.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()
