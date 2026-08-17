"""
Push Notification Service via Firebase Cloud Messaging (FCM).
Falls back to logging when FCM key is not configured.
"""

import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

FCM_URL = "https://fcm.googleapis.com/fcm/send"


async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """Send a FCM push notification to a single device token."""
    if not settings.FCM_SERVER_KEY:
        logger.info("[FCM stub] title=%s body=%s token=%s…", title, body, token[:12])
        return False

    payload = {
        "to": token,
        "notification": {
            "title": title,
            "body": body,
            "sound": "default",
            "badge": "1",
        },
        "data": data or {},
        "priority": "high",
    }

    headers = {
        "Authorization": f"key={settings.FCM_SERVER_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(FCM_URL, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            if result.get("success", 0) == 1:
                logger.info("FCM notification sent: %s", title)
                return True
            else:
                logger.warning("FCM send failed: %s", result)
                return False
    except httpx.HTTPError as e:
        logger.error("FCM HTTP error: %s", e)
        return False
