# app/routers/predict.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.disease_predictor import predictor
from app.database import db
import time
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/predict")
async def predict_disease(
    file: UploadFile = File(...),
    user_id: str = None
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "Only image files allowed")
    
    try:
        image_bytes = await file.read()
        
        start_time = time.time()
        result = predictor.predict(image_bytes)
        inference_time = round((time.time() - start_time) * 1000, 2)
        
        prediction_data = {
            "user_id": user_id or "anonymous",
            "image_url": f"/test_images/{uuid.uuid4()}.jpg",
            "crop": result.get("crop", "unknown"),
            "disease": result.get("disease", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "is_healthy": result.get("is_healthy", False),
            "class_name": result.get("class_name", "unknown"),
            "inference_time_ms": inference_time,
            "created_at": datetime.utcnow()
        }
        
        # ✅ FORCE DATABASE SAVE
        try:
            collection = db.database["predictions"]
            inserted = await collection.insert_one(prediction_data)
            print("✅ Data saved to MongoDB, ID:", inserted.inserted_id)
        except Exception as e:
            print("❌ MongoDB Save Error:", str(e))
            inserted = None
        
        return {
            "success": True,
            "data": result,
            "inference_time_ms": inference_time,
            "saved_to_db": inserted is not None,
            "prediction_id": str(inserted.inserted_id) if inserted else None
        }
    
    except Exception as e:
        print("❌ Prediction Error:", str(e))
        raise HTTPException(500, f"Prediction failed: {str(e)}")