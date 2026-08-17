# app/routers/predict.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.disease_predictor import predictor
from app.database import db
from app.models.prediction import PredictionCreate
import time
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/predict")
async def predict_disease(
    file: UploadFile = File(...),
    user_id: str = None  # Optional: user_id from auth
):
    """
    Image upload karein, prediction karein, aur database mein save karein
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "Only image files allowed")
    
    try:
        # 1. Image read karein
        image_bytes = await file.read()
        
        # 2. Prediction
        start_time = time.time()
        result = predictor.predict(image_bytes)
        inference_time = round((time.time() - start_time) * 1000, 2)
        
        # 3. ✅ Database mein save karein (FIXED: db.predictions not db.db.predictions)
        prediction_data = {
            "user_id": user_id or "anonymous",
            "image_url": f"/test_images/{uuid.uuid4()}.jpg",
            "crop": result["crop"],
            "disease": result["disease"],
            "confidence": result["confidence"],
            "is_healthy": result["is_healthy"],
            "class_name": result["class_name"],
            "inference_time_ms": inference_time,
            "created_at": datetime.utcnow()
        }
        
        # 🔥 FIX: db.predictions use karein (db.db nahi)
        inserted = await db.predictions.insert_one(prediction_data)
        prediction_data["_id"] = str(inserted.inserted_id)
        
        return {
            "success": True,
            "data": result,
            "inference_time_ms": inference_time,
            "saved_to_db": True,
            "prediction_id": str(inserted.inserted_id)
        }
    
    except Exception as e:
        raise HTTPException(500, f"Prediction failed: {str(e)}")


@router.get("/predictions/history")
async def get_prediction_history(
    user_id: str = None,
    limit: int = 50,
    skip: int = 0
):
    """
    User ki prediction history get karein
    """
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    # 🔥 FIX: db.predictions use karein
    cursor = db.predictions.find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    predictions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        predictions.append(doc)
    
    total = await db.predictions.count_documents(query)
    
    return {
        "success": True,
        "data": predictions,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/predictions/stats")
async def get_prediction_stats(user_id: str = None):
    """
    Prediction statistics
    """
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    # 🔥 FIX: db.predictions use karein
    total = await db.predictions.count_documents(query)
    healthy_count = await db.predictions.count_documents({**query, "is_healthy": True})
    diseased_count = await db.predictions.count_documents({**query, "is_healthy": False})
    
    pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "avg_confidence": {"$avg": "$confidence"}}}
    ]
    avg_result = await db.predictions.aggregate(pipeline).to_list(length=1)
    avg_confidence = avg_result[0]["avg_confidence"] if avg_result else 0
    
    return {
        "success": True,
        "stats": {
            "total_predictions": total,
            "healthy": healthy_count,
            "diseased": diseased_count,
            "avg_confidence": round(avg_confidence, 2)
        }
    }