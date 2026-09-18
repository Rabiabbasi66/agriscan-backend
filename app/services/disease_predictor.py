# app/services/disease_predictor.py
from ultralytics import YOLO
from PIL import Image
import io
import os

class DiseasePredictor:
    def __init__(self, model_path="models/best.pt"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
        self.model = YOLO(model_path)
        
        # PlantVillage ke 38 class names
        self.class_names = [
            'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
            'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy',
            'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
            'Corn_(maize)___healthy', 'Corn_(maize)___Northern_Leaf_Blight',
            'Grape___Black_rot', 'Grape___Esca_(Black_Measles)', 'Grape___healthy',
            'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Orange___Haunglongbing_(Citrus_greening)',
            'Peach___Bacterial_spot', 'Peach___healthy', 'Pepper,_bell___Bacterial_spot',
            'Pepper,_bell___healthy', 'Potato___Early_blight', 'Potato___healthy',
            'Potato___Late_blight', 'Raspberry___healthy', 'Soybean___healthy',
            'Squash___Powdery_mildew', 'Strawberry___healthy', 'Strawberry___Leaf_scorch',
            'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___healthy',
            'Tomato___Late_blight', 'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot',
            'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot',
            'Tomato___Tomato_mosaic_virus', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus'
        ]
    
    def predict(self, image_bytes):
        image = Image.open(io.BytesIO(image_bytes))
        results = self.model(image)
        probs = results[0].probs
        top_idx = probs.top1
        confidence = probs.top1conf.item()
        disease_name = self.class_names[top_idx]

        crop, disease = self._parse_disease_name(disease_name)

        # Phase 6: expose the real top-1 class index from the classifier.
        # This is genuine model output (no synthetic severity/GPS/yield).
        return {
            "disease": disease,
            "crop": crop,
            "confidence": round(confidence * 100, 2),
            "is_healthy": "healthy" in disease.lower(),
            "class_name": disease_name,
            "class_index": int(top_idx),
        }
    
    def _parse_disease_name(self, full_name):
        parts = full_name.split('___')
        if len(parts) == 2:
            return parts[0].replace('_', ' '), parts[1].replace('_', ' ')
        return "Unknown", full_name.replace('_', ' ')

predictor = DiseasePredictor()