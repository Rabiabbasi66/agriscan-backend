from fastapi import APIRouter
from app.database import get_client
from app.config import settings
import psutil
import time

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
    # DB ping
    db_ok = False
    try:
        await get_client().admin.command("ping")
        db_ok = True
    except Exception:
        pass

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
