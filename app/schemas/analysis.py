from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class DetectionItem(BaseModel):
    image_url: str
    label: str
    confidence: float
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2] in pixels")
    annotated_url: str
    severity: Literal["high", "medium", "low", "healthy"]


class DiseaseSummaryItem(BaseModel):
    label: str
    count: int
    area_pct: float
    severity: Literal["high", "medium", "low", "healthy"]
    avg_confidence: float


class AnalysisResultOut(BaseModel):
    id: str
    upload_id: str
    field_id: str
    health_score: float = Field(..., ge=0, le=100)
    ndvi_mean: Optional[float] = None
    disease_summary: List[DiseaseSummaryItem]
    detections: List[DetectionItem]
    point_cloud_url: Optional[str] = None
    report_pdf_url: Optional[str] = None
    processing_time_s: Optional[float] = None
    created_at: datetime


class FieldHistoryItem(BaseModel):
    upload_id: str
    health_score: float
    disease_count: int
    created_at: datetime


class ReportRequest(BaseModel):
    upload_id: str
    include_detections: bool = True
    include_map: bool = True
