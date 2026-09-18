# app/routers/predictions.py
#
# Prediction History — authenticated access to the predictions the current
# user created via POST /api/v1/predict (app/routers/predict.py).
#
# Endpoints:
#   GET  /api/v1/predictions                    → paginated history (newest first)
#   GET  /api/v1/predictions/{prediction_id}    → single prediction detail
#
# User isolation: every query is scoped to the JWT subject (user_id), so a
# user can only ever see their own documents. Ownership failures return 404
# (never a distinction between "missing" and "not yours").
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db, get_current_active_user
from app.schemas.common import DataResponse, PaginatedResponse, serialize_doc

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)

# Bounded page sizes — the API never returns an unbounded document list.
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get(
    "",
    response_model=PaginatedResponse[dict],
    summary="Prediction history for the authenticated user (newest first)",
)
async def list_predictions(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Results per page"
    ),
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    skip = (page - 1) * page_size

    # Uses the compound index (user_id ASC, created_at DESC) ensured in
    # app/database.py::ensure_indexes — exact match for this query shape.
    cursor = (
        db.predictions.find({"user_id": user_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = [serialize_doc(doc) for doc in await cursor.to_list(length=page_size)]
    total = await db.predictions.count_documents({"user_id": user_id})

    return PaginatedResponse(
        data=docs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get(
    "/{prediction_id}",
    response_model=DataResponse[dict],
    summary="Single prediction detail (owner only)",
)
async def get_prediction(
    prediction_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # Malformed IDs get a 422-style validation error, consistent with how
    # FastAPI reports invalid path/query parameters.
    if not ObjectId.is_valid(prediction_id):
        raise HTTPException(422, "Invalid prediction id")

    user_id = str(current_user["_id"])

    # Ownership is part of the query itself — another user's document is
    # indistinguishable from a missing one (404 either way).
    doc = await db.predictions.find_one(
        {"_id": ObjectId(prediction_id), "user_id": user_id}
    )
    if not doc:
        raise HTTPException(404, "Prediction not found")

    return DataResponse(data=serialize_doc(doc))
