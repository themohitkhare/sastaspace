"""Tests for WebSocket connection manager."""

from unittest.mock import AsyncMock

import pytest

from app.modules.sastadice.websocket import ConnectionManager


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def mock_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnectionManager:
    async def test_connect_adds_to_room(
        self, manager: ConnectionManager, mock_ws: AsyncMock
    ) -> None:
        await manager.connect("game1", mock_ws)
        assert manager.get_connection_count("game1") == 1
        mock_ws.accept.assert_called_once()

    async def test_disconnect_removes_from_room(
        self, manager: ConnectionManager, mock_ws: AsyncMock
    ) -> None:
        await manager.connect("game1", mock_ws)
        manager.disconnect("game1", mock_ws)
        assert manager.get_connection_count("game1") == 0

    async def test_broadcast_sends_to_all(self, manager: ConnectionManager) -> None:
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect("game1", ws1)
        await manager.connect("game1", ws2)

        await manager.broadcast("game1", {"type": "STATE_UPDATE", "data": "test"})

        ws1.send_json.assert_called_once_with({"type": "STATE_UPDATE", "data": "test"})
        ws2.send_json.assert_called_once_with({"type": "STATE_UPDATE", "data": "test"})

    async def test_broadcast_removes_dead_connections(self, manager: ConnectionManager) -> None:
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock(side_effect=Exception("closed"))
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect("game1", ws1)
        await manager.connect("game1", ws2)

        await manager.broadcast("game1", {"data": "test"})

        assert manager.get_connection_count("game1") == 1

    async def test_broadcast_no_room(self, manager: ConnectionManager) -> None:
        # Should not raise
        await manager.broadcast("nonexistent", {"data": "test"})

    async def test_multiple_games(self, manager: ConnectionManager) -> None:
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()

        await manager.connect("game1", ws1)
        await manager.connect("game2", ws2)

        assert manager.get_connection_count("game1") == 1
        assert manager.get_connection_count("game2") == 1
