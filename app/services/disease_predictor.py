# Inference for the trained PlantVillage classifier at backend/models/best.pt
# (YOLOv8n-cls, 38 classes, imgsz 224).
#
# Class names come from the checkpoint itself (model.names), never from a
# hand-maintained list that can drift from the weights.
#
# Weights are loaded once per process; predict() is guarded by a lock because a
# single Ultralytics model instance is not safe for concurrent calls.
from __future__ import annotations

import io
import logging
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.services.disease_info import get_category, get_disease_info

logger = logging.getLogger(__name__)

# Architecture of the deployed checkpoint (Ultralytics YOLOv8 nano classifier).
# Reported with every prediction so the UI never has to hardcode it.
MODEL_NAME = "YOLOv8n-cls"

# backend/ — weights are resolved relative to the package, not the shell CWD.
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Pillow formats the scanner accepts. Anything else is an unsupported format.
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}

# Longest edge handed to the model. The classifier resizes to imgsz internally,
# so decoding a multi-megapixel drone frame only wastes CPU/bandwidth here.
MAX_INFERENCE_EDGE = 512


class InvalidImageError(ValueError):
    """The uploaded bytes are not a decodable, supported image."""


class ModelNotReadyError(RuntimeError):
    """The trained weights could not be loaded."""


class UnsupportedImageError(ValueError):
    """The image is decodable but is not a supported plant leaf."""


class DomainGuardUnavailableError(RuntimeError):
    """Validation is unavailable, so no image can be verified as supported."""


class DiseasePredictor:
    def __init__(self, model_path: str | Path | None = None):
        settings = get_settings()

        raw_path = Path(model_path or settings.YOLO_MODEL_PATH)
        self.model_path = raw_path if raw_path.is_absolute() else BACKEND_DIR / raw_path
        if not self.model_path.is_file():
            raise ModelNotReadyError(f"Trained weights not found: {self.model_path}")

        # Heavy import kept local so the API can boot without torch loaded.
        from ultralytics import YOLO

        self.model = YOLO(str(self.model_path))

        model_task = getattr(self.model, "task", None) or "classify"
        if model_task != "classify":
            raise ModelNotReadyError(
                f"Expected a classification checkpoint, got task={model_task!r}"
            )

        # Single source of truth for class mapping: the checkpoint's own names.
        names = getattr(self.model, "names", None) or {}
        if not names:
            raise ModelNotReadyError("Checkpoint contains no class names")
        self.class_names = [names[i] for i in range(len(names))]
        self.num_classes = len(self.class_names)

        # Image size used during training (224 for this checkpoint).
        train_args = (getattr(self.model, "ckpt", None) or {}).get("train_args") or {}
        self.image_size = int(train_args.get("imgsz") or 224)
        self.min_confidence = float(settings.YOLO_CONFIDENCE_THRESHOLD)

        self._lock = threading.Lock()
        self._warmed_up = False

        # Capture the 1280-d embedding that feeds the classifier head without
        # a second forward pass; the domain guard scores it. Inference is
        # serialised by self._lock, so a single buffer is safe.
        self._features = None
        self._feature_hook = None
        try:
            # YOLO -> ClassificationModel -> Sequential(nn.Module) -> Classify
            target = self.model.model.model[-1].linear
            self._feature_hook = target.register_forward_pre_hook(self._capture_features)
        except (AttributeError, IndexError):
            logger.warning("Classifier embedding unavailable; feature domain signal disabled")

        logger.info(
            "Loaded trained YOLOv8 weights: %s (task=%s, classes=%d, imgsz=%d)",
            self.model_path, model_task, self.num_classes, self.image_size,
        )

    def _capture_features(self, _module, inputs):
        self._features = inputs[0].detach()

    # ── preprocessing ─────────────────────────────────────────────────────
    def _preprocess(self, image_bytes: bytes) -> Image.Image:
        """Decode an upload into an RGB PIL image ready for inference."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as source:
                image_format = (source.format or "").upper()
                if image_format and image_format not in SUPPORTED_FORMATS:
                    raise InvalidImageError(
                        f"Unsupported image format: {image_format}. "
                        f"Use {', '.join(sorted(SUPPORTED_FORMATS))}."
                    )

                # JPEG only: decode straight to a reduced DCT scale instead of
                # decoding 12 MP frames at full resolution (verified identical
                # top-1 labels on upscaled dataset images vs a full decode).
                source.draft("RGB", (MAX_INFERENCE_EDGE, MAX_INFERENCE_EDGE))
                image = ImageOps.exif_transpose(source).convert("RGB")
        except InvalidImageError:
            raise
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise InvalidImageError("File is not a readable image") from exc

        if max(image.size) > MAX_INFERENCE_EDGE:
            image.thumbnail((MAX_INFERENCE_EDGE, MAX_INFERENCE_EDGE), Image.BILINEAR)

        return image

    # ── inference ─────────────────────────────────────────────────────────
    def predict(self, image_bytes: bytes) -> dict:
        preprocess_start = time.perf_counter()
        image = self._preprocess(image_bytes)
        preprocess_ms = round((time.perf_counter() - preprocess_start) * 1000, 2)

        # Validation is mandatory: without it an unverified image must not
        # receive a diagnosis, so a missing gate aborts the scan (503).
        guard = _get_guard()

        # Cheap quality floor before paying for two forward passes.
        variance = guard.blur_variance(image)
        if variance < guard.blur_threshold:
            raise UnsupportedImageError(
                "Unsupported image: the photo is too blurry or has too "
                "little detail to analyse. Upload a sharp, close-up photo "
                "of a single leaf."
            )

        inference_start = time.perf_counter()
        with self._lock:
            results = self.model.predict(
                source=image,
                imgsz=self.image_size,
                verbose=False,
            )
            features = self._features.numpy().reshape(-1) if self._features is not None else None
        inference_ms = round((time.perf_counter() - inference_start) * 1000, 2)

        if features is None:
            raise DomainGuardUnavailableError(
                "Classifier embedding unavailable; the image cannot be validated"
            )

        decision = guard.evaluate(image, features)
        if not decision.supported:
            raise UnsupportedImageError(decision.reason or "Unsupported image")

        probs = results[0].probs if results else None
        if probs is None:
            raise ModelNotReadyError("Checkpoint returned no classification output")

        top_idx = int(probs.top1)
        confidence = float(probs.top1conf)
        class_name = self.class_names[top_idx] if 0 <= top_idx < self.num_classes \
            else f"class_{top_idx}"

        top_k = [
            {
                "class_name": self.class_names[int(i)],
                "confidence": round(float(c) * 100, 2),
                **_parse_class_name(self.class_names[int(i)]),
            }
            for i, c in zip(probs.top5, probs.top5conf)
        ]

        detected = confidence >= self.min_confidence

        if detected:
            parsed = _parse_class_name(class_name)
            crop, disease = parsed["crop"], parsed["disease"]
            is_healthy = "healthy" in disease.lower()
            category = get_category(class_name)
            # Reference text exists only for a class the model actually
            # predicted; an abstained result carries no disease content.
            disease_info = get_disease_info(class_name)
        else:
            # Never invent a disease for an image the model is unsure about.
            crop, disease = "unknown", "No confident detection"
            is_healthy = False
            category = get_category(None)
            disease_info = None

        return {
            "detected": detected,
            "disease": disease,
            "crop": crop,
            "category": category,
            "confidence": round(confidence * 100, 2),
            "is_healthy": is_healthy,
            "class_name": class_name,
            "class_index": top_idx,
            "top_k": top_k,
            "supported": True,
            "disease_info": disease_info,
            "model_name": MODEL_NAME,
            "model_file": self.model_path.name,
            "num_classes": self.num_classes,
            "confidence_threshold": round(self.min_confidence * 100, 2),
            # None when the style signal alone accepted the image and the
            # ImageNet pass was skipped (see DomainGuard.evaluate).
            "plant_score": (
                round(decision.plant_score, 4)
                if decision and decision.plant_score is not None
                else None
            ),
            "style_similarity": round(decision.style_similarity, 4) if decision else None,
            "preprocess_time_ms": preprocess_ms,
            "inference_time_ms": inference_ms,
        }

    def warm_up(self) -> None:
        """Run one dummy inference so the first real request is not slow."""
        if self._warmed_up:
            return
        # A guard failure is logged here but still blocks scans at request
        # time; warm-up itself must not take the whole service down.
        try:
            _get_guard().warm_up()
        except Exception:
            logger.exception("Plant-domain gate unavailable at start-up")
        try:
            import numpy as np

            blank = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
            with self._lock:
                self.model.predict(source=blank, imgsz=self.image_size, verbose=False)
            self._warmed_up = True
            logger.info("YOLOv8 inference pipeline warmed up")
        except Exception:  # non-fatal: the first request just pays the cost
            logger.exception("YOLOv8 warm-up failed")


def _parse_class_name(full_name: str) -> dict:
    """Split a PlantVillage class name (Crop___Disease) into readable parts."""
    parts = full_name.split("___")
    if len(parts) == 2:
        return {
            "crop": parts[0].replace("_", " ").strip(),
            "disease": parts[1].replace("_", " ").strip(),
        }
    return {"crop": "Unknown", "disease": full_name.replace("_", " ").strip()}


_guard_unavailable = False


def _get_guard():
    """Domain guard singleton; raises when validation cannot be performed.

    Failing closed is deliberate: an unvalidated image must never be handed a
    disease label, so callers surface a service-unavailable error instead.
    """
    global _guard_unavailable
    if _guard_unavailable:
        raise DomainGuardUnavailableError("Plant-domain gate could not be loaded")
    try:
        from app.services.domain_guard import get_guard

        return get_guard()
    except Exception as exc:
        _guard_unavailable = True
        logger.exception(
            "Plant-domain gate unavailable - refusing to analyse images"
        )
        raise DomainGuardUnavailableError("Plant-domain gate could not be loaded") from exc


_predictor: DiseasePredictor | None = None
_predictor_lock = threading.Lock()


def get_predictor() -> DiseasePredictor:
    """Process-wide singleton: the weights are loaded once and kept in memory."""
    global _predictor
    if _predictor is None:
        with _predictor_lock:
            if _predictor is None:
                _predictor = DiseasePredictor()
    return _predictor
