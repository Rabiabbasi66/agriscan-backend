from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
import time
import logging

from app.config import settings
from app.database import db
from app.utils.logger import setup_logging
from app.routers import auth, farms, fields, uploads, results, notifications, health
from app.routers import predict
from app.routers import predictions
from app.services.disease_predictor import get_predictor
from starlette.concurrency import run_in_threadpool


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AgriScan 3D API starting up...")
    if await db.connect():
        logger.info("✅ Connected to MongoDB")
    else:
        logger.warning("MongoDB unavailable - AI scans run without persistence")

    # Load the trained weights once and keep them resident. Failures are
    # logged instead of aborting startup: /predict then answers 503 clearly.
    try:
        predictor = await run_in_threadpool(get_predictor)
        await run_in_threadpool(predictor.warm_up)
        logger.info("✅ YOLOv8 model ready (%d classes)", predictor.num_classes)
    except Exception:
        logger.exception("❌ YOLOv8 model failed to load — /predict will return 503")

    yield
    logger.info("🔻 Shutting down...")
    await db.close()
    logger.info("✅ Disconnected from MongoDB")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AgriScan 3D AI Crop Disease Detection API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}
)


app.add_middleware(GZipMiddleware, minimum_size=1000)

# Explicit origins only: a wildcard is incompatible with allow_credentials
# (browsers reject "Access-Control-Allow-Origin: *" on credentialed requests).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/test_images",
    StaticFiles(directory="test_images"),
    name="test_images"
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


PREFIX = "/api/v1"

# Health lives outside the API prefix so probes can hit plain /health/health.
app.include_router(health.router, tags=["Health"])

for router, tag in [
    (auth.router, "Auth"),
    (farms.router, "Farms"),
    (fields.router, "Fields"),
    (uploads.router, "Uploads"),
    (results.router, "Results"),
    (notifications.router, "Notifications"),
    (predict.router, "Disease Prediction"),
    (predictions.router, "Predictions"),
]:
    app.include_router(router, prefix=PREFIX, tags=[tag])


@app.get("/")
async def root():
    return {
        "message": "AgriScan 3D API",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agriscan-api"}