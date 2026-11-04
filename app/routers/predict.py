# Single-image prediction endpoint for the frontend scanner.
# Flow: validate upload → trained YOLOv8 inference (backend/models/best.pt) →
# persist to MongoDB → respond.
# Contract: {success, data, inference_time_ms, saved_to_db, prediction_id}.
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.database import db
from app.config import get_settings
from app.dependencies import get_optional_current_user
from app.services.disease_predictor import (
    DomainGuardUnavailableError,
    InvalidImageError,
    ModelNotReadyError,
    UnsupportedImageError,
    get_predictor,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_inference(image_bytes: bytes) -> dict:
    """Blocking model call, always executed in the threadpool."""
    return get_predictor().predict(image_bytes)


@router.post("/predict")
async def predict_disease(
    file: UploadFile = File(...),
    current_user=Depends(get_optional_current_user),
):
    settings = get_settings()

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "Only image files allowed")

    # Enforce the configured size limit before reading the whole body into
    # memory (DoS guard). Content-Length is a first check; the streamed read
    # below is the authoritative one.
    declared_size = file.size if getattr(file, "size", None) is not None else None
    if declared_size is not None and declared_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Image too large")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty upload")
    if len(image_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Image too large")

    # Inference runs off the event loop.
    start_time = time.perf_counter()
    try:
        result = await run_in_threadpool(_run_inference, image_bytes)
    except InvalidImageError as exc:
        logger.info("Rejected upload: %s", exc)
        raise HTTPException(400, str(exc))
    except UnsupportedImageError as exc:
        # Decodable image, but not a supported plant leaf: no disease is
        # reported and nothing is persisted.
        logger.info("Unsupported image: %s", exc)
        raise HTTPException(415, str(exc))
    except DomainGuardUnavailableError as exc:
        # Validation cannot run, so the image cannot be proven supported. No
        # disease is produced and nothing is persisted.
        logger.error("Plant-domain validation unavailable: %s", exc)
        raise HTTPException(
            503,
            "AI image validation is temporarily unavailable, so this image "
            "cannot be verified as a supported plant leaf. Nothing was "
            "analysed — please try again shortly.",
        )
    except ModelNotReadyError as exc:
        logger.error("AI model unavailable: %s", exc)
        raise HTTPException(503, "AI model unavailable")
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(500, "Prediction failed")

    inference_time = round((time.perf_counter() - start_time) * 1000, 2)

    logger.info(
        "Prediction ok: crop=%s disease=%s confidence=%.2f detected=%s in %sms",
        result.get("crop"), result.get("disease"),
        result.get("confidence", 0.0), result.get("detected"), inference_time,
    )

    # Persistence is non-fatal: the inference result is returned either way.
    # The verified JWT subject is the only trusted source of user_id;
    # unauthenticated scans are attributed to "anonymous".
    attributed_user_id = str(current_user["_id"]) if current_user else "anonymous"

    prediction_data = {
        "user_id": attributed_user_id,
        # The upload is not retained, so there is no image URL to claim.
        "image_url": None,
        "detected": bool(result.get("detected", False)),
        "crop": result.get("crop", "unknown"),
        "disease": result.get("disease", "unknown"),
        "confidence": result.get("confidence", 0.0),
        "is_healthy": result.get("is_healthy", False),
        "class_name": result.get("class_name", "unknown"),
        "class_index": result.get("class_index"),
        "top_k": result.get("top_k", []),
        "inference_time_ms": result.get("inference_time_ms", inference_time),
        "preprocess_time_ms": result.get("preprocess_time_ms"),
        "created_at": datetime.utcnow(),
    }

    prediction_id = None
    if db.database is None:
        logger.warning("Prediction not persisted: MongoDB is unavailable")
    else:
        try:
            collection = db.database["predictions"]
            inserted = await collection.insert_one(prediction_data)
            prediction_id = str(inserted.inserted_id)
            logger.info("Prediction saved to MongoDB: %s", prediction_id)
        except Exception:
            logger.exception("MongoDB save failed for prediction")

    return {
        "success": True,
        "data": result,
        "inference_time_ms": inference_time,
        "saved_to_db": prediction_id is not None,
        "prediction_id": prediction_id,
    }
