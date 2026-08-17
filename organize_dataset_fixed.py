# organize_dataset_fixed.py
import os
import shutil
from sklearn.model_selection import train_test_split

print("=" * 60)
print("🌱 AGRISCAN 3D - ORGANIZING DATASET")
print("=" * 60)

# DIRECT PATH - jo abhi mila hai
source_dir = r"C:\Users\M.T.LaptoppoinT\.cache\kagglehub\datasets\abdallahalidev\plantvillage-dataset\versions\3\plantvillage dataset\color"
print(f"📁 Source: {source_dir}")

# Check if exists
if not os.path.exists(source_dir):
    print("❌ Path not found! Please check.")
    exit()

# Check sample
test_class = None
for item in os.listdir(source_dir):
    item_path = os.path.join(source_dir, item)
    if os.path.isdir(item_path):
        test_class = item
        test_images = os.listdir(item_path)
        print(f"📸 Sample: {test_class} has {len(test_images)} images ✅")
        break

if not test_class:
    print("❌ No class folders found!")
    exit()

# Destination
base_dir = "plantvillage_dataset"
train_dir = os.path.join(base_dir, "train")
val_dir = os.path.join(base_dir, "val")
os.makedirs(train_dir, exist_ok=True)
os.makedirs(val_dir, exist_ok=True)

# All classes
all_classes = [item for item in os.listdir(source_dir) 
               if os.path.isdir(os.path.join(source_dir, item))]

print(f"📚 Total classes: {len(all_classes)}")

# Split and copy
print("\n⏳ Splitting images (80% train, 20% val)...")

total_train = 0
total_val = 0

for class_name in all_classes:
    class_source = os.path.join(source_dir, class_name)
    images = [f for f in os.listdir(class_source) 
              if f.lower().endswith(('.jpg', '.png', '.jpeg', '.JPG', '.PNG'))]
    
    if len(images) == 0:
        print(f"⚠️ {class_name}: No images, skipping")
        continue
    
    train_imgs, val_imgs = train_test_split(images, test_size=0.2, random_state=42)
    
    os.makedirs(os.path.join(train_dir, class_name), exist_ok=True)
    os.makedirs(os.path.join(val_dir, class_name), exist_ok=True)
    
    for img in train_imgs:
        shutil.copy2(os.path.join(class_source, img), 
                     os.path.join(train_dir, class_name, img))
    
    for img in val_imgs:
        shutil.copy2(os.path.join(class_source, img), 
                     os.path.join(val_dir, class_name, img))
    
    total_train += len(train_imgs)
    total_val += len(val_imgs)
    print(f"✅ {class_name}: {len(train_imgs)} train, {len(val_imgs)} val")

print("\n" + "=" * 60)
print("✅ DATASET ORGANIZED!")
print(f"📊 Total: {total_train} train, {total_val} val")
print(f"📁 Location: {os.path.abspath(base_dir)}")
print("=" * 60)