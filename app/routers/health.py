from fastapi import APIRouter
from app.database import get_client
from app.config import settings
import logging
import psutil
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health")
_start_time = time.time()


@router.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_s": round(time.time() - _start_time),
    }


@router.get("/health/full", summary="Detailed health check (DB + system)")
async def health_full():
    client = get_client()
    db_ok = False
    if client is None:
        logger.warning("Health check: MongoDB is not connected")
    else:
        try:
            await client.admin.command("ping")
            db_ok = True
        except Exception:
            logger.warning("Health check: MongoDB ping failed", exc_info=True)

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_s": round(time.time() - _start_time),
        "database": "connected" if db_ok else "unreachable",
        "system": {
            "cpu_pct": cpu,
            "mem_total_mb": round(mem.total / 1024 / 1024),
            "mem_used_pct": mem.percent,
        },
    }
