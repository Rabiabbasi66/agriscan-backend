

from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

SEVERITY_MAP: dict[str, Literal["high", "medium", "low", "healthy"]] = {
    "Healthy": "healthy",
    "Leaf_Blight": "high",
    "Powdery_Mildew": "medium",
    "Root_Rot": "high",
    "Wheat_Rust": "low",
    "Downy_Mildew": "medium",
    "Septoria_Leaf_Spot": "medium",
    "Fusarium_Wilt": "high",
    "Bacterial_Blight": "high",
    "Early_Blight": "medium",
    "Late_Blight": "high",
}

BOX_COLORS: dict[str, tuple[int, int, int]] = {
    "healthy": (57, 255, 20),
    "high": (32, 32, 255),
    "medium": (32, 144, 255),
    "low": (20, 204, 255),
}

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
            model_path = settings.YOLO_MODEL_PATH
            if not Path(model_path).exists():
                logger.warning(
                    "Custom model %s not found — loading YOLOv8n as base (no disease classes).",
                    model_path,
                )
                _model = YOLO("yolov8n.pt")
            else:
                _model = YOLO(model_path)
            logger.info("YOLOv8 model loaded: %s", model_path)
        except ImportError:
            logger.error("ultralytics not installed — install it with: pip install ultralytics")
            raise
    return _model


def run_detection(image: np.ndarray) -> dict:
    """
    Run YOLOv8 on a BGR numpy array.
    Returns:
        {
          detections: [{label, confidence, bbox, severity}],
          annotated_image: np.ndarray  (BGR),
          health_score: float,
          processing_time_s: float,
        }
    """
    t0 = time.perf_counter()
    model = _get_model()

    # Guard: the trained checkpoint is a classifier (yolov8n-cls). Running it
    # through this detection path would silently return zero boxes ("healthy"),
    # so refuse instead of reporting a false negative.
    if getattr(model, "task", None) == "classify":
        raise RuntimeError(
            "run_detection() requires a detection checkpoint; "
            "YOLO_MODEL_PATH points to a classifier. Use DiseasePredictor."
        )

    results = model.predict(
        source=image,
        conf=settings.YOLO_CONFIDENCE_THRESHOLD,
        iou=settings.YOLO_IOU_THRESHOLD,
        verbose=False,
    )[0]

    detections = []
    annotated = image.copy()

    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = model.names.get(cls_id, f"class_{cls_id}")
        conf = float(box.conf[0])
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        severity = SEVERITY_MAP.get(label, "medium")
        color = BOX_COLORS[severity]

        # Draw bounding box
        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        # Corner brackets
        for (cx, cy, dx, dy) in [
            (int(x1), int(y1), 1, 1), (int(x2), int(y1), -1, 1),
            (int(x1), int(y2), 1, -1), (int(x2), int(y2), -1, -1),
        ]:
            cv2.line(annotated, (cx, cy), (cx + dx * 14, cy), color, 3)
            cv2.line(annotated, (cx, cy), (cx, cy + dy * 14), color, 3)
        # Label background
        label_text = f"{label.replace('_', ' ')} {conf * 100:.1f}%"
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        ly = int(y1) - 4 if int(y1) > 20 else int(y2) + 16
        cv2.rectangle(annotated, (int(x1), ly - th - 4), (int(x1) + tw + 8, ly + 2), color, -1)
        cv2.putText(annotated, label_text, (int(x1) + 4, ly - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (10, 10, 10), 1, cv2.LINE_AA)

        detections.append({
            "label": label,
            "confidence": round(conf * 100, 2),
            "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            "severity": severity,
        })

    # Health score: share of healthy detections (no detections → fully healthy).
    total = len(detections)
    healthy = sum(1 for d in detections if d["severity"] == "healthy")
    health_score = 100.0 if total == 0 else round(healthy / total * 100.0, 1)

    processing_time_s = time.perf_counter() - t0
    logger.debug("Detection finished: %d boxes, health=%.1f%%, %.3fs", total, health_score, processing_time_s)

    return {
        "detections": detections,
        "annotated_image": annotated,
        "health_score": health_score,
        "processing_time_s": round(processing_time_s, 3),
    }


def encode_image_to_bytes(image: np.ndarray) -> bytes:
    """Encode a BGR numpy image to JPEG bytes (used before uploading to S3)."""
    ok, buf = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Failed to encode annotated image to JPEG")
    return buf.tobytes()
