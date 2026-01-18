# Phase 3: Advanced Features - Testing Guide

## Implementation Summary

All Phase 3 features have been implemented and are ready for testing:

### ✅ Backend Features
1. **DDOS Buff Fix**: Fixed missing player lookup in BLOCK_TILE action
2. **Blocked Tiles Persistence**: Added `blocked_until_round` to TileDocument model
3. **Blocked Tiles Clearing**: Automatically clears when round advances
4. **Turn Timer**: Full implementation with timeout checking and auto-action

### ✅ Frontend Features
1. **DDOS Tile Selection**: UI for selecting tiles to block
2. **PEEK Events Modal**: Displays next 3 events when PEEK buff is used
3. **Turn Timer UI**: Visual countdown with progress bar
4. **Rules Modal**: Comprehensive rules display with navigation

## Testing Instructions

### Backend Testing (Simulation Script)

The simulation script has been enhanced to track Phase 3 features:

```bash
# Run from backend container or with proper Python environment
cd backend
python3 scripts/simulate_games.py
```

**What it tests:**
- DDOS buff purchases and usage
- PEEK buff purchases
- Turn timeout handling
- Blocked tiles clearing on round advance
- All existing game mechanics

**Expected output includes:**
- Phase 3 feature statistics:
  - DDOS buffs bought
  - Tiles blocked (DDOS)
  - PEEK buffs bought
  - Turn timeouts
  - Blocked tiles cleared

### Frontend E2E Testing

The e2e test has been enhanced to test UI features:

```bash
# Run Playwright tests
cd frontends/sastadice
npm run test:e2e
# or
npx playwright test tests/e2e/game_flow.spec.js
```

**What it tests:**
1. **Rules Modal**
   - Opens from lobby and game page
   - Displays all sections
   - Navigation works
   - Closes properly

2. **Turn Timer**
   - Visible when it's player's turn
   - Shows countdown
   - Updates in real-time

3. **DDOS Buff Usage**
   - Button appears when player has DDOS buff
   - Activates DDOS mode
   - Tiles become selectable

4. **PEEK Events Modal**
   - Appears when PEEK buff is used
   - Displays 3 event names
   - Can be closed

5. **Black Market Flow**
   - Can buy buffs
   - Buffs activate correctly

## Manual Testing Checklist

### Backend Features

- [ ] **DDOS Buff Purchase**
  - Land on Black Market
  - Buy DDOS buff ($150)
  - Verify `active_buff` is set to "DDOS"

- [ ] **DDOS Tile Blocking**
  - Use DDOS buff
  - Select a property tile
  - Verify `blocked_until_round` is set correctly
  - Verify tile doesn't collect rent when blocked

- [ ] **Blocked Tiles Clearing**
  - Block a tile in round 1
  - Advance to round 2
  - Verify `blocked_until_round` is cleared when `current_round` advances

- [ ] **PEEK Buff**
  - Buy PEEK buff ($100)
  - Verify message contains "Insider Info! Next Events: ..."
  - Verify 3 event names are shown

- [ ] **Turn Timer**
  - Start a game
  - Verify `turn_start_time` is set when turn starts
  - Wait 30+ seconds (or adjust timeout in settings)
  - Verify timeout triggers auto-action

### Frontend Features

- [ ] **Rules Modal**
  - Click "📖 RULES" button in lobby
  - Verify all 8 sections are accessible
  - Navigate between sections
  - Close modal
  - Open from game page header

- [ ] **Turn Timer UI**
  - Start a game
  - When it's your turn, verify timer appears
  - Verify countdown decreases
  - Verify warning color when < 10 seconds

- [ ] **DDOS Tile Selection**
  - Buy DDOS buff from Black Market
  - Click "💀 USE DDOS" button
  - Verify property tiles are highlighted
  - Click a property tile
  - Verify BLOCK_TILE action is sent
  - Verify DDOS mode exits

- [ ] **PEEK Events Modal**
  - Buy PEEK buff from Black Market
  - Verify modal appears with 3 event names
  - Verify event names are correct
  - Close modal

- [ ] **Blocked Tile Visual**
  - Block a tile using DDOS
  - Verify tile shows "BLOCKED" overlay
  - Verify overlay persists until round advances

## Running Tests in Docker

If using Docker Compose:

```bash
# Backend simulation (run in backend container)
docker exec -it sastaspace-backend python3 scripts/simulate_games.py

# Frontend e2e (run locally with services running)
cd frontends/sastadice
npm run test:e2e
```

## Expected Test Results

### Simulation Script
- ✅ All configurations complete successfully
- ✅ Phase 3 features tracked in statistics
- ✅ No errors in game flow

### E2E Tests
- ✅ Rules modal opens and closes
- ✅ Turn timer displays correctly
- ✅ DDOS buff can be activated
- ✅ PEEK modal displays events
- ✅ Full game flow works end-to-end

## Known Issues / Notes

1. **Turn Timer**: Timeout auto-action may need adjustment based on game settings
2. **DDOS Mode**: Tile selection requires clicking on property tiles specifically
3. **PEEK Events**: Events are shown in order they appear in deck (not shuffled preview)

## Next Steps

After testing:
1. Review any errors or edge cases
2. Adjust timeout behavior if needed
3. Enhance CPU player logic to use new buffs
4. Add more comprehensive e2e test scenarios
