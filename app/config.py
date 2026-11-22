from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field
from functools import lru_cache
from typing import List
import json


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
    # Deployment environment: "development" | "production". Anything other
    # than "development" is treated as production for security decisions.
    ENV: str = "development"

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() != "development"

    # Optional remote classifier endpoint (Cloud Run etc.). When unset the
    # backend uses the locally loaded weights in models/best.pt.
    CLASSIFIER_API_URL: str = ""
    # Server-side secret forwarded to the remote classifier. NEVER expose to
    # the browser bundle.
    CLASSIFIER_API_KEY: str = ""

    # Domain routers (fields, uploads, results, notifications) are not used by
    # the current frontend and their owner-scoping is incomplete (IDOR risk).
    # They stay in the codebase but are NOT mounted unless explicitly enabled.
    ENABLE_DOMAIN_ROUTERS: bool = False

    # Comma-separated string (ALLOWED_ORIGINS=a,b,c). Parsed lazily by the
    # allowed_origins property — a plain str avoids pydantic-settings'
    # JSON-only decoding for list fields.
    ALLOWED_ORIGINS: str = ""

    @property
    def allowed_origins(self) -> List[str]:
        raw = self.ALLOWED_ORIGINS.strip()
        env_origins: List[str] = []
        if raw.startswith("["):
            # JSON list form (legacy .env style)
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    env_origins = [str(o).strip() for o in parsed if str(o).strip()]
            except json.JSONDecodeError:
                env_origins = []
        else:
            env_origins = [o.strip() for o in raw.split(",") if o.strip()]
        if env_origins:
            return env_origins
        if self.is_production:
            # Production with no explicit origins: deny cross-origin browser
            # calls rather than silently trusting localhost.
            return []
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8443",
            "http://127.0.0.1:8443",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://agriscan-3d.netlify.app",
            "https://agriscan-3d.vercel.app",
        ]

    # Upload security: maximum accepted image size in bytes (10 MB default).
    MAX_UPLOAD_SIZE: int = 5_242_880  # 5 MB — predict is the only consumer

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

    # JWT — no default: the app refuses to boot without a strong secret.
    JWT_SECRET_KEY: str = ""
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
    s = Settings()
    if not s.JWT_SECRET_KEY or len(s.JWT_SECRET_KEY) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or shorter than 32 characters. "
            "Set a strong random secret in the environment before starting."
        )
    return s


settings = get_settings()
