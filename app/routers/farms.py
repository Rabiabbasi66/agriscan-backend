from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db, get_current_active_user
from app.schemas.farm import FarmCreate, FarmUpdate, FarmOut, FarmListItem
from app.schemas.common import DataResponse, PaginatedResponse
from app.services.farm_service import create_farm, list_farms, get_farm, update_farm, delete_farm
import math

router = APIRouter(
    prefix="/farms",
    tags=["Farms"],
)


@router.post("", response_model=DataResponse[FarmOut], status_code=201)
async def create(
    body: FarmCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a new farm. Logged-in farmer only."""
    farm = await create_farm(body, str(current_user["_id"]), db)
    return DataResponse(data=farm, message="Farm created")


@router.get("", response_model=PaginatedResponse[FarmListItem])
async def list_my_farms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List all farms owned by the current user."""
    items, total = await list_farms(str(current_user["_id"]), page, page_size, db)
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


@router.get("/{farm_id}", response_model=DataResponse[FarmOut])
async def get_one(
    farm_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    farm = await get_farm(farm_id, str(current_user["_id"]), db)
    return DataResponse(data=farm)


@router.patch("/{farm_id}", response_model=DataResponse[FarmOut])
async def update(
    farm_id: str,
    body: FarmUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    farm = await update_farm(farm_id, body, str(current_user["_id"]), db)
    return DataResponse(data=farm, message="Farm updated")


@router.delete("/{farm_id}", status_code=204)
async def delete(
    farm_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await delete_farm(farm_id, str(current_user["_id"]), db)
