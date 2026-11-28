"""Generate a large, fully-labelled confusion matrix for the thesis.

Runs the deployed checkpoint over the local validation split and renders a
publication-size figure (labels are not clipped). Output:
  runs/classify/val/confusion_matrix_large.png
"""
import os
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.expanduser("~"), ".matplotlib"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "plantvillage_dataset")
MODEL = os.path.join(ROOT, "models", "best.pt")
OUT = os.path.join(ROOT, "runs", "classify", "val", "confusion_matrix_large.png")

model = YOLO(MODEL)
names = model.names  # {idx: class_name}
n_classes = len(names)
label_to_idx = {v: k for k, v in names.items()}

# Validation images are organised as val/<ClassName>/<img>
val_dir = os.path.join(DATA, "val")
cm = np.zeros((n_classes, n_classes), dtype=np.int64)
total = correct = 0

for cls_name in sorted(os.listdir(val_dir)):
    cls_dir = os.path.join(val_dir, cls_name)
    if not os.path.isdir(cls_dir):
        continue
    true_idx = label_to_idx[cls_name]
    files = [f for f in os.listdir(cls_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    for i in range(0, len(files), 32):
        batch_paths = [os.path.join(cls_dir, f) for f in files[i:i + 32]]
        results = model.predict(batch_paths, imgsz=224, device="cpu", verbose=False)
        for r in results:
            pred_idx = int(r.probs.top1)
            cm[true_idx, pred_idx] += 1
            total += 1
            correct += int(pred_idx == true_idx)

print(f"Evaluated {total} images, top-1 acc = {correct / total:.4f}")

# Normalise rows for readability
cm_norm = cm.astype(float) / np.maximum(cm.sum(axis=1, keepdims=True), 1)

short = [names[i].replace("___", " / ") for i in range(n_classes)]
fig_w = max(24, n_classes * 0.55)
fig, ax = plt.subplots(figsize=(fig_w, fig_w * 0.85))
im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)

ax.set_xticks(range(n_classes))
ax.set_yticks(range(n_classes))
ax.set_xticklabels(short, rotation=90, fontsize=6, ha="center")
ax.set_yticklabels(short, fontsize=6)
ax.set_xlabel("Predicted class", fontsize=12)
ax.set_ylabel("True class", fontsize=12)
ax.set_title("Confusion Matrix — YOLOv8n-cls on PlantVillage validation set (10,876 images)", fontsize=14)

# Annotate only cells with meaningful counts to keep it readable
thresh = cm.max() * 0.02
for i in range(n_classes):
    for j in range(n_classes):
        if cm[i, j] > 0:
            v = cm_norm[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=4.5,
                    color="white" if v > 0.5 else "black")

fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Row-normalised accuracy")
plt.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=200, bbox_inches="tight")
print("Saved:", OUT)
