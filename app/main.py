# app/main.py
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


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AgriScan 3D API starting up...")
    await db.connect()
    logger.info("✅ Connected to MongoDB")
    yield
    logger.info("🔻 Shutting down...")
    await db.close()
    logger.info("✅ Disconnected from MongoDB")


app = FastAPI(
    title=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "AgriScan 3D API",
    version=settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
    description="AgriScan 3D AI Crop Disease Detection API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}
)


app.add_middleware(GZipMiddleware, minimum_size=1000)

# ✅ CORS — configured origins only (Phase 12 hardening).
# The previous wildcard "*" was both insecure AND non-functional for
# credentialed requests (browsers reject "Access-Control-Allow-Origin: *"
# together with allow_credentials). Origins now come exclusively from
# settings.ALLOWED_ORIGINS (env-overridable) — localhost dev and the
# deployed Netlify/Vercel frontends are covered by the defaults.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
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

routers_to_include = [
    (health.router, "Health"),
    (auth.router, "Auth"),
    (farms.router, "Farms"),
    (fields.router, "Fields"),
    (uploads.router, "Uploads"),
    (results.router, "Results"),
    (notifications.router, "Notifications"),
    (predict.router, "Disease Prediction"),
    (predictions.router, "Predictions"),
]

for router, tag in routers_to_include:
    if router is not None:
        if router == health.router:
            app.include_router(router, tags=[tag])
        else:
            app.include_router(router, prefix=PREFIX, tags=[tag])


@app.get("/")
async def root():
    return {
        "message": "AgriScan 3D API",
        "status": "running",
        "version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agriscan-api"}