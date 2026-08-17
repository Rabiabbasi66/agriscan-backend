"""MongoDB document shape for uploads collection."""
# {
#   _id:           ObjectId
#   field_id:      str
#   uploaded_by:   str  (user._id)
#   files:         list[{
#                    original_name: str,
#                    s3_url: str,
#                    file_type: "image" | "video",
#                    size_bytes: int
#                  }]
#   status:        "pending" | "processing" | "done" | "failed"
#   source:        "drone" | "mobile" | "satellite"
#   notes:         str | None
#   created_at:    datetime
#   updated_at:    datetime
# }
