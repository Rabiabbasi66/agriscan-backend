# train_model_v2.py — PlantVillage + PlantDoc merged dataset
# Fast config: yolov8n-cls @320px, 40 epochs (~5-6 hrs on Colab T4)
# Upload plantvillage_dataset folder (merged) to Colab, then run this.
from ultralytics import YOLO

print("=" * 60)
print("AGRISCAN 3D - YOLOv8n-cls v2 TRAINING (PV + PlantDoc)")
print("=" * 60)

model = YOLO('yolov8n-cls.pt')

results = model.train(
    data="plantvillage_dataset",
    epochs=40,
    imgsz=320,
    batch=64,
    device=0,            # Colab GPU
    workers=4,
    patience=8,
    project="agriscan_model",
    name="classification_v2",
    exist_ok=True,
    verbose=True
)

print("\n" + "=" * 60)
print("DONE! Model: agriscan_model/classification_v2/weights/best.pt")
print("Download it -> backend/models/best.pt -> modal deploy modal_app.py")
print("=" * 60)
