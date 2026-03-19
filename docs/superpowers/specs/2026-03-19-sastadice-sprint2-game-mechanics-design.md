# SastaDice Sprint 2: Game Mechanics Expansion — Design Spec

**Date:** 2026-03-19
**Status:** Approved
**Scope:** Frontend-only. All backend data already exists — this sprint surfaces it in the UI.

---

## Goal

Make hidden game state visible: buff ownership, AFK/disconnect status, economy conditions, event deck size, blocked/free tile countdowns, and bankruptcy auction queue. No new component files — all changes are additions to existing components.

## Decisions

- Buff display: Inline badges in PlayerPanel per player (no separate HUD component)
- Economy/deck indicators: Inside CenterStage (no separate info bar)
- Tile enhancements: Minimal — round count text on blocked, subtle green border on free-landing
- Bankruptcy banner: Inline conditional in GamePage (no separate component file)
- Dropped: PlayerToken grayscale for disconnected (YAGNI), GO inflation indicator (always increasing, not useful)

---

## Changes by File

### 1. PlayerPanel.jsx — Buff Badges + AFK/Disconnect Indicators

**Location:** Per-player row, after the turn indicator area (~line 49)

**Buff badge:**
- `player.active_buff === 'VPN'` → `<span>` with cyan bg: "VPN"
- `player.active_buff === 'DDOS'` → `<span>` with magenta bg: "DDOS"
- `player.active_buff === 'PEEK'` → `<span>` with yellow bg: "PEEK"
- `player.active_buff` is null/undefined → render nothing

**AFK/Disconnect badge:**
- `player.disconnected === true` → Red pulsing badge: "DISCONNECTED"
- `player.afk_turns > 0` (and not disconnected) → Orange badge: "AFK (N/3)"
- Neither → render nothing

**Styling:** 9-10px font-zero, border-brutal-sm, inline with existing badges. Brutalist aesthetic.

**Props:** No new props needed — `players` array already contains `active_buff`, `disconnected`, `afk_turns`.

### 2. CenterStage.jsx — Deck Counter + Economy Indicator

**New props (passed from GamePage):**
- `eventDeckSize: number` — length of `game.event_deck`
- `rentMultiplier: number` — `game.rent_multiplier`

**Event deck counter** (near dice/event message area):
- Text: `DECK: {eventDeckSize}/35`
- Style: 10px font-data, opacity-50

**Economy indicator** (near cash/stash display):
- `rentMultiplier < 1.0` → Red text: `MARKET CRASH: RENT -{Math.round((1 - rentMultiplier) * 100)}%`
- `rentMultiplier > 1.0` → Green text: `BULL MARKET: RENT +{Math.round((rentMultiplier - 1) * 100)}%`
- `rentMultiplier === 1.0` → render nothing

### 3. TileComponent.jsx — Blocked Countdown + Free Landing

**Blocked tile countdown:**
- New prop: `blockedRoundsRemaining: number | null`
- When blocked overlay renders, change "BLOCKED" text to `BLOCKED ({blockedRoundsRemaining})`
- Only show count when `blockedRoundsRemaining > 0`

**Free-landing indicator:**
- New prop: `isFreeLanding: boolean`
- When true: Add green border (`border-green-400`) and small "FREE" label
- Style: 9px font-zero text-green-500, positioned at bottom of tile

### 4. BoardView.jsx — Pass New Props to TileComponent

**Compute and pass:**
- `blockedRoundsRemaining`: `tile.blocked_until_round ? tile.blocked_until_round - currentRound : null`
- `isFreeLanding`: `tile.free_landing_until_round ? tile.free_landing_until_round >= currentRound : false`

No other changes to BoardView.

### 5. GamePage.jsx — Bankruptcy Banner + New CenterStage Props

**CenterStage props addition:**
```
eventDeckSize={game?.event_deck?.length ?? 0}
rentMultiplier={game?.rent_multiplier ?? 1.0}
```

**Bankruptcy auction banner** (after PlayerPanel, before modals):
- Condition: `game?.bankruptcy_auction_queue?.length > 0`
- Render: Orange/amber banner with text: "BANKRUPTCY AUCTION: {count} PROPERTIES QUEUED"
- List property names by looking up tile IDs in `game.board`
- Style: Brutalist — amber bg, black border, font-zero, pulsing animation

---

## Testing Strategy

| Component | Test File | What to Test |
|-----------|-----------|-------------|
| PlayerPanel | Modify existing `PlayerPanel.test.jsx` | Buff badge renders for VPN/DDOS/PEEK; nothing when null. Disconnected badge renders. AFK badge shows turns. |
| CenterStage | Create `CenterStage.test.jsx` | Deck counter shows correct count. Economy indicator shows crash/bull/nothing. |
| TileComponent | Modify existing `TileComponent.test.jsx` | Blocked countdown text. Free-landing green border and label. |
| GamePage | Modify existing `GamePage.test.jsx` | Bankruptcy banner renders when queue non-empty, hidden when empty. |

---

## Files Affected Summary

| File | Action | Lines Added (est.) |
|------|--------|--------------------|
| PlayerPanel.jsx | Modify | ~25 |
| CenterStage.jsx | Modify | ~20 |
| TileComponent.jsx | Modify | ~15 |
| BoardView.jsx | Modify | ~4 |
| GamePage.jsx | Modify | ~15 |
| PlayerPanel.test.jsx | Modify | ~40 |
| CenterStage.test.jsx | Create | ~50 |
| TileComponent.test.jsx | Modify | ~20 |
| GamePage.test.jsx | Modify | ~20 |

**Total: 5 files modified, 1 test file created. ~210 lines added.**

No new component files. No backend changes.
