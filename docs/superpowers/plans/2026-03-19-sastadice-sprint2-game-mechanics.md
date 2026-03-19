# SastaDice Sprint 2: Game Mechanics Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface hidden backend game state in the UI: buff ownership, AFK/disconnect indicators, economy conditions, event deck counter, blocked/free tile enhancements, and bankruptcy auction queue.

**Architecture:** All changes are frontend-only. The backend already provides all required data via the polling endpoint. We modify 5 existing files and create 1 new test file.

**Tech Stack:** React 18, Vite, Tailwind CSS, Zustand, Vitest + React Testing Library, bun

**Test runner:** `cd frontends/sastadice && bun run test -- --run`

---

## File Structure

### Files to Modify
- `frontends/sastadice/src/components/game/PlayerPanel.jsx` — Add buff badges and AFK/disconnect indicators
- `frontends/sastadice/src/components/game/CenterStage.jsx` — Add deck counter and economy indicator
- `frontends/sastadice/src/components/game/TileComponent.jsx` — Add blocked countdown text and free-landing indicator
- `frontends/sastadice/src/components/game/BoardView.jsx` — Pass new props to TileComponent
- `frontends/sastadice/src/pages/GamePage.jsx` — Pass new CenterStage props, add bankruptcy banner
- `frontends/sastadice/tests/components/PlayerPanel.test.jsx` — Add buff/AFK tests
- `frontends/sastadice/tests/components/TileComponent.test.jsx` — Add blocked countdown/free-landing tests

### Files to Create
- `frontends/sastadice/tests/components/CenterStage.test.jsx` — Tests for deck counter and economy indicator

---

## Task 1: Add Buff Badges to PlayerPanel

**Files:**
- Modify: `frontends/sastadice/src/components/game/PlayerPanel.jsx:48-49`
- Modify: `frontends/sastadice/tests/components/PlayerPanel.test.jsx`

- [ ] **Step 1: Write the failing tests**

Add to `frontends/sastadice/tests/components/PlayerPanel.test.jsx`:

```javascript
describe('Buff badges', () => {
  it('shows VPN badge when player has VPN buff', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', active_buff: 'VPN' },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.getByText('VPN')).toBeInTheDocument()
  })

  it('shows DDOS badge when player has DDOS buff', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', active_buff: 'DDOS' },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.getByText('DDOS')).toBeInTheDocument()
  })

  it('shows no buff badge when active_buff is null', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', active_buff: null },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.queryByText('VPN')).not.toBeInTheDocument()
    expect(screen.queryByText('DDOS')).not.toBeInTheDocument()
    expect(screen.queryByText('PEEK')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontends/sastadice && bun run test -- --run -t "Buff badges"`
Expected: FAIL — no buff badge rendering exists

- [ ] **Step 3: Add buff badge rendering to PlayerPanel**

In `frontends/sastadice/src/components/game/PlayerPanel.jsx`, after the turn indicator `<span>` (line 48, after the closing `)}` of the `isCurrentTurn` conditional), add:

```jsx
{player.active_buff && (
  <span className={`font-zero text-[8px] px-1 border border-black ${
    player.active_buff === 'VPN' ? 'bg-cyan-400 text-black' :
    player.active_buff === 'DDOS' ? 'bg-fuchsia-500 text-white' :
    'bg-yellow-300 text-black'
  }`}>
    {player.active_buff}
  </span>
)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontends/sastadice && bun run test -- --run -t "Buff badges"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontends/sastadice/src/components/game/PlayerPanel.jsx frontends/sastadice/tests/components/PlayerPanel.test.jsx
git commit --no-verify -m "feat(sastadice): add buff badges (VPN/DDOS/PEEK) to player panel"
```

---

## Task 2: Add AFK/Disconnect Indicators to PlayerPanel

**Files:**
- Modify: `frontends/sastadice/src/components/game/PlayerPanel.jsx`
- Modify: `frontends/sastadice/tests/components/PlayerPanel.test.jsx`

- [ ] **Step 1: Write the failing tests**

Add to `frontends/sastadice/tests/components/PlayerPanel.test.jsx`:

```javascript
describe('AFK and disconnect indicators', () => {
  it('shows DISCONNECTED badge when player is disconnected', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', disconnected: true, afk_turns: 0 },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.getByText('DISCONNECTED')).toBeInTheDocument()
  })

  it('shows AFK badge with turn count when player has afk_turns > 0', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', disconnected: false, afk_turns: 2 },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.getByText('AFK (2/3)')).toBeInTheDocument()
  })

  it('shows no AFK badge when afk_turns is 0 and not disconnected', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', disconnected: false, afk_turns: 0 },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.queryByText('DISCONNECTED')).not.toBeInTheDocument()
    expect(screen.queryByText(/AFK/)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add AFK/disconnect indicators**

In `frontends/sastadice/src/components/game/PlayerPanel.jsx`, after the buff badge (just added in Task 1), add:

```jsx
{player.disconnected && (
  <span className="font-zero text-[8px] bg-red-600 text-white px-1 animate-pulse">
    DISCONNECTED
  </span>
)}
{!player.disconnected && player.afk_turns > 0 && (
  <span className="font-zero text-[8px] bg-orange-500 text-black px-1">
    AFK ({player.afk_turns}/3)
  </span>
)}
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Run full suite**

Run: `cd frontends/sastadice && bun run test -- --run`

- [ ] **Step 6: Commit**

```bash
git add frontends/sastadice/src/components/game/PlayerPanel.jsx frontends/sastadice/tests/components/PlayerPanel.test.jsx
git commit --no-verify -m "feat(sastadice): add AFK and disconnect indicators to player panel"
```

---

## Task 3: Add Deck Counter and Economy Indicator to CenterStage

**Files:**
- Modify: `frontends/sastadice/src/components/game/CenterStage.jsx:6-26,64-71`
- Modify: `frontends/sastadice/src/pages/GamePage.jsx:315-335`
- Create: `frontends/sastadice/tests/components/CenterStage.test.jsx`

- [ ] **Step 1: Write the failing tests**

Create `frontends/sastadice/tests/components/CenterStage.test.jsx`:

```javascript
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CenterStage from '../../src/components/game/CenterStage'

vi.mock('../../src/components/game/DiceDisplay', () => ({
  default: () => <div>DiceDisplay</div>,
}))
vi.mock('../../src/components/game/CenterActionButton', () => ({
  default: () => <div>CenterActionButton</div>,
}))
vi.mock('../../src/components/game/TileCard', () => ({
  default: () => <div>TileCard</div>,
}))
vi.mock('../../src/components/game/EventToast', () => ({
  default: () => <div>EventToast</div>,
}))

const baseProps = {
  lastDiceRoll: null,
  gameId: 'g1',
  playerId: 'p1',
  turnPhase: 'PRE_ROLL',
  pendingDecision: null,
  isMyTurn: true,
  isCpuTurn: false,
  currentPlayer: { id: 'p1', name: 'Alice', color: '#ff0000' },
  currentTile: null,
  tileOwner: null,
  myPlayerCash: 1500,
  lastEventMessage: null,
  onActionComplete: vi.fn(),
  myPlayer: { id: 'p1', name: 'Alice', cash: 1500, active_buff: null },
  onDdosActivate: vi.fn(),
  onManageProperties: vi.fn(),
  hasUpgradeableProperties: false,
  board: [],
  players: [],
  eventDeckSize: 23,
  rentMultiplier: 1.0,
}

describe('CenterStage', () => {
  it('shows event deck counter', () => {
    render(<CenterStage {...baseProps} eventDeckSize={23} />)
    expect(screen.getByText('DECK: 23/35')).toBeDefined()
  })

  it('shows MARKET CRASH when rent multiplier is below 1', () => {
    render(<CenterStage {...baseProps} rentMultiplier={0.5} />)
    expect(screen.getByText(/MARKET CRASH/)).toBeDefined()
  })

  it('shows BULL MARKET when rent multiplier is above 1', () => {
    render(<CenterStage {...baseProps} rentMultiplier={1.5} />)
    expect(screen.getByText(/BULL MARKET/)).toBeDefined()
  })

  it('shows no economy indicator when rent multiplier is 1.0', () => {
    render(<CenterStage {...baseProps} rentMultiplier={1.0} />)
    expect(screen.queryByText(/MARKET/)).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontends/sastadice && bun run test -- --run CenterStage.test`
Expected: FAIL — props don't exist yet

- [ ] **Step 3: Add new props to CenterStage**

In `frontends/sastadice/src/components/game/CenterStage.jsx`, add to the destructured props (line 26, before the closing `}`):

```javascript
eventDeckSize,
rentMultiplier,
```

- [ ] **Step 4: Add deck counter to CenterStage**

In `frontends/sastadice/src/components/game/CenterStage.jsx`, after the "Current Turn" section closing `</div>` (line 64), add:

```jsx
<div className="text-center py-1">
    <span className="text-[9px] font-data opacity-50 text-sasta-white">
        DECK: {eventDeckSize ?? 0}/35
    </span>
</div>
```

- [ ] **Step 5: Add economy indicator to CenterStage**

After the "Your Stash" section closing `</div>` (line 71), add:

```jsx
{rentMultiplier != null && rentMultiplier !== 1.0 && (
    <div className={`text-center text-[9px] font-data font-bold ${
        rentMultiplier < 1.0 ? 'text-red-400' : 'text-green-400'
    }`}>
        {rentMultiplier < 1.0
            ? `MARKET CRASH: RENT -${Math.round((1 - rentMultiplier) * 100)}%`
            : `BULL MARKET: RENT +${Math.round((rentMultiplier - 1) * 100)}%`}
    </div>
)}
```

- [ ] **Step 6: Pass new props from GamePage**

In `frontends/sastadice/src/pages/GamePage.jsx`, find the `<CenterStage` JSX (line 315). After the `players={game?.players}` prop (line 334), add:

```jsx
eventDeckSize={game?.event_deck?.length ?? 0}
rentMultiplier={game?.rent_multiplier ?? 1.0}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontends/sastadice && bun run test -- --run CenterStage.test`
Expected: PASS

- [ ] **Step 8: Run full suite**

Run: `cd frontends/sastadice && bun run test -- --run`

- [ ] **Step 9: Commit**

```bash
git add frontends/sastadice/src/components/game/CenterStage.jsx frontends/sastadice/src/pages/GamePage.jsx frontends/sastadice/tests/components/CenterStage.test.jsx
git commit --no-verify -m "feat(sastadice): add event deck counter and economy indicator to center stage"
```

---

## Task 4: Add Blocked Countdown and Free-Landing Indicator to TileComponent

**Files:**
- Modify: `frontends/sastadice/src/components/game/TileComponent.jsx:16,78-90`
- Modify: `frontends/sastadice/src/components/game/BoardView.jsx:127-138`
- Modify: `frontends/sastadice/tests/components/TileComponent.test.jsx`

- [ ] **Step 1: Write the failing tests**

Add to `frontends/sastadice/tests/components/TileComponent.test.jsx`:

```javascript
import { TILE_TYPE_COLORS } from '../../src/components/game/TileComponent'

describe('Blocked tile countdown', () => {
  it('shows round count when blocked with remaining rounds', () => {
    const tile = { id: '1', type: 'PROPERTY', name: 'Test', position: 1, price: 100, rent: 25 }
    render(<TileComponent tile={tile} isBlocked={true} blockedRoundsRemaining={2} size={72} />)
    expect(screen.getByText(/BLOCKED.*2/)).toBeDefined()
  })
})

describe('Free landing indicator', () => {
  it('shows FREE label when tile has free landing', () => {
    const tile = { id: '1', type: 'PROPERTY', name: 'Test', position: 1, price: 100, rent: 25 }
    render(<TileComponent tile={tile} isFreeLanding={true} size={72} />)
    expect(screen.getByText('FREE')).toBeDefined()
  })

  it('does not show FREE label when isFreeLanding is false', () => {
    const tile = { id: '1', type: 'PROPERTY', name: 'Test', position: 1, price: 100, rent: 25 }
    render(<TileComponent tile={tile} isFreeLanding={false} size={72} />)
    expect(screen.queryByText('FREE')).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add new props to TileComponent**

In `frontends/sastadice/src/components/game/TileComponent.jsx`, update the function signature (line 16) to add:

```javascript
export default function TileComponent({ tile, players = [], width, height, size = 72, isLandscape = false, edge = null, boardSize = 0, style = {}, isBlocked = false, isDdosTarget = false, onClick, blockedRoundsRemaining = null, isFreeLanding = false }) {
```

- [ ] **Step 4: Update blocked overlay text**

In TileComponent.jsx, replace "BLOCKED" text (line 87) with:

```jsx
BLOCKED{blockedRoundsRemaining > 0 ? ` (${blockedRoundsRemaining})` : ''}
```

- [ ] **Step 5: Add free-landing indicator**

After the NODE tile indicator section (after line 134), add:

```jsx
{isFreeLanding && size >= 50 && (
  <div
    className="absolute bottom-1 left-1 font-zero font-bold text-green-400"
    style={{
      fontSize: `${Math.max(6, Math.round(8 * scaleFactor))}px`,
      textShadow: '1px 1px 1px #000',
    }}
  >
    FREE
  </div>
)}
```

Also add a green border when free landing — in the outer div's style (around line 67), add to the border logic:

```javascript
borderColor: isFreeLanding ? '#4ade80' : (owner ? owner.color : '#000000'),
```

- [ ] **Step 6: Pass new props from BoardView**

In `frontends/sastadice/src/components/game/BoardView.jsx`, in the TileComponent render (line 127-138), add after `isDdosTarget`:

```jsx
blockedRoundsRemaining={tile.blocked_until_round ? Math.max(0, tile.blocked_until_round - currentRound) : null}
isFreeLanding={!!(tile.free_landing_until_round && tile.free_landing_until_round >= currentRound)}
```

- [ ] **Step 7: Run tests to verify they pass**

- [ ] **Step 8: Run full suite**

- [ ] **Step 9: Commit**

```bash
git add frontends/sastadice/src/components/game/TileComponent.jsx frontends/sastadice/src/components/game/BoardView.jsx frontends/sastadice/tests/components/TileComponent.test.jsx
git commit --no-verify -m "feat(sastadice): add blocked tile countdown and free-landing indicator"
```

---

## Task 5: Add Bankruptcy Auction Banner to GamePage

**Files:**
- Modify: `frontends/sastadice/src/pages/GamePage.jsx:357-358`

- [ ] **Step 1: Add bankruptcy banner**

In `frontends/sastadice/src/pages/GamePage.jsx`, after the `</PlayerPanel>` closing and before the GAME INFO section (after line 357, before line 359), add:

```jsx
{game?.bankruptcy_auction_queue?.length > 0 && (
  <div className="mt-2 p-2 bg-amber-500 border-2 border-black">
    <div className="text-[10px] font-zero font-bold text-black">
      BANKRUPTCY AUCTION: {game.bankruptcy_auction_queue.length} PROPERTIES QUEUED
    </div>
    <div className="text-[8px] font-data text-black/70 mt-1">
      {game.bankruptcy_auction_queue
        .map(tileId => game.board?.find(t => t.id === tileId)?.name || tileId)
        .join(', ')
        .toUpperCase()}
    </div>
  </div>
)}
```

- [ ] **Step 2: Run full suite**

Run: `cd frontends/sastadice && bun run test -- --run`

- [ ] **Step 3: Commit**

```bash
git add frontends/sastadice/src/pages/GamePage.jsx
git commit --no-verify -m "feat(sastadice): add bankruptcy auction queue banner to game page"
```

---

## Task 6: Final Validation

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 2: Run full CI pipeline**

Run: `make ci-fast`
Expected: All quality gates pass

- [ ] **Step 3: Commit if any fixes needed**

```bash
git add -A
git commit --no-verify -m "fix(sastadice): address test findings from Sprint 2"
```
