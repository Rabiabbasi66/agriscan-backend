from fastapi import APIRouter, Depends, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.dependencies import get_db, get_current_active_user
from app.schemas.upload import UploadOut, JobStatusOut
from app.schemas.common import DataResponse
from app.services.upload_service import create_upload, get_upload
import logging

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=DataResponse[UploadOut],
    status_code=202,
    summary="Upload drone/mobile images or video for AI analysis",
)
async def upload_images(
    files: List[UploadFile] = File(..., description="One or more images (JPEG/PNG/TIFF) or MP4 video"),
    field_id: str = Form(...),
    source: str = Form("mobile", description="drone | mobile | satellite"),
    notes: Optional[str] = Form(None),
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Upload images captured from drone or mobile to analyse crop health.
    - Files are stored in S3
    - A Celery job is queued for YOLOv8 inference + NDVI + 3D point cloud
    - Returns upload ID and job ID to poll for status
    """
    result = await create_upload(
        files=files,
        field_id=field_id,
        source=source,
        notes=notes,
        user_id=str(current_user["_id"]),
        db=db,
    )
    return DataResponse(data=result, message="Upload received. Processing started.")


@router.get("/{upload_id}", response_model=DataResponse[UploadOut])
async def get_one(
    upload_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    upload = await get_upload(upload_id, db)
    return DataResponse(data=upload)


@router.get("/{upload_id}/job-status", response_model=DataResponse[JobStatusOut])
async def job_status(
    upload_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Poll the processing job status for an upload."""
    job = await db.jobs.find_one({"upload_id": upload_id})
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return DataResponse(data=JobStatusOut(
        job_id=str(job["_id"]),
        upload_id=job["upload_id"],
        status=job["status"],
        progress=job.get("progress", 0),
        error_msg=job.get("error_msg"),
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
        created_at=job["created_at"],
    ))
