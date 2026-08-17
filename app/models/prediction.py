# app/models/prediction.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class PredictionBase(BaseModel):
    user_id: str = "anonymous"
    image_url: str
    crop: str
    disease: str
    confidence: float
    is_healthy: bool
    class_name: str
    inference_time_ms: float

class PredictionCreate(PredictionBase):
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Prediction(PredictionCreate):
    id: str = Field(alias="_id")
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}