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

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.database import db
from app.services.disease_predictor import predictor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/predict")
async def predict_disease(
    file: UploadFile = File(...),
    user_id: str = None
):
    # ── 1. Validate upload ────────────────────────────────────────────────
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files allowed")

    # ── 2. AI inference ───────────────────────────────────────────────────
    try:
        image_bytes = await file.read()

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
    prediction_data = {
        "user_id": user_id or "anonymous",
        "image_url": f"/test_images/{uuid.uuid4()}.jpg",
        "crop": result.get("crop", "unknown"),
        "disease": result.get("disease", "unknown"),
        "confidence": result.get("confidence", 0.0),
        "is_healthy": result.get("is_healthy", False),
        "class_name": result.get("class_name", "unknown"),
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

    # ── 4. Response (contract unchanged) ─────────────────────────────────
    return {
        "success": True,
        "data": result,
        "inference_time_ms": inference_time,
        "saved_to_db": prediction_id is not None,
        "prediction_id": prediction_id,
    }
