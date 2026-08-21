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
        
        # ✅ FIXED: db.db["predictions"] use karo
        collection = db.db["predictions"]
        inserted = await collection.insert_one(prediction_data)
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
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    collection = db.db["predictions"]
    cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    predictions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        predictions.append(doc)
    
    total = await collection.count_documents(query)
    
    return {
        "success": True,
        "data": predictions,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/predictions/stats")
async def get_prediction_stats(user_id: str = None):
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    collection = db.db["predictions"]
    total = await collection.count_documents(query)
    healthy_count = await collection.count_documents({**query, "is_healthy": True})
    diseased_count = await collection.count_documents({**query, "is_healthy": False})
    
    pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "avg_confidence": {"$avg": "$confidence"}}}
    ]
    avg_result = await collection.aggregate(pipeline).to_list(length=1)
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