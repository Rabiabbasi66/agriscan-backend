# download_kaggle.py
import kagglehub

# Download latest version of PlantVillage dataset
path = kagglehub.dataset_download("abdallahalidev/plantvillage-dataset")

print(f"✅ Dataset downloaded to: {path}")