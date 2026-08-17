"""MongoDB document shape for fields collection."""
# {
#   _id:         ObjectId
#   farm_id:     str  (farm._id ref)
#   name:        str
#   area:        float  (sq meters)
#   boundary:    GeoJSON Polygon  {"type": "Polygon", "coordinates": [[[lon,lat], ...]]}
#   crop_type:   str
#   planted_at:  datetime | None
#   created_at:  datetime
#   updated_at:  datetime
# }
