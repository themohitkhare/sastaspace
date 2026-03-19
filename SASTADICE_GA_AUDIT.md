# SastaDice GA Audit

**Date**: 2026-03-18
**Status**: Pre-GA — playable but missing core "Bring Your Own Powers" identity

---

## Current State Summary

SastaDice is a **fully playable Monopoly variant** with a tech/hacker theme, multiplayer lobby, dynamic economy, 35 events, trading, auctions, upgrades, CPU opponents, and a polished brutalist UI. The core game loop works end-to-end.

However, the **original "bring your own powers" vision has been lost** — players currently join with auto-generated tiles and have no way to customize their contributions or bring unique abilities.

---

## What's Built (Complete)

### Core Game Loop
- Lobby: create, join via code, host settings, ready-up, kick, CPU opponents
- Board: dynamic sizing, perimeter mapping, 2 presets (CLASSIC, UGC_24)
- Dice: 2d6, doubles extra turn, triple doubles jail, stimulus check
- Turn FSM: PRE_ROLL → MOVING → DECISION → AUCTION → POST_TURN
- Polling multiplayer with version tracking
- Turn timer (30s default), AFK ghost mode

### Economy
- Property buying, rent (base + set bonus + upgrades + multipliers)
- 2 upgrade levels: SCRIPT KIDDIE / 1337 HAXXOR (requires full color set)
- Dynamic economy scaling (rent/costs scale after round 10, GO inflation with cap)
- Auto-liquidation, bankruptcy, state auction queue

### Special Tiles
- GO, THE GLITCH (teleport), SERVER DOWNTIME (jail), BLACK MARKET (buffs)
- 404: ACCESS DENIED (go to jail), NODE (railroad equivalent, rent = $50 * 2^(n-1))
- CHANCE, PROPERTY, TAX, BUFF, TRAP, NEUTRAL

### Buffs (Black Market Only)
- VPN ($200): Block next rent
- DDoS ($150): Disable a tile for 1 round
- Insider Info ($100): Peek at next 3 events

### Events (35 total)
- 8 Cash Gain, 7 Cash Loss, 5 Take-That, 6 Sabotage, 5 Movement, 4 Global
- Chaos level affects deck composition

### Win Conditions
- Sudden Death (richest at round limit)
- Last Standing (last player standing)
- First to Cash (race to target amount)

### Trading & Auctions
- Player-to-player trades (cash + properties)
- Timed auctions when property is passed on
- Bankruptcy state auctions

### Frontend
- Isometric board, dice display, player panels
- Auction/Trade/Property modals, victory screen
- Toast notifications, contextual tooltips
- Mobile responsive

### Testing
- 20+ backend test files, 18+ frontend tests, E2E with Playwright
- Simulation manager, invariant checker, snapshot manager

---

## What's Missing for GA

### P0 — Restore Core Identity ("Bring Your Own")

| # | Gap | Detail |
|---|-----|--------|
| 1 | **Tile submission UI hidden** | `TileSubmissionForm.jsx` exists but `LobbyView.jsx` never renders it. Players join with auto-generated generic tiles. The core "bring your own" mechanic is dead. |
| 2 | **`effect_config` unused** | Every tile has `effect_config: dict` but it's never read during gameplay. Player-submitted TAX/BUFF/TRAP tiles use hardcoded formulas instead. |
| 3 | **No "Powers" system** | Only Black Market buffs exist. No player-selected abilities, drafting, or unique powers brought into the game. |

### P1 — Multiplayer Reliability

| # | Gap | Detail |
|---|-----|--------|
| 4 | **No WebSocket** | Polling-based updates create latency. Real-time would dramatically improve UX. |
| 5 | **No reconnection** | Player identity is localStorage UUID. Browser refresh = lost session. |
| 6 | **Board preset selector missing** | Backend supports CLASSIC/UGC_24 but frontend settings don't expose it. |

### P2 — GA Polish

| # | Gap | Detail |
|---|-----|--------|
| 7 | **No rematch flow** | Must create new game after finish. |
| 8 | **No sound effects** | Purely visual experience. |
| 9 | **No spectator mode** | Can't watch without joining. |
| 10 | **No tutorial** | Rules modal exists but no interactive onboarding. |

### P3 — Engagement

| # | Gap | Detail |
|---|-----|--------|
| 11 | **No player accounts** | Anonymous, no history or stats. |
| 12 | **No leaderboards** | Games are ephemeral. |
| 13 | **Limited buff variety** | Only 3 Black Market buffs. |

---

## Code Quality Notes

- `EconomyManager.check_end_conditions()` always returns `False` (dead code — actual logic is in `ActionDispatcher`)
- Heavy `getattr()` usage in models suggests incremental field additions without migration
- `determine_winner` filters by `cash >= 0` instead of `is_bankrupt`
- `income_tax_rate` setting exists in `GameSettings` but isn't applied in tax landing logic
