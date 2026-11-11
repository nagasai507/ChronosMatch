
"""Manage WebSocket connections and market event broadcasting."""

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class ConnectionManager:
    """Manage connected market clients."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        disconnected = []

        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)
