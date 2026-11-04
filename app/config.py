from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App
    APP_NAME: str = "AgriScan 3D API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    ALLOWED_ORIGINS: List[str] = [
        # Local dev: Vite binds 0.0.0.0, so the browser may open the app as
        # either localhost or 127.0.0.1 — both must be accepted or the auth /
        # history calls are blocked by CORS and the UI stays in its loading
        # state.
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8443",
        "http://127.0.0.1:8443",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Deployed frontends (public URLs, also overridable via env).
        "https://agriscan-3d.netlify.app",
        "https://agriscan-3d.vercel.app",
    ]

    # Upload security: maximum accepted image size in bytes (10 MB default).
    MAX_UPLOAD_SIZE: int = 10_485_760

    # MongoDB (Local Compass)
    # MONGODB_URI / MONGODB_DB_NAME are read from the environment or the local
    # .env file. Never hardcode real credentials here — set them in .env only.
    # The legacy MONGODB_URL variable name is accepted as an alias.
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGODB_URI", "MONGODB_URL"),
    )
    MONGODB_DB_NAME: str = "agriscan"

    @property
    def mongodb_uri(self) -> str:
        return self.MONGODB_URI

    @property
    def mongodb_db_name(self) -> str:
        return self.MONGODB_DB_NAME

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-32-chars-min"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS S3 (Optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "agriscan-uploads"
    S3_ENDPOINT_URL: str = ""

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI Model — trained PlantVillage classifier (38 classes). Paths are
    # resolved relative to backend/, independent of the shell CWD.
    YOLO_MODEL_PATH: str = "models/best.pt"
    # Minimum top-1 confidence required to report a class; below it the API
    # returns detected=false instead of guessing a disease.
    YOLO_CONFIDENCE_THRESHOLD: float = 0.40
    YOLO_IOU_THRESHOLD: float = 0.45

    # Plant-domain validation. The ImageNet checkpoint already in the repo
    # scores "does this look like a plant at all"; the calibrated reference
    # (class centroids) scores "does this look like a supported leaf".
    PLANT_GATE_MODEL_PATH: str = "yolov8n-cls.pt"
    DOMAIN_REFERENCE_PATH: str = "models/domain_guard.npz"
    # ImageNet plant-class probability mass that accepts an image.
    # Calibrated on real non-plant photos: 97.5th percentile = 0.030.
    PLANT_SCORE_THRESHOLD: float = 0.03
    # Laplacian-variance floor; 0.5th percentile of held-out leaves = 15.2.
    BLUR_VARIANCE_THRESHOLD: float = 12.0

    # Firebase
    FCM_SERVER_KEY: str = ""

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Uvicorn
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
