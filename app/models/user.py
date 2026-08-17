"""MongoDB document shape for users collection (reference only — Motor uses dicts)."""
from datetime import datetime
from typing import Literal


# Shape of a user document stored in MongoDB
# {
#   _id:           ObjectId
#   email:         str  (unique)
#   phone:         str | None
#   full_name:     str
#   hashed_password: str
#   role:          "farmer" | "agronomist" | "admin"
#   is_active:     bool
#   profile_pic:   str | None   (S3 URL)
#   fcm_token:     str | None   (Firebase push token)
#   created_at:    datetime
#   updated_at:    datetime
# }

ROLES = Literal["farmer", "agronomist", "admin"]
