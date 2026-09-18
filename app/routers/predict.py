# app/routers/predict.py
#
# Single-image disease prediction endpoint used by the frontend image scanner.
# Flow: validate upload → run YOLOv8 inference → persist to MongoDB → respond.
# The response contract must stay: {success, data, inference_time_ms,
# saved_to_db, prediction_id}.
import logging
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.database import db
from app.config import get_settings
from app.dependencies import get_optional_current_user
from app.services.disease_predictor import predictor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/predict")
async def predict_disease(
    file: UploadFile = File(...),
    current_user=Depends(get_optional_current_user),
):
    # ── 1. Validate upload ────────────────────────────────────────────────
    settings = get_settings()

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "Only image files allowed")

    # Phase 12: enforce the configured size limit before reading the whole
    # body into memory (DoS guard). Content-Length is a first check; the
    # streamed read below is the authoritative one.
    declared_size = file.size if getattr(file, "size", None) is not None else None
    if declared_size is not None and declared_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Image too large")

    # ── 2. AI inference ───────────────────────────────────────────────────
    try:
        image_bytes = await file.read()

        # Authoritative streamed-size check (Content-Length can be absent
        # or lying; a chunked/oversized body must still be rejected).
        if len(image_bytes) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(413, "Image too large")

        start_time = time.time()
        result = predictor.predict(image_bytes)
        inference_time = round((time.time() - start_time) * 1000, 2)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(500, "Prediction failed")

    logger.info(
        "Prediction ok: crop=%s disease=%s confidence=%.2f in %sms",
        result.get("crop"), result.get("disease"),
        result.get("confidence", 0.0), inference_time,
    )

    # ── 3. Persist (non-fatal: inference result is returned either way) ──
    # User attribution: the verified JWT subject is the ONLY trusted source
    # of user_id. Client-supplied identifiers are never accepted — the legacy
    # insecure ?user_id= query parameter was removed (Phase 4 security fix):
    # it allowed any caller to impersonate arbitrary users. Unauthenticated
    # scans are recorded as "anonymous".
    attributed_user_id = str(current_user["_id"]) if current_user else "anonymous"

    prediction_data = {
        "user_id": attributed_user_id,
        "image_url": f"/test_images/{uuid.uuid4()}.jpg",
        "crop": result.get("crop", "unknown"),
        "disease": result.get("disease", "unknown"),
        "confidence": result.get("confidence", 0.0),
        "is_healthy": result.get("is_healthy", False),
        "class_name": result.get("class_name", "unknown"),
        "class_index": result.get("class_index"),
        "inference_time_ms": inference_time,
        "created_at": datetime.utcnow()
    }

    prediction_id = None
    try:
        collection = db.database["predictions"]
        inserted = await collection.insert_one(prediction_data)
        prediction_id = str(inserted.inserted_id)
        logger.info("Prediction saved to MongoDB: %s", prediction_id)
    except Exception:
        logger.exception("MongoDB save failed for prediction")

    # ── 4. Response (contract: existing top-level fields unchanged; the
    # structured `result` dict now also carries the real model class_index) ──
    return {
        "success": True,
        "data": result,
        "inference_time_ms": inference_time,
        "saved_to_db": prediction_id is not None,
        "prediction_id": prediction_id,
    }
