# SastaDice Sprint 4: WebSocket Real-Time Migration — Design Spec

**Date:** 2026-03-19
**Status:** Approved

---

## Goal

Replace HTTP polling with WebSocket connections for real-time game state updates. Keep polling as fallback for graceful degradation.

## Architecture

### Backend

**New WebSocket endpoint:**
```
WS /api/v1/sastadice/games/{game_id}/ws?player_id={player_id}
```

**ConnectionManager** — in-memory per-game room management:
- Tracks active WebSocket connections per game
- On any game state mutation → broadcasts full GameStateResponse to all connected clients
- Heartbeat ping every 30s, client pongs back
- Disconnect cleanup on WebSocket close

**Broadcast injection:** After every `repository.update(game)` call in GameOrchestrator, call `connection_manager.broadcast(game_id, game_state)`. Rather than patching 40+ mutation sites, we override the repository's update method to trigger broadcasts automatically.

**No Redis pub/sub needed** — single-process FastAPI with in-memory ConnectionManager is sufficient for the current scale. Redis pub/sub would be needed for multi-process deployments but that's YAGNI.

### Frontend

**New hook: `useWebSocket.js`**
```javascript
useWebSocket(gameId, playerId) → {
  connected: boolean,
  lastMessage: object | null,
}
```

- Auto-connect on mount, disconnect on unmount
- Auto-reconnect with exponential backoff (1s, 2s, 4s, max 8s)
- Falls back to `useSastaPolling` after 3 consecutive WebSocket failures
- On `STATE_UPDATE` message → calls `setGame(game, version)` directly

**Migration:** GamePage and LobbyPage switch from `useSastaPolling` to `useWebSocket`, with polling as automatic fallback.

---

## Scope Decisions

- **Keep HTTP action endpoints** — Actions still go through `POST /action`. WebSocket is for server→client state pushes only. Simpler, more reliable.
- **No client→server WebSocket messages** — All mutations go through HTTP. WS is read-only subscription.
- **No Redis pub/sub** — Single process, in-memory ConnectionManager.
- **Keep polling fallback** — If WS fails 3 times, automatically switch to polling. No user action needed.
- **Full state broadcasts** — Send entire GameStateResponse on every mutation. No incremental diffs (YAGNI, state is 10-50KB).

---

## Changes by File

### Backend — New Files

#### `backend/app/modules/sastadice/websocket.py`
- `ConnectionManager` class: `connect(game_id, ws)`, `disconnect(game_id, ws)`, `broadcast(game_id, data)`
- WebSocket route handler: accept connection, add to room, listen for pongs, handle disconnect
- Singleton `connection_manager` instance

#### `backend/app/modules/sastadice/router.py`
- Add WebSocket route: `@router.websocket("/games/{game_id}/ws")`
- Import and use ConnectionManager

### Backend — Modified Files

#### `backend/app/modules/sastadice/repository.py`
- Add optional `on_update` callback hook
- After successful `update()`, call the callback with `(game_id, updated_game)`

#### `backend/app/modules/sastadice/services/game_orchestrator.py`
- Wire repository's `on_update` callback to `connection_manager.broadcast()`

### Frontend — New Files

#### `frontends/sastadice/src/hooks/useWebSocket.js`
- WebSocket connection hook with auto-reconnect and polling fallback
- Derives WS URL from current API base URL (http→ws, https→wss)

### Frontend — Modified Files

#### `frontends/sastadice/src/pages/GamePage.jsx`
- Replace `useSastaPolling(gameId, interval)` with `useWebSocket(gameId, playerId)`
- Keep `connectionLost` state driven by WS `connected` status
- Keep manual refetch for action callbacks (HTTP actions still trigger version bump → WS broadcast)

#### `frontends/sastadice/src/pages/LobbyPage.jsx`
- Replace `useSastaPolling(gameId, 2000)` with `useWebSocket(gameId, playerId)`

---

## Message Format (Server → Client)

```json
{
  "type": "STATE_UPDATE",
  "version": 42,
  "game": { /* full GameSession */ }
}
```

Single message type keeps it simple. Could add PING/PONG but browser WebSocket API handles that natively.

---

## Testing Strategy

| Component | Test Approach |
|-----------|--------------|
| ConnectionManager | pytest — test connect/disconnect/broadcast with mock WebSockets |
| WebSocket route | pytest with httpx WebSocket client — test handshake, state push, disconnect |
| useWebSocket hook | Vitest — mock WebSocket, test connect/reconnect/fallback |
| GamePage migration | Existing tests still pass (they mock the store, not the transport) |

---

## Files Affected

| File | Action | Lines (est.) |
|------|--------|-------------|
| `backend/app/modules/sastadice/websocket.py` | Create | ~60 |
| `backend/app/modules/sastadice/router.py` | Modify | ~15 |
| `backend/app/modules/sastadice/repository.py` | Modify | ~10 |
| `backend/app/modules/sastadice/services/game_orchestrator.py` | Modify | ~5 |
| `backend/tests/modules/sastadice/test_websocket.py` | Create | ~80 |
| `frontends/sastadice/src/hooks/useWebSocket.js` | Create | ~70 |
| `frontends/sastadice/src/pages/GamePage.jsx` | Modify | ~10 |
| `frontends/sastadice/src/pages/LobbyPage.jsx` | Modify | ~5 |
| `frontends/sastadice/tests/hooks/useWebSocket.test.js` | Create | ~60 |
| `docker-compose.yml` | Modify | ~2 (Traefik WS headers) |
