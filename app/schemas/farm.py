from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.common import GeoPoint


class FarmCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    address: Optional[str] = Field(None, max_length=300)
    total_area: float = Field(..., gt=0, description="Area in square meters")
    crop_type: str = Field(..., max_length=60)


class FarmUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None
    address: Optional[str] = None
    total_area: Optional[float] = Field(None, gt=0)
    crop_type: Optional[str] = None


class FarmOut(BaseModel):
    id: str
    owner_id: str
    name: str
    description: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    total_area: float
    crop_type: str
    field_count: int = 0
    created_at: datetime
    updated_at: datetime


class FarmListItem(BaseModel):
    id: str
    name: str
    crop_type: str
    total_area: float
    field_count: int
    created_at: datetime
