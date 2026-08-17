"""MongoDB document shape for farms collection."""
# {
#   _id:         ObjectId
#   owner_id:    str  (user._id ref)
#   name:        str
#   description: str | None
#   location:    GeoJSON Point  {"type": "Point", "coordinates": [lon, lat]}
#   address:     str | None
#   total_area:  float  (sq meters)
#   crop_type:   str    (Wheat, Corn, Rice …)
#   created_at:  datetime
#   updated_at:  datetime
# }
