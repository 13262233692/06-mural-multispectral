"""按图像集分组的 WebSocket 连接中枢，支撑多用户实时协作。"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class CollaborationHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._users: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def join(self, imageset_id: str, websocket: WebSocket, username: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[imageset_id].add(websocket)
            self._users[websocket] = username
        await self.broadcast(imageset_id, {
            "type": "presence",
            "event": "join",
            "username": username,
            "users": self.online_users(imageset_id),
        }, exclude=websocket)

    async def leave(self, imageset_id: str, websocket: WebSocket) -> None:
        username = self._users.pop(websocket, None)
        async with self._lock:
            self._rooms[imageset_id].discard(websocket)
        if username:
            await self.broadcast(imageset_id, {
                "type": "presence",
                "event": "leave",
                "username": username,
                "users": self.online_users(imageset_id),
            })

    def online_users(self, imageset_id: str) -> list[str]:
        return sorted({self._users[ws] for ws in self._rooms[imageset_id] if ws in self._users})

    async def broadcast(self, imageset_id: str, message: dict, exclude: WebSocket | None = None) -> None:
        dead: list[WebSocket] = []
        payload = json.dumps(message, ensure_ascii=False, default=str)
        for websocket in list(self._rooms.get(imageset_id, set())):
            if websocket is exclude:
                continue
            try:
                await websocket.send_text(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            async with self._lock:
                self._rooms[imageset_id].discard(websocket)
                self._users.pop(websocket, None)


hub = CollaborationHub()
