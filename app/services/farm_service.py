from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.farm import FarmCreate, FarmUpdate, FarmOut, FarmListItem
from app.schemas.common import serialize_doc
import logging

logger = logging.getLogger(__name__)


def _build_farm_out(doc: dict, field_count: int = 0) -> FarmOut:
    return FarmOut(
        id=str(doc["_id"]),
        owner_id=str(doc["owner_id"]),
        name=doc["name"],
        description=doc.get("description"),
        location=doc["location"],
        address=doc.get("address"),
        total_area=doc["total_area"],
        crop_type=doc["crop_type"],
        field_count=field_count,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_farm(data: FarmCreate, owner_id: str, db: AsyncIOMotorDatabase) -> FarmOut:
    now = datetime.now(timezone.utc)
    doc = {
        "owner_id": owner_id,
        "name": data.name,
        "description": data.description,
        "location": {"type": "Point", "coordinates": [data.longitude, data.latitude]},
        "address": data.address,
        "total_area": data.total_area,
        "crop_type": data.crop_type,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.farms.insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info("Farm created: %s by user %s", data.name, owner_id)
    return _build_farm_out(doc)


async def list_farms(owner_id: str, page: int, page_size: int, db: AsyncIOMotorDatabase):
    skip = (page - 1) * page_size
    total = await db.farms.count_documents({"owner_id": owner_id})
    cursor = db.farms.find({"owner_id": owner_id}).skip(skip).limit(page_size).sort("created_at", -1)
    items = []
    async for doc in cursor:
        field_count = await db.fields.count_documents({"farm_id": str(doc["_id"])})
        items.append(FarmListItem(
            id=str(doc["_id"]),
            name=doc["name"],
            crop_type=doc["crop_type"],
            total_area=doc["total_area"],
            field_count=field_count,
            created_at=doc["created_at"],
        ))
    return items, total


async def get_farm(farm_id: str, owner_id: str, db: AsyncIOMotorDatabase) -> FarmOut:
    doc = await db.farms.find_one({"_id": ObjectId(farm_id), "owner_id": owner_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Farm not found")
    field_count = await db.fields.count_documents({"farm_id": farm_id})
    return _build_farm_out(doc, field_count)


async def update_farm(farm_id: str, data: FarmUpdate, owner_id: str, db: AsyncIOMotorDatabase) -> FarmOut:
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    result = await db.farms.update_one(
        {"_id": ObjectId(farm_id), "owner_id": owner_id},
        {"$set": update},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Farm not found")
    return await get_farm(farm_id, owner_id, db)


async def delete_farm(farm_id: str, owner_id: str, db: AsyncIOMotorDatabase) -> None:
    result = await db.farms.delete_one({"_id": ObjectId(farm_id), "owner_id": owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Farm not found")
    # cascade: mark fields inactive (soft delete)
    await db.fields.update_many({"farm_id": farm_id}, {"$set": {"deleted": True}})
    logger.info("Farm deleted: %s", farm_id)
