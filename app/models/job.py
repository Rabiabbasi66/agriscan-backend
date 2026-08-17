"""MongoDB document shape for jobs collection (Celery task tracking)."""
# {
#   _id:         ObjectId
#   upload_id:   str
#   celery_task_id: str
#   status:      "queued" | "running" | "done" | "failed"
#   progress:    int  (0–100)
#   error_msg:   str | None
#   started_at:  datetime | None
#   finished_at: datetime | None
#   created_at:  datetime
# }
