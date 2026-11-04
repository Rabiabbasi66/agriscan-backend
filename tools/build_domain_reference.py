# backend/tools/build_domain_reference.py
#
# Builds models/domain_guard.npz, the calibration data used by the plant-domain
# gate: one embedding centroid per trained class (from the training split) and
# the style threshold (1st percentile of the held-out validation split).
#
# Run after retraining or replacing best.pt:
#   python tools/build_domain_reference.py
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO
from ultralytics.data.augment import classify_transforms

TRAIN_PER_CLASS = 30
VAL_PER_CLASS = 20
IMGSZ = 224


def embed(model, net, transform, paths):
    buffer = {}
    net.model[-1].linear.register_forward_pre_hook(
        lambda _module, inputs: buffer.__setitem__("x", inputs[0].detach())
    )
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), 32):
            batch = torch.stack([transform(Image.open(p).convert("RGB")) for p in paths[i:i + 32]])
            net.model(batch)
            out.append(buffer["x"].numpy().astype(np.float32))
    return np.concatenate(out)


def sample(split: Path, per_class: int, seed: int):
    rng = np.random.default_rng(seed)
    paths = []
    for cls in sorted(p.name for p in split.iterdir()):
        files = sorted((split / cls).iterdir())
        pick = rng.choice(len(files), size=min(per_class, len(files)), replace=False)
        paths += [files[j] for j in pick]
    return paths


def main() -> None:
    torch.set_num_threads(4)
    data = BACKEND_DIR / "plantvillage_dataset"
    model = YOLO(str(BACKEND_DIR / "models" / "best.pt"))
    net = model.model.eval()
    transform = classify_transforms(IMGSZ)
    classes = [model.names[i] for i in range(len(model.names))]

    train_paths = sample(data / "train", TRAIN_PER_CLASS, seed=0)
    train_x = embed(model, net, transform, train_paths)
    # Sample paths are grouped per class in sorted order.
    labels = np.repeat(np.arange(len(classes)), TRAIN_PER_CLASS)[: len(train_x)]
    centroids = np.stack([train_x[labels == c].mean(0) for c in range(len(classes))])

    val_paths = sample(data / "val", VAL_PER_CLASS, seed=0)
    val_x = embed(model, net, transform, val_paths)
    unit = val_x / np.maximum(np.linalg.norm(val_x, axis=1, keepdims=True), 1e-9)
    normed_centroids = centroids / np.maximum(np.linalg.norm(centroids, axis=1, keepdims=True), 1e-9)
    style = (unit @ normed_centroids.T).max(1)
    style_threshold = float(np.percentile(style, 1))

    out = BACKEND_DIR / "models" / "domain_guard.npz"
    np.savez(
        out,
        centroids=centroids.astype(np.float32),
        style_threshold=np.float32(style_threshold),
        imgsz=np.int32(IMGSZ),
        classes=np.array(classes),
    )
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
    print(f"style threshold (val 1st percentile) = {style_threshold:.4f}")
    print(f"val similarity median = {np.median(style):.4f}, min = {style.min():.4f}")


if __name__ == "__main__":
    main()
