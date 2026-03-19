# SastaDice Sprint 1: Wire Up Disconnected Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up existing but disconnected frontend components (TileSubmissionForm, KeyStatus), expose hidden backend settings, add missing tile type visuals, fix session restoration edge cases, and enhance spectator mode.

**Architecture:** All changes are frontend-only (no backend modifications needed). The backend already supports board presets, income tax rates, starting cash multipliers, and all tile types — the frontend simply doesn't expose them. We integrate existing unused components, extend color/icon maps, and harden the session restoration and spectator flows.

**Tech Stack:** React 18, Vite, Tailwind CSS, Zustand, Vitest + React Testing Library, bun (package manager)

**Test runner:** `cd frontends/sastadice && bun run test -- --run`

**Lint/CI:** `make ci-fast` (from repo root)

---

## File Structure

### Files to Delete
- `frontends/sastadice/src/components/game/IsometricContainer.jsx` — Unused 3D transform container, no integration path
- `frontends/sastadice/src/components/lobby/PlayerList.jsx` — Replaced by inline cards in LobbyView; KeyStatus will replace those too
- `frontends/sastadice/tests/components/PlayerList.test.jsx` — Tests for deleted component

### Files to Modify
- `frontends/sastadice/src/components/lobby/LobbyView.jsx` — Import KeyStatus, replace inline player cards, add TileSubmissionForm
- `frontends/sastadice/src/components/lobby/LobbyView.test.jsx` — Update tests for KeyStatus integration and TileSubmissionForm
- `frontends/sastadice/src/components/lobby/GameSettingsPanel.jsx` — Add board_preset, starting_cash_multiplier, income_tax_rate controls
- `frontends/sastadice/src/components/game/TileComponent.jsx` — Add NODE, GO_TO_JAIL, TELEPORT, MARKET to TILE_TYPE_COLORS
- `frontends/sastadice/src/components/game/TileCard.jsx` — Add icons and display logic for NODE, GO_TO_JAIL, TELEPORT, MARKET
- `frontends/sastadice/src/components/RulesModal.jsx` — Update special tiles section with all tile types
- `frontends/sastadice/src/App.jsx` — Add AbortController to restoration fetch, handle FINISHED status redirect
- `frontends/sastadice/src/pages/GamePage.jsx` — Add SPECTATING banner, hide action buttons for spectators
- `frontends/sastadice/src/components/game/CenterActionButton.jsx` — Already has spectator guard (no changes needed)
- `frontends/sastadice/src/components/game/PlayerPanel.jsx` — Hide trade buttons for spectators
- `frontends/sastadice/src/components/game/AuctionModal.jsx` — Disable bid buttons for spectators

### Files to Create
- `frontends/sastadice/tests/components/GameSettingsPanel.test.jsx` — Tests for new settings controls
- `frontends/sastadice/tests/pages/App.test.jsx` — Tests for session restoration edge cases

---

## Task 1: Delete Dead Code

**Files:**
- Delete: `frontends/sastadice/src/components/game/IsometricContainer.jsx`
- Delete: `frontends/sastadice/src/components/lobby/PlayerList.jsx`
- Delete: `frontends/sastadice/tests/components/PlayerList.test.jsx`

- [ ] **Step 1: Verify no imports reference these files**

Run: `cd frontends/sastadice && grep -r "IsometricContainer" src/ && grep -r "PlayerList" src/`
Expected: No matches (neither component is imported anywhere)

- [ ] **Step 2: Delete the files**

```bash
rm frontends/sastadice/src/components/game/IsometricContainer.jsx
rm frontends/sastadice/src/components/lobby/PlayerList.jsx
rm frontends/sastadice/tests/components/PlayerList.test.jsx
```

- [ ] **Step 3: Run tests to confirm nothing breaks**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(sastadice): delete unused IsometricContainer and PlayerList components"
```

---

## Task 2: Add Missing Tile Type Colors to TileComponent

**Files:**
- Modify: `frontends/sastadice/src/components/game/TileComponent.jsx:1-9`
- Test: `frontends/sastadice/tests/components/TileComponent.test.jsx`

- [ ] **Step 1: Write the failing test**

Add to `frontends/sastadice/tests/components/TileComponent.test.jsx`:

```javascript
import { TILE_TYPE_COLORS } from '../../src/components/game/TileComponent'

describe('TILE_TYPE_COLORS', () => {
  it('includes all backend tile types', () => {
    const requiredTypes = [
      'PROPERTY', 'TAX', 'CHANCE', 'TRAP', 'BUFF', 'NEUTRAL', 'GO',
      'NODE', 'GO_TO_JAIL', 'TELEPORT', 'MARKET', 'JAIL',
    ]
    for (const type of requiredTypes) {
      expect(TILE_TYPE_COLORS[type]).toBeDefined()
    }
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontends/sastadice && bun run test -- --run -t "includes all backend tile types"`
Expected: FAIL — NODE, GO_TO_JAIL, TELEPORT, MARKET, JAIL are undefined

- [ ] **Step 3: Add missing tile type colors**

In `frontends/sastadice/src/components/game/TileComponent.jsx`, replace the TILE_TYPE_COLORS object (lines 1-9):

```javascript
const TILE_TYPE_COLORS = {
  PROPERTY: '#00ff00',
  TAX: '#ff0000',
  CHANCE: '#ffff00',
  TRAP: '#ff00ff',
  BUFF: '#00ffff',
  NEUTRAL: '#666666',
  GO: '#00ff00',
  NODE: '#ff6600',
  GO_TO_JAIL: '#ff0000',
  TELEPORT: '#9900ff',
  MARKET: '#ff00ff',
  JAIL: '#888888',
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontends/sastadice && bun run test -- --run -t "includes all backend tile types"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontends/sastadice/src/components/game/TileComponent.jsx frontends/sastadice/tests/components/TileComponent.test.jsx
git commit -m "feat(sastadice): add missing tile type colors for NODE, GO_TO_JAIL, TELEPORT, MARKET, JAIL"
```

---

## Task 3: Add Missing Tile Type Icons to TileCard

**Files:**
- Modify: `frontends/sastadice/src/components/game/TileCard.jsx:3-11`
- Test: `frontends/sastadice/tests/components/TileCard.test.jsx`

- [ ] **Step 1: Write the failing test**

Create `frontends/sastadice/tests/components/TileCard.test.jsx`:

```javascript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TileCard from '../../src/components/game/TileCard'

describe('TileCard', () => {
  it('renders NODE tile with server icon', () => {
    const tile = { id: '1', type: 'NODE', name: 'Server Node', position: 5, price: 200, rent: 50 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🖥️')).toBeDefined()
  })

  it('renders MARKET tile with shop icon', () => {
    const tile = { id: '2', type: 'MARKET', name: 'Black Market', position: 18 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🏪')).toBeDefined()
  })

  it('renders TELEPORT tile with portal icon', () => {
    const tile = { id: '3', type: 'TELEPORT', name: 'The Glitch', position: 6 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🌀')).toBeDefined()
  })

  it('renders GO_TO_JAIL tile with siren icon', () => {
    const tile = { id: '4', type: 'GO_TO_JAIL', name: '404: Access Denied', position: 24 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🚨')).toBeDefined()
  })

  it('renders JAIL tile with lock icon', () => {
    const tile = { id: '5', type: 'JAIL', name: 'Server Downtime', position: 12 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🔒')).toBeDefined()
  })

  it('returns null when not visible', () => {
    const tile = { id: '1', type: 'PROPERTY', name: 'Test', position: 1 }
    const { container } = render(<TileCard tile={tile} isVisible={false} />)
    expect(container.innerHTML).toBe('')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontends/sastadice && bun run test -- --run TileCard.test`
Expected: FAIL — missing icons for NODE, MARKET, TELEPORT, GO_TO_JAIL, JAIL

- [ ] **Step 3: Add missing icons and display logic**

In `frontends/sastadice/src/components/game/TileCard.jsx`, replace TILE_TYPE_ICONS (lines 3-11):

```javascript
const TILE_TYPE_ICONS = {
    PROPERTY: '🏠',
    TAX: '💸',
    CHANCE: '🎰',
    TRAP: '⚡',
    BUFF: '✨',
    NEUTRAL: '⬜',
    GO: '🚀',
    NODE: '🖥️',
    GO_TO_JAIL: '🚨',
    TELEPORT: '🌀',
    MARKET: '🏪',
    JAIL: '🔒',
}
```

Then add display cases for the new tile types. After the existing GO tile rendering block (around line 81), add:

```javascript
{tile.type === 'NODE' && (
    <div className="text-[10px] font-zero opacity-80">SERVER NODE</div>
)}
{tile.type === 'TELEPORT' && (
    <div className="text-[10px] font-zero opacity-80">RANDOM TELEPORT</div>
)}
{tile.type === 'MARKET' && (
    <div className="text-[10px] font-zero opacity-80">BUY BUFFS</div>
)}
{tile.type === 'GO_TO_JAIL' && (
    <div className="text-[10px] font-zero opacity-80">GO TO JAIL</div>
)}
{tile.type === 'JAIL' && (
    <div className="text-[10px] font-zero opacity-80">JUST VISITING</div>
)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontends/sastadice && bun run test -- --run TileCard.test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontends/sastadice/src/components/game/TileCard.jsx frontends/sastadice/tests/components/TileCard.test.jsx
git commit -m "feat(sastadice): add icons and labels for NODE, TELEPORT, MARKET, GO_TO_JAIL, JAIL tiles"
```

---

## Task 4: Update RulesModal Special Tiles Section

**Files:**
- Modify: `frontends/sastadice/src/components/RulesModal.jsx:68-88`

- [ ] **Step 1: Update the special-tiles section content**

In `frontends/sastadice/src/components/RulesModal.jsx`, replace the `special-tiles` section content (the `content` string in the SECTIONS array, around lines 68-88) to include all tile types:

```javascript
{
    id: 'special-tiles',
    title: '🗺️ SPECIAL TILES',
    content: `GO (START) — Collect salary every time you pass.
Salary = Base ($200) + ($20 × Round Number)
Capped at 3× base to prevent runaway inflation.

THE GLITCH (25%) — Teleports you to a random unowned property or chance tile. Chaos is a feature.

SERVER DOWNTIME (50%) — This is jail.
• Land here = just visiting (safe)
• Sent here by 404 or event = locked up
• Escape: Pay $50 bribe OR roll doubles (max attempts from settings)

BLACK MARKET (75%) — Buy one-use power-ups:
• VPN ($200) — Blocks next rent payment against you
• DDoS ($150) — Disable any tile for 1 round
• Insider Info ($100) — Peek at next 3 event cards

SERVER NODES — Railroad equivalents.
Rent scales exponentially: $50 × 2^(nodes_owned - 1)
Own all 4 = $400 rent per landing.

404: ACCESS DENIED — Go directly to Server Downtime (jail). Do not pass GO. Do not collect salary.

TAX TILES — Pay the posted tax amount or half your GO bonus, whichever applies.

SASTA EVENTS (CHANCE) — Draw from the event deck. 35 possible events ranging from cash windfalls to hostile takeovers.`
},
```

- [ ] **Step 2: Run tests to make sure nothing breaks**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add frontends/sastadice/src/components/RulesModal.jsx
git commit -m "docs(sastadice): update rules modal with all special tile types"
```

---

## Task 5: Fix Session Restoration Edge Cases in App.jsx

**Files:**
- Modify: `frontends/sastadice/src/App.jsx:66-95`
- Modify: `frontends/sastadice/src/store/useGameStore.js` — Add `lastRestoredAt` timestamp
- Test: `frontends/sastadice/tests/pages/App.test.jsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontends/sastadice/tests/pages/App.test.jsx`:

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// Mock the store
const mockStore = {
  gameId: 'test-game',
  playerId: 'player-1',
  game: null,
  version: 0,
  isLoading: false,
  error: null,
  setGame: vi.fn(),
  setPlayerId: vi.fn(),
  setGameId: vi.fn(),
  reset: vi.fn(),
  isMyTurn: vi.fn(() => false),
  myPlayer: vi.fn(() => null),
  currentTurnPlayer: vi.fn(() => null),
  turnPhase: vi.fn(() => 'PRE_ROLL'),
  getTileById: vi.fn(),
  getPlayerById: vi.fn(),
}

vi.mock('../../src/store/useGameStore', () => ({
  useGameStore: (selector) => selector(mockStore),
}))

vi.mock('../../src/api/apiClient', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

import { apiClient } from '../../src/api/apiClient'
import App from '../../src/App'

describe('GameRoute session restoration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStore.game = null
    mockStore.gameId = 'test-game'
    mockStore.playerId = 'player-1'
  })

  it('redirects to home when restored game is FINISHED and player not found', async () => {
    apiClient.get.mockResolvedValue({
      data: {
        game: {
          id: 'test-game',
          status: 'FINISHED',
          players: [{ id: 'other-player', name: 'Other' }],
          board: [],
        },
        version: 1,
      },
    })

    render(
      <MemoryRouter initialEntries={['/game/test-game']}>
        <App />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(mockStore.setPlayerId).toHaveBeenCalledWith(null)
    })
  })

  it('cancels fetch on unmount via AbortController', async () => {
    let rejectFn
    apiClient.get.mockImplementation(() => new Promise((_, reject) => { rejectFn = reject }))

    const { unmount } = render(
      <MemoryRouter initialEntries={['/game/test-game']}>
        <App />
      </MemoryRouter>
    )

    unmount()

    // The abort should prevent state updates after unmount
    // This test verifies no errors are thrown on unmount
    expect(mockStore.setGame).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontends/sastadice && bun run test -- --run App.test`
Expected: FAIL — AbortController not implemented yet

- [ ] **Step 3: Add `lastRestoredAt` debounce to useGameStore**

In `frontends/sastadice/src/store/useGameStore.js`, add a `lastRestoredAt` field to the store state (non-persisted) and a `setLastRestoredAt` action:

```javascript
// Add to store state OUTSIDE the persist wrapper (alongside `game`, `version`, etc.)
// so it resets on page refresh. Place it in the non-persisted portion of the store:
lastRestoredAt: 0,

// Add action (also outside persist):
setLastRestoredAt: (ts) => set({ lastRestoredAt: ts }),
```

- [ ] **Step 4: Add AbortController, debounce, and FINISHED status handling to App.jsx**

In `frontends/sastadice/src/App.jsx`, modify the GameRoute component's restoration effect (around lines 66-95). Replace the restoration useEffect with:

```javascript
const lastRestoredAt = useGameStore((s) => s.lastRestoredAt)
const setLastRestoredAt = useGameStore((s) => s.setLastRestoredAt)

useEffect(() => {
    const controller = new AbortController()

    // Debounce: skip if restored less than 2s ago (prevents React strict mode double-mount)
    const now = Date.now()
    if (now - lastRestoredAt < 2000) return

    if (gameId && !game && !isRestoring) {
        setIsRestoring(true)
        setLastRestoredAt(now)
        apiClient
            .get(`/sastadice/games/${gameId}/state`, {
                signal: controller.signal,
            })
            .then((res) => {
                if (controller.signal.aborted) return
                const restored = res.data
                setGame(restored.game, restored.version)

                // Clear playerId if player no longer in game
                if (playerId && !restored.game.players.find((p) => p.id === playerId)) {
                    setPlayerId(null)
                }

                // Redirect to home if game is finished and we're not a participant
                if (restored.game.status === 'FINISHED' && !restored.game.players.find((p) => p.id === playerId)) {
                    reset()
                }
            })
            .catch((err) => {
                if (controller.signal.aborted) return
                if (err?.response?.status === 404) {
                    reset()
                } else {
                    setError('Failed to restore game session')
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setIsRestoring(false)
                }
            })
    }

    return () => controller.abort()
}, [gameId, game])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontends/sastadice && bun run test -- --run App.test`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add frontends/sastadice/src/App.jsx frontends/sastadice/src/store/useGameStore.js frontends/sastadice/tests/pages/App.test.jsx
git commit -m "fix(sastadice): add AbortController, debounce, and FINISHED redirect to session restoration"
```

---

## Task 6: Enhance Spectator Mode

**Files:**
- Modify: `frontends/sastadice/src/pages/GamePage.jsx:290`
- Modify: `frontends/sastadice/src/components/game/PlayerPanel.jsx:56-63`
- Modify: `frontends/sastadice/src/components/game/AuctionModal.jsx`

- [ ] **Step 1: Write failing tests for spectator mode**

Add to `frontends/sastadice/tests/components/PlayerPanel.test.jsx`:

```javascript
describe('PlayerPanel spectator mode', () => {
  it('hides trade buttons when onTradeClick is null', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000' },
      { id: 'p2', name: 'Bob', cash: 500, properties: [], color: '#00ff00' },
    ]
    render(
      <PlayerPanel
        players={players}
        currentTurnPlayerId="p1"
        currentPlayerId="p1"
        tiles={[]}
        onTradeClick={null}
        turnPhase="PRE_ROLL"
      />
    )
    expect(screen.queryByText('TRADE')).toBeNull()
  })
})
```

Also create `frontends/sastadice/tests/components/AuctionModal.test.jsx` for spectator bid hiding:

```javascript
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import AuctionModal from '../../src/components/game/AuctionModal'

vi.mock('../../src/api/apiClient', () => ({
  apiClient: { post: vi.fn() },
}))

describe('AuctionModal spectator mode', () => {
  const baseProps = {
    game: {
      id: 'g1',
      auction_state: {
        property_id: 't1',
        highest_bid: 100,
        highest_bidder_id: 'p1',
        end_time: Date.now() / 1000 + 30,
        start_time: Date.now() / 1000,
        participants: ['p1', 'p2'],
        status: 'ACTIVE',
      },
      turn_phase: 'AUCTION',
      players: [
        { id: 'p1', name: 'Alice', cash: 1000, color: '#ff0000' },
        { id: 'p2', name: 'Bob', cash: 500, color: '#00ff00' },
      ],
      board: [{ id: 't1', name: 'Test Tile', type: 'PROPERTY', price: 200, rent: 50 }],
    },
    onClose: vi.fn(),
    onActionComplete: vi.fn(),
  }

  it('shows SPECTATOR VIEW instead of bid buttons when playerId is null', () => {
    render(<AuctionModal {...baseProps} playerId={null} />)
    expect(screen.getByText('SPECTATOR VIEW')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontends/sastadice && bun run test -- --run -t "spectator"`
Expected: FAIL — PlayerPanel trade test may already pass (existing conditional), AuctionModal spectator not implemented

- [ ] **Step 3: Add SPECTATING banner to GamePage**

In `frontends/sastadice/src/pages/GamePage.jsx`, replace the small spectator badge (around line 290) with a prominent banner. Find the existing spectator check:

```javascript
{!playerId && <span className="text-[10px] font-data text-blue-600">👁️ SPECTATOR</span>}
```

Replace with:

```javascript
{!playerId && (
    <div className="w-full bg-blue-900/80 border-2 border-blue-400 text-blue-200 text-center py-2 px-4 font-zero text-sm tracking-wider">
        SPECTATING
    </div>
)}
```

- [ ] **Step 4: Hide trade buttons for spectators in GamePage**

In `frontends/sastadice/src/pages/GamePage.jsx`, find where PlayerPanel is rendered and ensure `onTradeClick` is null when spectating. Find the PlayerPanel usage and wrap the trade callback:

```javascript
onTradeClick={playerId ? (player) => setTradeTarget(player) : null}
```

- [ ] **Step 5: Disable bid buttons for spectators in AuctionModal**

First, verify that `GamePage.jsx` passes `playerId` to `AuctionModal`. If it doesn't, add it:
```javascript
<AuctionModal {...otherProps} playerId={playerId} />
```

In `frontends/sastadice/src/components/game/AuctionModal.jsx`, add `playerId` to the destructured props if not already present. Then find the bid buttons and wrap with:

```javascript
{playerId && (
    // existing bid buttons
)}
{!playerId && (
    <div className="text-center text-sm font-zero text-gray-500 py-2">SPECTATOR VIEW</div>
)}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add frontends/sastadice/src/pages/GamePage.jsx frontends/sastadice/src/components/game/PlayerPanel.jsx frontends/sastadice/src/components/game/AuctionModal.jsx frontends/sastadice/tests/
git commit -m "feat(sastadice): enhance spectator mode with banner, hidden trade/bid buttons"
```

---

## Task 7: Expose Board Preset Setting in GameSettingsPanel

**Files:**
- Modify: `frontends/sastadice/src/components/lobby/GameSettingsPanel.jsx`
- Test: `frontends/sastadice/tests/components/GameSettingsPanel.test.jsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontends/sastadice/tests/components/GameSettingsPanel.test.jsx`:

```javascript
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import GameSettingsPanel from '../../src/components/lobby/GameSettingsPanel'

describe('GameSettingsPanel', () => {
  const defaultSettings = {
    win_condition: 'SUDDEN_DEATH',
    round_limit: 30,
    chaos_level: 'NORMAL',
    doubles_give_extra_turn: true,
    enable_stimulus: true,
    enable_black_market: true,
    enable_auctions: true,
    target_cash: 5000,
    board_preset: 'CLASSIC',
    starting_cash_multiplier: 1.0,
    income_tax_rate: 0.1,
  }

  it('renders board preset selector for host', () => {
    const onUpdate = vi.fn()
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={onUpdate}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    expect(screen.getByText('CLASSIC')).toBeDefined()
    expect(screen.getByText('UGC 24')).toBeDefined()
  })

  it('updates board_preset when UGC 24 is clicked', () => {
    const onUpdate = vi.fn()
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={onUpdate}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    fireEvent.click(screen.getByText('UGC 24'))
    expect(onUpdate).toHaveBeenCalledWith('board_preset', 'UGC_24')
  })

  it('renders starting cash multiplier options', () => {
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={vi.fn()}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    expect(screen.getByText('0.5x')).toBeDefined()
    expect(screen.getByText('1x')).toBeDefined()
    expect(screen.getByText('2x')).toBeDefined()
  })

  it('renders income tax rate options', () => {
    render(
      <GameSettingsPanel
        settings={defaultSettings}
        onUpdate={vi.fn()}
        onSave={vi.fn()}
        hasChanges={false}
        isHost={true}
        alwaysExpanded={true}
      />
    )
    expect(screen.getByText('5%')).toBeDefined()
    expect(screen.getByText('10%')).toBeDefined()
    expect(screen.getByText('15%')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontends/sastadice && bun run test -- --run GameSettingsPanel.test`
Expected: FAIL — board_preset, starting_cash_multiplier, income_tax_rate controls don't exist

- [ ] **Step 3: Add constants for new settings**

In `frontends/sastadice/src/components/lobby/GameSettingsPanel.jsx`, add after the existing constants (around line 20):

```javascript
const BOARD_PRESETS = [
  { value: 'CLASSIC', label: 'CLASSIC' },
  { value: 'UGC_24', label: 'UGC 24' },
]

const CASH_MULTIPLIERS = [
  { value: 0.5, label: '0.5x' },
  { value: 1.0, label: '1x' },
  { value: 2.0, label: '2x' },
]

const TAX_RATES = [
  { value: 0.05, label: '5%' },
  { value: 0.10, label: '10%' },
  { value: 0.15, label: '15%' },
]
```

- [ ] **Step 4: Add UI controls for new settings**

In the host editing section of GameSettingsPanel (after the features toggles, around line 153), add a new "BOARD" section:

```jsx
{/* BOARD section */}
<div className="mt-4 pt-4 border-t-2 border-black">
    <div className="text-xs font-zero mb-2 opacity-60">BOARD</div>
    <div className="flex gap-1 flex-wrap">
        {BOARD_PRESETS.map((preset) => (
            <button
                key={preset.value}
                onClick={() => onUpdate('board_preset', preset.value)}
                className={`px-3 py-1 text-xs font-zero border-2 border-black transition-all ${
                    settings.board_preset === preset.value
                        ? 'bg-black text-white shadow-brutal-sm'
                        : 'bg-white hover:bg-gray-100'
                }`}
            >
                {preset.label}
            </button>
        ))}
    </div>
</div>

{/* ECONOMY section */}
<div className="mt-4 pt-4 border-t-2 border-black">
    <div className="text-xs font-zero mb-2 opacity-60">ECONOMY</div>

    <div className="mb-2">
        <div className="text-[10px] font-zero opacity-50 mb-1">STARTING CASH</div>
        <div className="flex gap-1">
            {CASH_MULTIPLIERS.map((mult) => (
                <button
                    key={mult.value}
                    onClick={() => onUpdate('starting_cash_multiplier', mult.value)}
                    className={`px-3 py-1 text-xs font-zero border-2 border-black transition-all ${
                        settings.starting_cash_multiplier === mult.value
                            ? 'bg-black text-white shadow-brutal-sm'
                            : 'bg-white hover:bg-gray-100'
                    }`}
                >
                    {mult.label}
                </button>
            ))}
        </div>
    </div>

    <div>
        <div className="text-[10px] font-zero opacity-50 mb-1">TAX RATE</div>
        <div className="flex gap-1">
            {TAX_RATES.map((rate) => (
                <button
                    key={rate.value}
                    onClick={() => onUpdate('income_tax_rate', rate.value)}
                    className={`px-3 py-1 text-xs font-zero border-2 border-black transition-all ${
                        settings.income_tax_rate === rate.value
                            ? 'bg-black text-white shadow-brutal-sm'
                            : 'bg-white hover:bg-gray-100'
                    }`}
                >
                    {rate.label}
                </button>
            ))}
        </div>
    </div>
</div>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontends/sastadice && bun run test -- --run GameSettingsPanel.test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontends/sastadice/src/components/lobby/GameSettingsPanel.jsx frontends/sastadice/tests/components/GameSettingsPanel.test.jsx
git commit -m "feat(sastadice): expose board preset, starting cash multiplier, and tax rate settings"
```

---

## Task 8: Wire Up TileSubmissionForm in LobbyView

**Files:**
- Modify: `frontends/sastadice/src/components/lobby/LobbyView.jsx`
- Modify: `frontends/sastadice/tests/components/LobbyView.test.jsx`

- [ ] **Step 1: Write the failing test**

Add to `frontends/sastadice/tests/components/LobbyView.test.jsx`:

```javascript
describe('TileSubmissionForm integration', () => {
  it('shows tile submission form when board preset is UGC_24 and player has joined', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        game: {
          id: 'game-123',
          status: 'LOBBY',
          players: [{ id: 'player-123', name: 'Test Player', ready: false, color: '#00ff00' }],
          settings: { board_preset: 'UGC_24' },
        },
        playerId: 'player-123',
        setPlayerId: vi.fn(),
        setGame: vi.fn(),
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText(/TILES/i)).toBeInTheDocument()
  })

  it('hides tile submission form when board preset is CLASSIC', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        game: {
          id: 'game-123',
          status: 'LOBBY',
          players: [{ id: 'player-123', name: 'Test Player', ready: false, color: '#00ff00' }],
          settings: { board_preset: 'CLASSIC' },
        },
        playerId: 'player-123',
        setPlayerId: vi.fn(),
        setGame: vi.fn(),
      }
      return selector(state)
    })

    render(<LobbyView />)
    // TileSubmissionForm should NOT render — look for its unique text
    expect(screen.queryByText(/SUBMIT.*TILES/i)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontends/sastadice && bun run test -- --run -t "TileSubmissionForm integration"`
Expected: FAIL — TileSubmissionForm is not rendered in LobbyView

- [ ] **Step 3: Import TileSubmissionForm and add to LobbyView**

In `frontends/sastadice/src/components/lobby/LobbyView.jsx`:

Add import (after existing imports):
```javascript
import TileSubmissionForm from './TileSubmissionForm'
```

Add state for tiles (after existing state declarations):
```javascript
const [tiles, setTiles] = useState([
    { type: 'PROPERTY', name: '', effect_config: {} },
    { type: 'PROPERTY', name: '', effect_config: {} },
    { type: 'CHANCE', name: '', effect_config: {} },
    { type: 'TAX', name: '', effect_config: {} },
    { type: 'BUFF', name: '', effect_config: {} },
])
```

Compute whether to show the form:
```javascript
const showTileForm = hasJoined && game?.settings?.board_preset === 'UGC_24'
```

In the right column (after GameSettingsPanel, before the closing `</div>` of the right column around line 313), add:

```jsx
{showTileForm && (
    <div className="mt-4">
        <TileSubmissionForm tiles={tiles} setTiles={setTiles} />
    </div>
)}
```

- [ ] **Step 4: Pass submitted_tiles in join request**

In the `handleJoin` function in LobbyView.jsx, modify the join API call to include tiles when board preset is UGC_24. Find the join POST request and update:

```javascript
const joinPayload = { name: playerName.trim() }
if (game?.settings?.board_preset === 'UGC_24') {
    joinPayload.tiles = tiles.filter(t => t.name.trim() !== '')
}
await apiClient.post(`/sastadice/games/${gameId}/join`, joinPayload)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontends/sastadice && bun run test -- --run LobbyView.test`
Expected: All tests pass (existing + new)

- [ ] **Step 6: Commit**

```bash
git add frontends/sastadice/src/components/lobby/LobbyView.jsx frontends/sastadice/tests/components/LobbyView.test.jsx
git commit -m "feat(sastadice): wire up TileSubmissionForm in lobby for UGC_24 board preset"
```

---

## Task 9: Integrate KeyStatus into LobbyView

**Files:**
- Modify: `frontends/sastadice/src/components/lobby/LobbyView.jsx:219-290`
- Modify: `frontends/sastadice/tests/components/LobbyView.test.jsx`

- [ ] **Step 1: Write the failing test**

Add to `frontends/sastadice/tests/components/LobbyView.test.jsx`:

```javascript
describe('KeyStatus integration', () => {
  it('renders KeyStatus component for each player in lobby', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        game: {
          id: 'game-123',
          status: 'LOBBY',
          host_id: 'player-123',
          players: [
            { id: 'player-123', name: 'Alice', ready: true, color: '#ff0000' },
            { id: 'player-456', name: 'Bob', ready: false, color: '#00ff00' },
          ],
          settings: {},
        },
        playerId: 'player-123',
        setPlayerId: vi.fn(),
        setGame: vi.fn(),
      }
      return selector(state)
    })

    render(<LobbyView />)
    // KeyStatus mock renders "KeyStatus: <name>" (see mock at top of file)
    expect(screen.getByText(/KeyStatus: Alice/)).toBeInTheDocument()
    expect(screen.getByText(/KeyStatus: Bob/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Import KeyStatus and replace inline player cards**

In `frontends/sastadice/src/components/lobby/LobbyView.jsx`:

Add import:
```javascript
import KeyStatus from './KeyStatus'
```

Replace the center column's inline player cards (the `myPlayer` card at lines 231-252 and the `otherPlayers.map` at lines 254-282) with KeyStatus components:

```jsx
{/* Center column - Squad */}
<div className="lg:col-span-6 space-y-2">
    <h3 className="text-sm font-zero opacity-60">// SQUAD</h3>
    {myPlayer && (
        <KeyStatus
            player={myPlayer}
            isMe={true}
            isHost={isHost}
            canKick={false}
            onKick={() => {}}
        />
    )}
    {otherPlayers.map((player) => (
        <KeyStatus
            key={player.id}
            player={player}
            isMe={false}
            isHost={player.id === game?.host_id}
            canKick={isHost}
            onKick={(playerId) => handleKick(playerId)}
        />
    ))}
    {(!game?.players || game.players.length === 0) && (
        <div className="text-center py-8 opacity-40 font-zero text-sm">
            WAITING FOR PLAYERS...
        </div>
    )}
</div>
```

- [ ] **Step 3: Run tests to verify everything passes**

Run: `cd frontends/sastadice && bun run test -- --run LobbyView.test`
Expected: All tests pass

- [ ] **Step 4: Run full test suite**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add frontends/sastadice/src/components/lobby/LobbyView.jsx frontends/sastadice/tests/components/LobbyView.test.jsx
git commit -m "refactor(sastadice): replace inline player cards with KeyStatus component in lobby"
```

---

## Task 10: Final Validation

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontends/sastadice && bun run test -- --run`
Expected: All tests pass

- [ ] **Step 2: Run full CI pipeline**

Run: `make ci-fast`
Expected: All quality gates pass (lint, typecheck, complexity, coverage, all tests)

- [ ] **Step 3: Manual smoke test (optional)**

```bash
cd frontends/sastadice && bun run dev
```

Verify:
- Lobby shows KeyStatus cards instead of inline cards
- GameSettingsPanel shows BOARD and ECONOMY sections
- Selecting UGC_24 preset shows TileSubmissionForm
- New tile types show correct colors on board
- Spectator mode shows banner and hides trade/bid buttons

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(sastadice): address smoke test findings"
```

---

## Future Sprints (Separate Plans)

This plan covers **Sprint 1** only. The remaining sprints from `DESIGN_PLAN.md` will get their own plans:

- **Sprint 2:** Game Mechanics Expansion (buff inventory, AFK indicators, economy indicators, event deck transparency, bankruptcy auction UI)
- **Sprint 3:** Mobile & Polish (responsive layout, keyboard shortcuts, animations)
- **Sprint 4:** Real-Time WebSocket Migration (backend WS endpoint, frontend hook, page migration, Traefik config)

Each sprint should be planned and executed independently after the previous sprint is merged.
