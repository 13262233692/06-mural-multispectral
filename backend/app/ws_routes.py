from __future__ import annotations
"""协作 WebSocket：转发在线光标，转发标注事件由 API 层广播。"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.security import decode_token
from app.ws_hub import hub

router = APIRouter()


@router.websocket("/ws/imagesets/{imageset_id}")
async def collaboration_socket(websocket: WebSocket, imageset_id: str) -> None:
    token = websocket.query_params.get("token", "")
    try:
        username = decode_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await hub.join(imageset_id, websocket, username)
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "cursor":
                await hub.broadcast(imageset_id, {
                    "type": "cursor",
                    "username": username,
                    "x": message.get("x"),
                    "y": message.get("y"),
                }, exclude=websocket)
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await hub.leave(imageset_id, websocket)
    except Exception:
        await hub.leave(imageset_id, websocket)
