# download_dataset.py

import subprocess
import sys

# Install datasets library
subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets"])

from datasets import load_dataset

print("📥 Downloading PlantVillage dataset...")
dataset = load_dataset("mohanty/PlantVillage", "color")

print("✅ Dataset downloaded successfully!")
print(f"📊 Total images: {len(dataset['train'])}")
print(f"📁 Dataset structure: {dataset}")