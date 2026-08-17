"""
WebSocket endpoint for real-time job progress notifications.
Connect: ws://host/api/v1/notifications/ws/{user_id}
Server sends JSON messages as job progresses.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_db
import asyncio
import json
import logging

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)
logger = logging.getLogger(__name__)

# In-memory connection registry {user_id: [WebSocket]}
_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    """
    Real-time upload progress and alert stream.
    Client connects once per session; server pushes job updates.
    """
    await websocket.accept()
    _connections.setdefault(user_id, []).append(websocket)
    logger.info("WS connected: user=%s", user_id)

    try:
        while True:
            # Heartbeat every 30s to keep alive
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        _connections[user_id].remove(websocket)
        logger.info("WS disconnected: user=%s", user_id)


async def push_to_user(user_id: str, message: dict) -> None:
    """Broadcast a message to all WS connections for a user."""
    sockets = _connections.get(user_id, [])
    dead = []
    for ws in sockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        sockets.remove(ws)


@router.get("/test-push/{user_id}", include_in_schema=False)
async def test_push(user_id: str):
    """Dev endpoint to test WS push."""
    await push_to_user(user_id, {
        "type": "job_update",
        "status": "done",
        "progress": 100,
        "message": "Analysis complete!",
    })
    return {"pushed": True}
