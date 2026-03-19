# SastaDice Improvement Design Plan

## Executive Summary

This plan covers 4 improvement areas based on the comprehensive frontend + backend audit:
1. **Disconnected Features** — Wire up unused components & expose hidden backend capabilities
2. **Real-Time Upgrade** — Replace HTTP polling with WebSockets
3. **Game Mechanics Expansion** — New powers, tile types, and event visibility
4. **UX & Polish** — Mobile, animations, spectator mode, session edge cases

---

## Phase 1: Disconnected Features (Wire Up What Exists)

### 1A. Integrate TileSubmissionForm into Lobby

**Problem:** `TileSubmissionForm.jsx` exists (56 lines) but is never imported. Backend already supports `submitted_tiles` on the Player model and `UGC_24` board preset.

**Changes:**
- **LobbyView.jsx**: Add TileSubmissionForm below the player card when `board_preset === 'UGC_24'`
- **GameSettingsPanel.jsx**: Add `BOARD_PRESET` toggle (CLASSIC / UGC_24) to settings panel (host-only)
- **API**: `PATCH /games/{gameId}/settings` already accepts `board_preset` — no backend changes needed
- **Join flow**: Pass `submitted_tiles` array in `POST /games/{gameId}/join` body

**Estimate:** ~60 lines changed across 3 files

### 1B. Replace Inline Player Cards with KeyStatus Component

**Problem:** `KeyStatus.jsx` (68 lines) is a polished player card with key-turn animation, but LobbyView builds player cards inline (~40 lines of JSX).

**Changes:**
- **LobbyView.jsx**: Replace inline player card JSX with `<KeyStatus>` component
- Remove duplicate inline markup (~40 lines removed, 1 import added)
- Verify props match: `player`, `isMe`, `isHost`, `canKick`, `onKick`

**Estimate:** Net -30 lines (simplification)

### 1C. Expose Hidden Game Settings in UI

**Problem:** Backend supports settings the frontend doesn't expose:
- `chaos_level` (CHILL/NORMAL/CHAOS) — **partially exposed** in GameSettingsPanel but may need validation
- `income_tax_rate` — not shown anywhere
- `board_preset` — not in UI
- `starting_cash_multiplier` — not in UI

**Changes:**
- **GameSettingsPanel.jsx**: Add controls for `board_preset`, `starting_cash_multiplier` (0.5x, 1x, 2x presets), and `income_tax_rate` (5%, 10%, 15%)
- Group settings into collapsible sections: RULES, ECONOMY, BOARD

**Estimate:** ~80 lines added to GameSettingsPanel

### 1D. Surface Backend Tile Types Missing from Frontend

**Problem:** Backend defines tile types `NODE`, `GO_TO_JAIL`, `TELEPORT`, `MARKET` but frontend `TILE_TYPE_COLORS` only maps: PROPERTY, TAX, CHANCE, TRAP, BUFF, NEUTRAL, GO.

**Changes:**
- **TileComponent.jsx**: Add colors/icons for NODE (#FF6600), GO_TO_JAIL (#FF0000), TELEPORT (#9900FF), MARKET (#FF00FF)
- **TileCard.jsx**: Add display cards for these tile types with appropriate icons
- **RulesModal.jsx**: Update SPECIAL TILES section to document all tile types

**Estimate:** ~40 lines across 3 files

### 1E. Clean Up Dead Code

- **Delete** `PlayerList.jsx` (58 lines) — fully replaced by LobbyView inline + KeyStatus
- **Delete** `IsometricContainer.jsx` (26 lines) — no integration path, premature abstraction
- Keep TileSubmissionForm (will be integrated in 1A)
- Keep KeyStatus (will be integrated in 1B)

---

## Phase 2: Real-Time Upgrade (WebSocket Migration)

### 2A. Backend: Add WebSocket Endpoint

**New file:** `backend/app/modules/sastadice/websocket.py`

**Design:**
```
WS /api/v1/sastadice/games/{game_id}/ws?player_id={player_id}
```

**Message types (server → client):**
- `STATE_UPDATE` — Full game state (same as polling response)
- `TURN_CHANGE` — New turn started (player_id, phase)
- `AUCTION_TICK` — Auction timer update (remaining_seconds, current_bid, bidder)
- `TRADE_OFFER` — Incoming trade notification
- `PLAYER_JOIN` / `PLAYER_LEAVE` — Lobby events
- `GAME_START` — Game started
- `GAME_END` — Winner declared

**Message types (client → server):**
- `PING` — Keepalive (every 30s)
- `ACTION` — Same payload as POST /action (roll, buy, bid, etc.)

**Implementation approach:**
- Use FastAPI's built-in WebSocket support (`@router.websocket`)
- Maintain a `ConnectionManager` class with per-game rooms
- On any game state mutation, broadcast `STATE_UPDATE` to all connected clients
- Keep HTTP endpoints as fallback (graceful degradation)

**Dependencies:** None new — FastAPI includes WebSocket support via Starlette

### 2B. Frontend: WebSocket Hook

**New file:** `frontends/sastadice/src/hooks/useWebSocket.js`

**Design:**
```javascript
useWebSocket(gameId, playerId) → {
  connected: boolean,
  send: (type, payload) => void,
  lastMessage: object,
  reconnect: () => void
}
```

**Features:**
- Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- Heartbeat ping every 30s
- Falls back to `useSastaPolling` if WebSocket fails 3 consecutive times
- Updates Zustand store on `STATE_UPDATE` messages

### 2C. Frontend: Migrate Pages to WebSocket

**GamePage.jsx changes:**
- Replace `useSastaPolling(gameId, pollingInterval)` with `useWebSocket(gameId, playerId)`
- Remove dynamic polling interval logic (no longer needed)
- Keep `connectionLost` banner, driven by WebSocket `connected` state
- Actions still call HTTP endpoints (reliability) OR send via WebSocket `ACTION` message

**LobbyPage.jsx changes:**
- Replace `useSastaPolling(gameId, 2000)` with `useWebSocket(gameId, playerId)`
- Lobby events (join/leave/ready) arrive as WebSocket messages

**AuctionModal.jsx changes:**
- Remove client-side countdown timer
- Use server-pushed `AUCTION_TICK` for authoritative timer
- Eliminates timer drift between clients

### 2D. Backward Compatibility

- HTTP polling endpoints remain unchanged (mobile/fallback)
- `useSastaPolling` hook kept as fallback, not deleted
- WebSocket URL derived from existing API base URL (ws:// or wss://)
- Traefik config needs WebSocket upgrade headers (add to docker-compose labels)

**Estimate:** ~200 lines backend, ~150 lines frontend new, ~50 lines frontend modified

---

## Phase 3: Game Mechanics Expansion

### 3A. Buff Inventory & Visualization System

**Problem:** Players can hold buffs (VPN, DDOS, PEEK) but there's no persistent inventory UI. Buff status is only visible during the action phase.

**Changes:**
- **New component:** `BuffInventory.jsx` — Small HUD element showing active buff with icon
  - VPN: Shield icon, "BLOCKS NEXT RENT"
  - DDOS: Lightning icon, "TAP TO USE" (during PRE_ROLL)
  - Show "NO BUFF" when empty
- **PlayerPanel.jsx**: Add buff indicator next to each player's cash
- **BoardView.jsx**: Enhance blocked tile overlay — show round countdown ("BLOCKED 2 MORE ROUNDS")
- **TileComponent.jsx**: Add free-landing indicator (green glow, "FREE THIS ROUND")

**Estimate:** ~80 lines new component, ~30 lines modifications

### 3B. Bankruptcy Auction Queue UI

**Problem:** When a player goes bankrupt, their properties enter a state auction queue. No UI for this.

**Changes:**
- **New component:** `BankruptcyAuctionBanner.jsx` — Top banner showing queued properties
- **GamePage.jsx**: Render banner when `game.bankruptcy_auction_queue` is non-empty
- Transitions into standard AuctionModal for each property in queue

**Estimate:** ~50 lines new component, ~10 lines integration

### 3C. Event Deck Transparency

**Problem:** Players can't see how many events remain in deck or what events exist.

**Changes:**
- **CenterStage.jsx**: Add small "DECK: X/35" counter
- **PeekEventsModal.jsx**: Enhance to show event descriptions, not just names
- **EventToast.jsx**: Map remaining "DEFAULT" event types to proper icons/colors

**Estimate:** ~30 lines modified

### 3D. AFK/Disconnect Player Indicators

**Problem:** Backend tracks `disconnected` and `afk_turns` but frontend doesn't visualize them.

**Changes:**
- **PlayerPanel.jsx**: Show "DISCONNECTED" badge (red, pulsing) for `player.disconnected === true`
- **PlayerPanel.jsx**: Show "AFK (X turns)" warning for `afk_turns > 0`
- **PlayerToken.jsx**: Dim/grayscale token for disconnected players on board

**Estimate:** ~20 lines modified

### 3E. Dynamic Economy Indicators

**Problem:** Backend has `DynamicEconomyScaler` that adjusts costs after round 10, but players have no visibility.

**Changes:**
- **CenterStage.jsx**: Show current GO bonus amount (base + inflation)
- **TileCard.jsx**: If `game.rent_multiplier !== 1.0`, show "MARKET CRASH: RENT HALVED" or "BULL MARKET: RENT +50%"
- **GameSettingsPanel.jsx** (in-game read-only): Show active global modifiers

**Estimate:** ~25 lines modified

---

## Phase 4: UX & Polish

### 4A. Mobile Responsiveness

**Problem:** Board uses fixed grid sizing with ResizeObserver but small screens get cramped tiles.

**Changes:**
- **BoardView.jsx**: Add breakpoint-aware tile sizing
  - `< 640px`: Compact mode — smaller tiles, abbreviated names, stack CenterStage below board
  - `640-1024px`: Current layout with slightly smaller fonts
  - `> 1024px`: Current layout (no change)
- **GamePage.jsx**: Stack layout on mobile (board on top, center stage below, player panel as bottom drawer)
- **PlayerPanel.jsx**: Convert to slide-out drawer on mobile (hamburger trigger)
- **CenterActionButton.jsx**: Full-width buttons on mobile, larger touch targets (min 48px)

**Estimate:** ~100 lines of Tailwind responsive classes

### 4B. Enhanced Animations

**Changes:**
- **Property purchase**: Tile border animates from dashed → solid with color fill sweep
- **Rent payment**: Cash flies from payer to payee avatar (particle effect)
- **Bankruptcy**: Player token shatters/fades with red flash on board
- **Buff activation**: Shield shimmer (VPN), lightning strike (DDOS) overlay on board
- **Turn transition**: Smoother crossfade instead of hard cut

**Implementation:** CSS keyframes in `index.css` + conditional classes in components. No animation library needed.

**Estimate:** ~60 lines CSS, ~40 lines JSX

### 4C. Session Restoration Edge Cases

**Problem:** App.jsx restoration has gaps: race conditions on double-mount, stale playerId after game reset.

**Changes:**
- **App.jsx GameRoute**: Add `AbortController` to restoration fetch to cancel on unmount
- **App.jsx GameRoute**: Check `game.status === 'FINISHED'` during restoration → redirect to victory
- **useGameStore.js**: Add `lastRestoredAt` timestamp to prevent rapid re-restoration
- **GamePage.jsx**: If `playerId` not in `game.players`, switch to spectator mode instead of error

**Estimate:** ~30 lines modified

### 4D. Spectator Mode Enhancement

**Problem:** Spectator mode (null playerId) works but is bare — no indication you're spectating, action buttons still render.

**Changes:**
- **GamePage.jsx**: Show "SPECTATING" banner at top when `playerId` is null
- **CenterActionButton.jsx**: Hide all action buttons for spectators
- **PlayerPanel.jsx**: Hide TRADE buttons for spectators
- **AuctionModal.jsx**: Show auction progress but disable bid buttons for spectators

**Estimate:** ~20 lines of conditional rendering

### 4E. Keyboard Shortcuts Enhancement

**Problem:** Only Space (roll/end turn), Y (buy), N (pass) exist.

**Changes:**
- **GamePage.jsx**: Add keyboard handler:
  - `T` — Open trade with next player
  - `M` — Open property manager
  - `R` — Open rules
  - `Escape` — Close any open modal
  - `1/2/3` — Quick bid +$10/+$50/+$100 during auction
- Show shortcut hints on buttons (small gray text)

**Estimate:** ~40 lines in GamePage, ~10 lines across button components

---

## Implementation Priority & Sequencing

### Sprint 1: Quick Wins (Phase 1 + 4C/4D)
1. 1E — Delete dead code (IsometricContainer, PlayerList)
2. 1B — Integrate KeyStatus into LobbyView
3. 1D — Add missing tile type colors/icons
4. 4C — Fix session restoration edge cases
5. 4D — Enhance spectator mode
6. 1A — Wire up TileSubmissionForm + board preset setting
7. 1C — Expose hidden game settings

### Sprint 2: Visibility & Feedback (Phase 3)
1. 3A — Buff inventory & blocked/free tile visualization
2. 3D — AFK/disconnect indicators
3. 3E — Dynamic economy indicators
4. 3C — Event deck transparency
5. 3B — Bankruptcy auction queue UI

### Sprint 3: Mobile & Polish (Phase 4A/4B/4E)
1. 4A — Mobile responsive layout
2. 4E — Keyboard shortcuts
3. 4B — Enhanced animations

### Sprint 4: Real-Time (Phase 2)
1. 2A — Backend WebSocket endpoint + ConnectionManager
2. 2B — Frontend useWebSocket hook
3. 2C — Migrate GamePage + LobbyPage
4. 2D — Traefik WebSocket config + fallback testing

**Rationale:** Sprints 1-3 deliver visible improvements immediately with low risk. Sprint 4 (WebSocket) is the highest-effort, highest-risk change and benefits from the stabilized codebase.

---

## Testing Strategy

- **Each phase**: Run `make ci-fast` before committing
- **Phase 1**: Update existing component tests for KeyStatus integration, add TileSubmissionForm integration test
- **Phase 2**: Add WebSocket hook unit tests with mock WS server, E2E test for reconnection
- **Phase 3**: Add component tests for new BuffInventory, BankruptcyAuctionBanner
- **Phase 4**: Add Playwright mobile viewport E2E tests, keyboard shortcut tests

## Files Affected Summary

| Phase | New Files | Modified Files | Deleted Files |
|-------|-----------|----------------|---------------|
| 1     | 0         | 5 (LobbyView, GameSettingsPanel, TileComponent, TileCard, RulesModal) | 2 (IsometricContainer, PlayerList) |
| 2     | 2 (websocket.py, useWebSocket.js) | 4 (GamePage, LobbyPage, AuctionModal, docker-compose) | 0 |
| 3     | 2 (BuffInventory, BankruptcyAuctionBanner) | 5 (PlayerPanel, BoardView, TileComponent, CenterStage, EventToast) | 0 |
| 4     | 0         | 7 (BoardView, GamePage, PlayerPanel, CenterActionButton, AuctionModal, App, index.css) | 0 |
