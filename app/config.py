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
        "http://localhost:5173",
        "http://localhost:8443",
        "http://localhost:3000",
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

    # AI Model
    YOLO_MODEL_PATH: str = "models/agriscan_yolov8.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.40
    YOLO_IOU_THRESHOLD: float = 0.45

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
