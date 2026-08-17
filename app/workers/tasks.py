"""
Celery Tasks — background image processing pipeline.

Pipeline per upload:
  1. Download images from S3
  2. Run YOLOv8 detection on each image
  3. Calculate NDVI
  4. Generate 3D point cloud (COLMAP or mock)
  5. Upload annotated images + PLY back to S3
  6. Save AnalysisResult to MongoDB
  7. Send push notification to farmer
"""

from __future__ import annotations
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import asyncio
import os
import shutil

import cv2
import numpy as np
from bson import ObjectId

logger = logging.getLogger(__name__)

# Celery app
try:
    from celery import Celery
    
    # Use environment variables or defaults
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    celery_app = Celery(
        "agriscan",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
    def process_upload_task(self, upload_id: str, job_id: str):
        """Celery task wrapper — runs async pipeline via asyncio.run()."""
        try:
            asyncio.run(_process_upload_inline(upload_id, job_id))
        except Exception as e:
            logger.error(f"Task failed for upload {upload_id}: {e}")
            raise

except ImportError:
    logger.warning("Celery not installed — tasks will run inline (dev mode).")
    celery_app = None

    def process_upload_task(upload_id: str, job_id: str):
        """Fallback function when Celery is not installed."""
        logger.warning("Running task inline (Celery not installed)")
        return asyncio.run(_process_upload_inline(upload_id, job_id))


# ── Core pipeline (also used as inline fallback) ─────────────────────────────

async def _process_upload_inline(
    upload_id: str,
    job_id: str,
    db=None,
) -> None:
    """Full processing pipeline. Runs inside Celery worker OR inline (dev)."""
    # Import here to avoid circular imports
    from app.database import db
    from app.ai.detector import run_detection, encode_image_to_bytes
    from app.ai.ndvi import calculate_ndvi_rgb
    from app.ai.pointcloud import generate_pointcloud_colmap
    from app.utils.storage import upload_file_to_s3
    from app.services.notification_service import send_push_notification

    # Make sure database is connected
    if db.client is None:
        await db.connect()
        logger.info("Database connected for task processing")

    async def _set_job(status: str, progress: int, error: str | None = None):
        update = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.now(timezone.utc),
        }
        if error:
            update["error_msg"] = error
        if status == "running" and progress == 5:
            update["started_at"] = datetime.now(timezone.utc)
        if status in ("done", "failed"):
            update["finished_at"] = datetime.now(timezone.utc)
        
        # Check if jobs collection exists, if not, skip
        try:
            await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": update})
        except Exception as e:
            logger.warning(f"Could not update job {job_id}: {e}")

    try:
        await _set_job("running", 5)
        t0 = datetime.now(timezone.utc)

        # Get upload
        upload = await db.uploads.find_one({"_id": ObjectId(upload_id)})
        if not upload:
            raise ValueError(f"Upload {upload_id} not found")

        await db.uploads.update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc)}},
        )

        all_detections = []
        health_scores = []
        ndvi_values = []
        image_paths = []

        await _set_job("running", 15)

        with tempfile.TemporaryDirectory() as tmpdir:
            # ── Step 1: Download images ──────────────────────────────
            files = upload.get("files", [])
            if not files:
                raise ValueError(f"No files found in upload {upload_id}")
                
            for i, file_info in enumerate(files):
                if file_info.get("file_type") != "image":
                    continue
                try:
                    local_path = Path(file_info["s3_url"])

                    if not local_path.exists():
                        logger.warning("Image not found: %s", local_path)
                        continue

                    img_path = Path(tmpdir) / f"img_{i}.jpg"
                    shutil.copy(local_path, img_path)
                    image_paths.append(str(img_path))
                except Exception as e:
                    logger.warning("Could not download %s: %s", file_info.get("s3_url", ""), e)

            if not image_paths:
                raise ValueError(f"No images could be downloaded for upload {upload_id}")

            await _set_job("running", 30)

            # ── Step 2: YOLOv8 + NDVI per image ─────────────────────
            for idx, img_path in enumerate(image_paths):
                image_bgr = cv2.imread(img_path)
                if image_bgr is None:
                    logger.warning(f"Could not read image {img_path}")
                    continue

                # Detection
                det_result = run_detection(image_bgr)
                health_scores.append(det_result["health_score"])

                # NDVI
                ndvi_mean, _ = calculate_ndvi_rgb(image_bgr)
                ndvi_values.append(ndvi_mean)

                # Upload annotated image
                annotated_bytes = encode_image_to_bytes(det_result["annotated_image"])
                ann_url = upload_file_to_s3(
                    annotated_bytes,
                    f"annotated_{Path(img_path).name}",
                    folder="results/annotated",
                )
                
                # Get original URL
                original_url = upload["files"][idx].get("s3_url") if idx < len(upload["files"]) else img_path

                for d in det_result["detections"]:
                    all_detections.append({
                        "image_url": original_url,
                        "label": d["label"],
                        "confidence": d["confidence"],
                        "bbox": d["bbox"],
                        "severity": d["severity"],
                        "annotated_url": ann_url,
                    })

                progress = 30 + int((idx + 1) / max(len(image_paths), 1) * 35)
                await _set_job("running", progress)

            # ── Step 3: 3D Point Cloud ───────────────────────────────
            await _set_job("running", 70)
            point_cloud_url = None
            if len(image_paths) >= 3:
                try:
                    ply_path = generate_pointcloud_colmap(image_paths, tmpdir)
                    if ply_path and os.path.exists(ply_path):
                        with open(ply_path, "rb") as fh:
                            ply_bytes = fh.read()
                        point_cloud_url = upload_file_to_s3(
                            ply_bytes, "pointcloud.ply", folder="results/pointclouds"
                        )
                except Exception as e:
                    logger.warning(f"Point cloud generation failed: {e}")
            else:
                logger.info("Not enough images for point cloud (need ≥ 3, got %d)", len(image_paths))

        # ── Step 4: Aggregate results ───────────────────────────────
        await _set_job("running", 80)

        health_score = float(np.mean(health_scores)) if health_scores else 80.0
        ndvi_mean = float(np.mean(ndvi_values)) if ndvi_values else None

        # Summarise diseases
        disease_counter: dict = {}
        for d in all_detections:
            key = d["label"]
            if key not in disease_counter:
                disease_counter[key] = {"count": 0, "total_conf": 0.0, "severity": d["severity"]}
            disease_counter[key]["count"] += 1
            disease_counter[key]["total_conf"] += d["confidence"]

        total_det = len(all_detections) or 1
        disease_summary = [
            {
                "label": label,
                "count": v["count"],
                "area_pct": round(v["count"] / total_det * 100, 2),
                "severity": v["severity"],
                "avg_confidence": round(v["total_conf"] / v["count"], 2),
            }
            for label, v in disease_counter.items()
        ]

        # ── Step 5: PDF report ──────────────────────────────────────
        await _set_job("running", 88)
        pdf_url = None
        try:
            from app.services.report_service import generate_pdf_report
            pdf_url = await generate_pdf_report(
                upload_id=upload_id,
                field_id=upload["field_id"],
                health_score=health_score,
                disease_summary=disease_summary,
                detections=all_detections,
                db=db,
            )
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")
            pdf_url = None

        processing_time = (datetime.now(timezone.utc) - t0).total_seconds()

        # ── Step 6: Save analysis result ────────────────────────────
        analysis_data = {
            "upload_id": upload_id,
            "field_id": upload["field_id"],
            "health_score": health_score,
            "ndvi_mean": ndvi_mean,
            "disease_summary": disease_summary,
            "detections": all_detections,
            "point_cloud_url": point_cloud_url,
            "report_pdf_url": pdf_url,
            "processing_time_s": round(processing_time, 2),
            "created_at": datetime.now(timezone.utc),
        }
        
        await db.analysis_results.update_one(
            {"upload_id": upload_id},
            {"$set": analysis_data},
            upsert=True,
        )

        await db.uploads.update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"status": "done", "updated_at": datetime.now(timezone.utc)}},
        )
        await _set_job("done", 100)
        logger.info("Upload %s processed in %.2fs | health=%.1f%%", upload_id, processing_time, health_score)

        # ── Step 7: Push notification ────────────────────────────────
        try:
            uploaded_by = upload.get("uploaded_by")
            if uploaded_by:
                user = await db.users.find_one({"_id": ObjectId(uploaded_by)})
                if user and user.get("fcm_token"):
                    await send_push_notification(
                        token=user["fcm_token"],
                        title="AgriScan Analysis Complete",
                        body=f"Field health: {health_score:.1f}% · {len([d for d in disease_summary if d['severity'] != 'healthy'])} diseases found.",
                        data={"upload_id": upload_id, "field_id": upload["field_id"]},
                    )
        except Exception as e:
            logger.warning(f"Push notification failed: {e}")

    except Exception as exc:
        logger.exception("Processing failed for upload %s", upload_id)
        await _set_job("failed", 0, str(exc))
        await db.uploads.update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"status": "failed", "updated_at": datetime.now(timezone.utc)}},
        )
        raise