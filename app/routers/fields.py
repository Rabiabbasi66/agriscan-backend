from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db, get_current_active_user
from app.schemas.field import FieldCreate, FieldUpdate, FieldOut, FieldListItem
from app.schemas.common import DataResponse
from app.services.field_service import (
    create_field, list_fields, get_field, update_field, delete_field,
)
from typing import List

router = APIRouter(
    prefix="/fields",
    tags=["Fields"],
)


@router.post("", response_model=DataResponse[FieldOut], status_code=201)
async def create(
    body: FieldCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    field = await create_field(body, db)
    return DataResponse(data=field, message="Field created")


@router.get("/farm/{farm_id}", response_model=DataResponse[List[FieldListItem]])
async def list_by_farm(
    farm_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    fields = await list_fields(farm_id, db)
    return DataResponse(data=fields)


@router.get("/{field_id}", response_model=DataResponse[FieldOut])
async def get_one(
    field_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    field = await get_field(field_id, db)
    return DataResponse(data=field)


@router.patch("/{field_id}", response_model=DataResponse[FieldOut])
async def update(
    field_id: str,
    body: FieldUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    field = await update_field(field_id, body, db)
    return DataResponse(data=field, message="Field updated")


@router.delete("/{field_id}", status_code=204)
async def delete(
    field_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await delete_field(field_id, db)
