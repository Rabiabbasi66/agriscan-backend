from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.common import GeoPolygon


class FieldCreate(BaseModel):
    farm_id: str
    name: str = Field(..., min_length=2, max_length=120)
    area: float = Field(..., gt=0, description="Area in sq meters")
    crop_type: str = Field(..., max_length=60)
    planted_at: Optional[datetime] = None
    boundary_coordinates: List[List[float]] = Field(
        ...,
        description="List of [lon, lat] points forming the polygon. First and last must match.",
        min_length=4,
    )


class FieldUpdate(BaseModel):
    name: Optional[str] = None
    area: Optional[float] = Field(None, gt=0)
    crop_type: Optional[str] = None
    planted_at: Optional[datetime] = None
    boundary_coordinates: Optional[List[List[float]]] = None


class FieldOut(BaseModel):
    id: str
    farm_id: str
    name: str
    area: float
    crop_type: str
    planted_at: Optional[datetime] = None
    boundary: GeoPolygon
    last_health_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class FieldListItem(BaseModel):
    id: str
    farm_id: str
    name: str
    area: float
    crop_type: str
    last_health_score: Optional[float] = None
    created_at: datetime
