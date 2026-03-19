"""WebSocket connection manager for real-time game state updates."""

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per game room."""

    def __init__(self) -> None:
        self._rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if game_id not in self._rooms:
            self._rooms[game_id] = []
        self._rooms[game_id].append(websocket)
        logger.info("WS connected: game=%s, total=%d", game_id, len(self._rooms[game_id]))

    def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if game_id in self._rooms:
            self._rooms[game_id] = [ws for ws in self._rooms[game_id] if ws is not websocket]
            if not self._rooms[game_id]:
                del self._rooms[game_id]
        logger.info("WS disconnected: game=%s", game_id)

    async def broadcast(self, game_id: str, data: dict[str, Any]) -> None:
        """Send data to all connections in a game room."""
        if game_id not in self._rooms:
            return
        dead: list[WebSocket] = []
        for ws in self._rooms[game_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(game_id, ws)

    def get_connection_count(self, game_id: str) -> int:
        """Get number of active connections for a game."""
        return len(self._rooms.get(game_id, []))


# Singleton instance
connection_manager = ConnectionManager()
