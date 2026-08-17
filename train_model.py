# train_model.py
from ultralytics import YOLO
import os

print("=" * 60)
print("🤖 AGRISCAN 3D - YOLOv8 TRAINING START")
print("=" * 60)

# Dataset check
if not os.path.exists("plantvillage_dataset"):
    print("❌ Dataset not found!")
    print("📁 Please run organize_dataset.py first.")
    exit()

print("📁 Dataset ready!")
print(f"📊 Location: {os.path.abspath('plantvillage_dataset')}")

# Class count check
classes = os.listdir("plantvillage_dataset/train")
print(f"📚 Total classes: {len(classes)}")

# Model load
print("\n📥 Loading YOLOv8 model...")
model = YOLO('yolov8n-cls.pt')

print("\n🚀 Starting training on CPU...")
print("⏱️ Estimated time: 2-3 hours (15 epochs)")
print("💡 Keep your laptop plugged in")
print("💡 Don't close terminal\n")

# Training
results = model.train(
    data="plantvillage_dataset",
    epochs=15,           # 15 epochs
    imgsz=224,           # Image size
    batch=16,  # Change in train_model.py    
    device='cpu',        # CPU par train
    workers=4,
    patience=5,          # Early stopping
    project="agriscan_model",
    name="classification_v1",
    exist_ok=True,
    verbose=True
)

print("\n" + "=" * 60)
print("✅ TRAINING COMPLETE!")
print("📁 Model saved in: agriscan_model/classification_v1/weights/best.pt")
print("=" * 60)