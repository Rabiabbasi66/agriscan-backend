from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime


class FileInfo(BaseModel):
    original_name: str
    s3_url: str
    file_type: Literal["image", "video"]
    size_bytes: int


class UploadCreate(BaseModel):
    field_id: str
    source: Literal["drone", "mobile", "satellite"] = "mobile"
    notes: Optional[str] = Field(None, max_length=500)


class UploadOut(BaseModel):
    id: str
    field_id: str
    uploaded_by: str
    files: List[FileInfo]
    status: str
    source: str
    notes: Optional[str] = None
    job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobStatusOut(BaseModel):
    job_id: str
    upload_id: str
    status: str
    progress: int
    error_msg: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
