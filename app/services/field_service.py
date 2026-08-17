from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.field import FieldCreate, FieldUpdate, FieldOut, FieldListItem
from app.schemas.common import GeoPolygon
import logging

logger = logging.getLogger(__name__)


def _build_polygon(coords: list) -> dict:
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    return {"type": "Polygon", "coordinates": [coords]}


def _doc_to_out(doc: dict, health_score=None) -> FieldOut:
    return FieldOut(
        id=str(doc["_id"]),
        farm_id=doc["farm_id"],
        name=doc["name"],
        area=doc["area"],
        crop_type=doc["crop_type"],
        planted_at=doc.get("planted_at"),
        boundary=GeoPolygon(**doc["boundary"]),
        last_health_score=health_score,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _get_last_health(field_id: str, db: AsyncIOMotorDatabase) -> float | None:
    result = await db.analysis_results.find_one(
        {"field_id": field_id},
        sort=[("created_at", -1)],
        projection={"health_score": 1},
    )
    return result["health_score"] if result else None


async def create_field(data: FieldCreate, db: AsyncIOMotorDatabase) -> FieldOut:
    farm = await db.farms.find_one({"_id": ObjectId(data.farm_id)})
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    now = datetime.now(timezone.utc)
    doc = {
        "farm_id": data.farm_id,
        "name": data.name,
        "area": data.area,
        "crop_type": data.crop_type,
        "planted_at": data.planted_at,
        "boundary": _build_polygon(data.boundary_coordinates),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.fields.insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info("Field created: %s in farm %s", data.name, data.farm_id)
    return _doc_to_out(doc)


async def list_fields(farm_id: str, db: AsyncIOMotorDatabase):
    docs = await db.fields.find({"farm_id": farm_id, "deleted": {"$ne": True}}).sort("created_at", -1).to_list(100)
    out = []
    for doc in docs:
        hs = await _get_last_health(str(doc["_id"]), db)
        out.append(FieldListItem(
            id=str(doc["_id"]),
            farm_id=doc["farm_id"],
            name=doc["name"],
            area=doc["area"],
            crop_type=doc["crop_type"],
            last_health_score=hs,
            created_at=doc["created_at"],
        ))
    return out


async def get_field(field_id: str, db: AsyncIOMotorDatabase) -> FieldOut:
    doc = await db.fields.find_one({"_id": ObjectId(field_id), "deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="Field not found")
    hs = await _get_last_health(field_id, db)
    return _doc_to_out(doc, hs)


async def update_field(field_id: str, data: FieldUpdate, db: AsyncIOMotorDatabase) -> FieldOut:
    update: dict = {k: v for k, v in data.model_dump().items() if v is not None}
    if "boundary_coordinates" in update:
        update["boundary"] = _build_polygon(update.pop("boundary_coordinates"))
    update["updated_at"] = datetime.now(timezone.utc)
    result = await db.fields.update_one({"_id": ObjectId(field_id)}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Field not found")
    return await get_field(field_id, db)


async def delete_field(field_id: str, db: AsyncIOMotorDatabase) -> None:
    result = await db.fields.update_one({"_id": ObjectId(field_id)}, {"$set": {"deleted": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Field not found")
