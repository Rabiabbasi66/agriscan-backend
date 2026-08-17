"""MongoDB document shape for analysis_results collection."""
# {
#   _id:              ObjectId
#   upload_id:        str  (unique)
#   field_id:         str
#   health_score:     float  (0–100)
#   ndvi_mean:        float  (-1 to 1)
#   disease_summary:  list[{
#                       label: str,
#                       count: int,
#                       area_pct: float,
#                       severity: "high"|"medium"|"low",
#                       avg_confidence: float
#                     }]
#   detections:       list[{
#                       image_url: str,
#                       label: str,
#                       confidence: float,
#                       bbox: [x1,y1,x2,y2],
#                       annotated_url: str
#                     }]
#   point_cloud_url:  str | None   (COLMAP output, S3)
#   report_pdf_url:   str | None
#   processing_time_s: float
#   created_at:       datetime
# }
