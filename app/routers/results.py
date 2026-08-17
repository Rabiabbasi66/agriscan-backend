from annotated_types import doc
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
import httpx

from app.dependencies import get_db, get_current_active_user
from app.schemas.analysis import AnalysisResultOut, FieldHistoryItem, DiseaseSummaryItem, DetectionItem
from app.schemas.common import DataResponse

router = APIRouter(
    prefix="/results",
    tags=["Results"],
)


def _build_result(doc: dict) -> AnalysisResultOut:
    return AnalysisResultOut(
        id=str(doc["_id"]),
        upload_id=doc["upload_id"],
        field_id=doc["field_id"],
        health_score=doc["health_score"],
        ndvi_mean=doc.get("ndvi_mean"),
        disease_summary=[DiseaseSummaryItem(**d) for d in doc.get("disease_summary", [])],
        detections=[DetectionItem(**d) for d in doc.get("detections", [])],
        point_cloud_url=doc.get("point_cloud_url"),
        report_pdf_url=doc.get("report_pdf_url"),
        processing_time_s=doc.get("processing_time_s"),
        created_at=doc["created_at"],
    )


@router.get(
    "/upload/{upload_id}",
    response_model=DataResponse[AnalysisResultOut],
    summary="Get analysis result for a specific upload",
)
async def get_by_upload(
    upload_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.analysis_results.find_one({"upload_id": upload_id})
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Result not found — processing may still be running")
    return DataResponse(data=_build_result(doc))


@router.get(
    "/field/{field_id}",
    response_model=DataResponse[List[FieldHistoryItem]],
    summary="Get health history for a field (all scans)",
)
async def get_field_history(
    field_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.analysis_results.find(
        {"field_id": field_id},
        sort=[("created_at", -1)],
        limit=50,
        projection={"upload_id": 1, "health_score": 1, "disease_summary": 1, "created_at": 1},
    )
    history = []
    async for doc in cursor:
        disease_count = sum(
            d["count"] for d in doc.get("disease_summary", []) if d.get("severity") != "healthy"
        )
        history.append(FieldHistoryItem(
            upload_id=doc["upload_id"],
            health_score=doc["health_score"],
            disease_count=disease_count,
            created_at=doc["created_at"],
        ))
    return DataResponse(data=history)


@router.get(
    "/report/{upload_id}/pdf",
    summary="Download PDF report for an upload",
)
async def download_pdf(
    upload_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.analysis_results.find_one(
        {"upload_id": upload_id}, projection={"report_pdf_url": 1}
    )
    if not doc or not doc.get("report_pdf_url"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="PDF report not available")

    # Stream PDF from S3
    from fastapi.responses import FileResponse
    from pathlib import Path

    pdf_path = Path(doc["report_pdf_url"])

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF not found"
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name
    )