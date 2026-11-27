"""Merge PlantDoc real-field images into the PlantVillage YOLO-cls dataset.

PlantDoc class folders use free-text names ("Tomato Early blight leaf") while
PlantVillage uses "Crop___Disease". This script maps the 27 PlantDoc classes
onto the matching PlantVillage class names, then appends each image to the
existing train/ or val/ folder with an 80/20 split — identical to the
PlantVillage layout Ultralytics expects.

Usage:  python merge_plantdoc.py
"""
import os
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "plantdoc_raw"
DATASET = ROOT / "plantvillage_dataset"
SEED = 42
VAL_FRACTION = 0.20
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# PlantDoc folder -> PlantVillage "Crop___Disease" class name.
# PlantDoc's bare "<crop> leaf" folders are healthy plants.
CLASS_MAP = {
    "Apple Scab Leaf": "Apple___Apple_scab",
    "Apple leaf": "Apple___healthy",
    "Apple rust leaf": "Apple___Cedar_apple_rust",
    "Bell_pepper leaf": "Pepper,_bell___healthy",
    "Bell_pepper leaf spot": "Pepper,_bell___Bacterial_spot",
    "Blueberry leaf": "Blueberry___healthy",
    "Cherry leaf": "Cherry_(including_sour)___healthy",
    "Corn Gray leaf spot": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn leaf blight": "Corn_(maize)___Northern_Leaf_Blight",
    "Corn rust leaf": "Corn_(maize)___Common_rust_",
    "Peach leaf": "Peach___healthy",
    "Potato leaf early blight": "Potato___Early_blight",
    "Potato leaf late blight": "Potato___Late_blight",
    "Raspberry leaf": "Raspberry___healthy",
    "Soyabean leaf": "Soybean___healthy",
    "Squash Powdery mildew leaf": "Squash___Powdery_mildew",
    "Strawberry leaf": "Strawberry___healthy",
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato Septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "Tomato leaf": "Tomato___healthy",
    "Tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "Tomato leaf late blight": "Tomato___Late_blight",
    "Tomato leaf mosaic virus": "Tomato___Tomato_mosaic_virus",
    "Tomato leaf yellow virus": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato mold leaf": "Tomato___Leaf_Mold",
    "Tomato two spotted spider mites leaf": "Tomato___Spider_mites Two-spotted_spider_mite",
    "grape leaf": "Grape___healthy",
    "grape leaf black rot": "Grape___Black_rot",
}


def collect_images(split_dir: Path):
    """Return {plantdoc_folder: [image paths]} for one PlantDoc split."""
    out = {}
    for folder in sorted(split_dir.iterdir()):
        if not folder.is_dir():
            continue
        imgs = [p for p in folder.iterdir()
                if p.suffix.lower() in IMG_EXT and p.is_file()]
        if imgs:
            out[folder.name] = imgs
    return out


def main():
    if not RAW.is_dir():
        raise SystemExit(f"PlantDoc checkout not found at {RAW}")

    rng = random.Random(SEED)
    splits = {"train": collect_images(RAW / "train"),
              "test": collect_images(RAW / "test")}

    added = {"train": 0, "val": 0}
    skipped = []

    for split_name, folders in splits.items():
        for pd_name, pv_name in CLASS_MAP.items():
            imgs = folders.get(pd_name)
            if not imgs:
                continue
            rng.shuffle(imgs)
            n_val = max(1, round(len(imgs) * VAL_FRACTION)) if len(imgs) > 3 else 0
            for i, src in enumerate(imgs):
                target_split = "val" if i < n_val else "train"
                dst_dir = DATASET / target_split / pv_name
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / f"plantdoc_{split_name}_{src.name}"
                # Names can collide across PlantDoc train/test; prefix handles it.
                if dst.exists():
                    dst = dst_dir / f"plantdoc_{split_name}_{i}_{src.name}"
                try:
                    shutil.copy2(src, dst)
                    added[target_split] += 1
                except OSError as exc:
                    skipped.append((str(src), str(exc)))

    for pd_name in CLASS_MAP:
        if pd_name not in splits["train"] and pd_name not in splits["test"]:
            skipped.append((pd_name, "folder missing in PlantDoc"))

    print(f"Added to train: {added['train']} images")
    print(f"Added to val:   {added['val']} images")
    if skipped:
        print(f"Skipped {len(skipped)}:")
        for s, why in skipped[:20]:
            print("  -", s, "->", why)


if __name__ == "__main__":
    main()
