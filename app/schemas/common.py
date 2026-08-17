from pydantic import BaseModel, Field
from typing import Any, Generic, TypeVar, List
from datetime import datetime
from bson import ObjectId

T = TypeVar("T")


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB _id ObjectId to str."""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return str(v)


class ResponseBase(BaseModel):
    success: bool = True
    message: str = "OK"


class DataResponse(ResponseBase, Generic[T]):
    data: T


class PaginatedResponse(ResponseBase, Generic[T]):
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    success: bool = False
    detail: str
    type: str | None = None


class GeoPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")


class GeoPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]] = Field(
        ..., description="[[[lon,lat], [lon,lat], ...]]"
    )
