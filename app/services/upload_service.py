from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.schemas.upload import UploadOut, FileInfo
from app.utils.storage import upload_file_to_s3
import logging

logger = logging.getLogger(__name__)

ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/tiff",
    "video/mp4", "video/quicktime",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


async def create_upload(
    files: List[UploadFile],
    field_id: str,
    source: str,
    notes: str | None,
    user_id: str,
    db: AsyncIOMotorDatabase,
) -> UploadOut:
    field = await db.fields.find_one({"_id": ObjectId(field_id)})
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    file_docs = []
    for f in files:
        if f.content_type not in ALLOWED_MIME:
            raise HTTPException(status_code=415, detail=f"File type {f.content_type} not allowed")
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File {f.filename} exceeds 100 MB limit")
        folder = "uploads/images" if f.content_type.startswith("image") else "uploads/videos"
        s3_url = upload_file_to_s3(content, f.filename or "upload", folder=folder)
        file_docs.append({
            "original_name": f.filename or "upload",
            "s3_url": s3_url,
            "file_type": "image" if f.content_type.startswith("image") else "video",
            "size_bytes": len(content),
        })

    now = datetime.now(timezone.utc)
    upload_doc = {
        "field_id": field_id,
        "uploaded_by": user_id,
        "files": file_docs,
        "status": "pending",
        "source": source,
        "notes": notes,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.uploads.insert_one(upload_doc)
    upload_id = str(result.inserted_id)

    # Create job record
    job_doc = {
        "upload_id": upload_id,
        "celery_task_id": None,
        "status": "queued",
        "progress": 0,
        "error_msg": None,
        "started_at": None,
        "finished_at": None,
        "created_at": now,
    }
    job_result = await db.jobs.insert_one(job_doc)
    job_id = str(job_result.inserted_id)

    # Development mode: run pipeline directly without Celery/Redis
    try:
        logger.info(
            "Running upload processing inline (development mode)"
        )

        from app.workers.tasks import _process_upload_inline

        await _process_upload_inline(
            upload_id,
            job_id
        )

        logger.info(
            "Upload %s processed inline successfully",
            upload_id
        )

    except Exception as e:
        logger.exception(
            "Inline processing failed for upload %s: %s",
            upload_id,
            e
        )

        await db.jobs.update_one(
            {"_id": job_result.inserted_id},
            {
                "$set": {
                    "status": "failed",
                    "error_msg": str(e)
                }
            }
        )

    return UploadOut(
        id=upload_id,
        field_id=field_id,
        uploaded_by=user_id,
        files=[FileInfo(**f) for f in file_docs],
        status="pending",
        source=source,
        notes=notes,
        job_id=job_id,
        created_at=now,
        updated_at=now,
    )


async def get_upload(
    upload_id: str,
    db: AsyncIOMotorDatabase
) -> UploadOut:
    doc = await db.uploads.find_one(
        {"_id": ObjectId(upload_id)}
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Upload not found"
        )

    return UploadOut(
        id=str(doc["_id"]),
        field_id=doc["field_id"],
        uploaded_by=doc["uploaded_by"],
        files=[
            FileInfo(**f)
            for f in doc.get("files", [])
        ],
        status=doc["status"],
        source=doc["source"],
        notes=doc.get("notes"),
        job_id=doc.get("job_id"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )