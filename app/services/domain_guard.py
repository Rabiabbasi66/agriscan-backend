# app/services/domain_guard.py
#
# Plant-domain validation for the image scanner.
#
# The trained checkpoint is a 38-class PlantVillage classifier: a high softmax
# probability only means "closest of those 38 classes", so a car or a portrait
# can still be labelled with 90% confidence. To decide whether an upload is a
# plant leaf at all, two independent signals are combined:
#
#   1. Semantic: an ImageNet-pretrained YOLOv8n-cls (backend/yolov8n-cls.pt,
#      already in the repo) scores how much the image looks like any of the
#      ImageNet plant classes (leafy crops, fruit, flowers, fungi).
#   2. Feature: cosine similarity between the trained classifier's 1280-d
#      embedding and the nearest PlantVillage class centroid.
#
# An image is accepted when EITHER signal is above its threshold. Measured on
# held-out data (see tools/build_domain_reference.py): 0/380 PlantVillage
# validation leaf images rejected, 32/33 real non-plant photos rejected, 7/7
# real field leaf photos accepted.
#
# Thresholds are calibrated offline, never on training images, and are read
# from the reference artifact so retraining can refresh them.
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]

# ImageNet classes that mean "plant". Resolved by name against torchvision's
# bundled ImageNet category list (no download): the pretrained checkpoint and
# torchvision share the same 1000-class ordering.
PLANT_CLASS_NAMES = (
    "daisy", "yellow lady's slipper", "corn", "acorn", "hip,", "buckeye",
    "coral fungus", "agaric", "gyromitra", "stinkhorn", "earthstar",
    "hen-of-the-woods", "bolete", "head cabbage", "broccoli", "cauliflower",
    "zucchini", "spaghetti squash", "acorn squash", "butternut squash",
    "cucumber", "artichoke", "bell pepper", "cardoon", "mushroom", "strawberry",
    "orange", "lemon", "fig,", "pineapple", "banana", "jackfruit",
    "custard apple", "pomegranate", "rapeseed", "pot, flowerpot",
)


class DomainReferenceMissing(RuntimeError):
    """The calibrated reference artifact is absent."""


@dataclass
class DomainDecision:
    supported: bool
    # None when the ImageNet pass was skipped because the style signal alone
    # already accepted the image (see evaluate()).
    plant_score: float | None
    style_similarity: float
    reason: str | None = None


class DomainGuard:
    def __init__(self, model_path: Path, reference_path: Path):
        from ultralytics import YOLO
        from torchvision.models import ResNet50_Weights

        if not model_path.is_file():
            raise DomainReferenceMissing(f"Plant gate weights not found: {model_path}")
        if not reference_path.is_file():
            raise DomainReferenceMissing(f"Domain reference not found: {reference_path}")

        self.model_path = model_path
        self.model = YOLO(str(model_path))
        if getattr(self.model, "task", None) != "classify":
            raise DomainReferenceMissing("Plant gate must be a classification model")

        categories = ResNet50_Weights.IMAGENET1K_V2.meta["categories"]
        found = [i for i, name in enumerate(categories) if name in PLANT_CLASS_NAMES]
        if len(found) < 30:
            raise DomainReferenceMissing(
                f"Only {len(found)} ImageNet plant classes resolved; category map mismatch"
            )
        self.plant_indices = np.array(found)

        ref = np.load(reference_path)
        centroids = ref["centroids"].astype(np.float32)
        norms = np.linalg.norm(centroids, axis=1, keepdims=True)
        self.centroids = centroids / np.maximum(norms, 1e-9)
        self.style_threshold = float(ref["style_threshold"])
        self.image_size = int(ref["imgsz"]) if "imgsz" in ref else 224

        settings = get_settings()
        self.plant_threshold = float(settings.PLANT_SCORE_THRESHOLD)
        self.blur_threshold = float(settings.BLUR_VARIANCE_THRESHOLD)

        from ultralytics.data.augment import classify_transforms

        self._transform = classify_transforms(self.image_size)
        self._lock = threading.Lock()
        self._warmed_up = False

        logger.info(
            "Plant-domain gate ready: %d ImageNet plant classes, plant>=%.3f or "
            "style>=%.3f, blur>=%.1f",
            len(self.plant_indices), self.plant_threshold, self.style_threshold,
            self.blur_threshold,
        )

    # ── signals ──────────────────────────────────────────────────────────
    def plant_score(self, image: Image.Image) -> float:
        """Probability mass on ImageNet plant classes (0..1)."""
        import torch

        with self._lock:
            tensor = self._transform(image).unsqueeze(0)
            with torch.no_grad():
                probs = self.model.model(tensor)[0][0].numpy()
        return float(probs[self.plant_indices].sum())

    def style_similarity(self, features: np.ndarray) -> float:
        """Cosine similarity to the nearest PlantVillage class centroid."""
        vector = np.asarray(features, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if norm <= 0:
            return 0.0
        return float((self.centroids @ (vector / norm)).max())

    @staticmethod
    def blur_variance(image: Image.Image) -> float:
        """Variance of the 4-neighbour Laplacian; low values mean no detail.

        Applied with slicing rather than sliding_window_view: the windowed
        version materialised an (H-2, W-2, 3, 3) array (66 ms per 512 px image),
        this is identical arithmetic in ~1 ms, so the calibrated threshold
        keeps its exact meaning.
        """
        grey = image.convert("L")
        if max(grey.size) > 512:
            grey = grey.copy()
            grey.thumbnail((512, 512))
        pixels = np.asarray(grey, dtype=np.float32)
        if pixels.shape[0] < 3 or pixels.shape[1] < 3:
            return 0.0
        laplacian = (
            pixels[:-2, 1:-1]
            + pixels[2:, 1:-1]
            + pixels[1:-1, :-2]
            + pixels[1:-1, 2:]
            - 4.0 * pixels[1:-1, 1:-1]
        )
        return float(laplacian.var())

    # ── decision ─────────────────────────────────────────────────────────
    def evaluate(self, image: Image.Image, features: np.ndarray) -> DomainDecision:
        """Combine both signals; OR semantics, ordered by cost.

        The style signal is a dot product against cached centroids; the
        ImageNet pass is a second neural forward pass (measured ~81 ms).
        Because the decision is an OR, a style score already above its
        threshold accepts the image without paying for that pass.
        """
        style = self.style_similarity(features)
        if style >= self.style_threshold:
            return DomainDecision(True, None, style)

        plant = self.plant_score(image)
        if plant >= self.plant_threshold:
            return DomainDecision(True, plant, style)

        return DomainDecision(
            False, plant, style,
            "Unsupported image: this does not look like a plant leaf. "
            "Upload a close-up photo of a crop leaf (the model covers 38 "
            "PlantVillage fruit and vegetable classes).",
        )

    def warm_up(self) -> None:
        if self._warmed_up:
            return
        try:
            self.plant_score(Image.new("RGB", (self.image_size, self.image_size)))
            self._warmed_up = True
        except Exception:
            logger.exception("Plant-domain gate warm-up failed")


_guard: DomainGuard | None = None
_guard_lock = threading.Lock()


def get_guard() -> DomainGuard:
    global _guard
    if _guard is None:
        with _guard_lock:
            if _guard is None:
                settings = get_settings()
                model = Path(settings.PLANT_GATE_MODEL_PATH)
                reference = Path(settings.DOMAIN_REFERENCE_PATH)
                _guard = DomainGuard(
                    model if model.is_absolute() else BACKEND_DIR / model,
                    reference if reference.is_absolute() else BACKEND_DIR / reference,
                )
    return _guard
