# SastaDice Chaos Testing Framework

## Overview

The chaos testing framework transforms SastaDice testing from **Fixed Scenario Testing** to **State-Space Exploration**, finding edge cases, race conditions, economic imbalances, and soft locks that traditional tests miss.

## Architecture

```
Backend Chaos Testing
├── InvariantChecker      - Validates game state (Strict/Lenient modes)
├── InflationMonitor      - Detects economic imbalances
├── SnapshotManager       - Time-travel debugging (5-state history)
├── MonkeyStrategy        - Random CPU behavior
└── ChaosRepository       - Fault injection (DB/network)

Frontend Chaos Testing
├── monkey.spec.js        - Smart/Dumb/Hoarder random testing
├── stress.spec.js        - Concurrent race conditions & zombie players
└── helpers/              - Shared testing utilities
```

## Backend Components

### 1. InvariantChecker

Validates game state consistency after every action.

**Modes:**
- `STRICT`: Fails immediately on violations (Dev/Test)
- `LENIENT`: Logs violations + auto-corrects (Production)

**Invariants Checked:**
- Asset Conservation: Properties owned = tiles with owner
- Cash Integrity: No negative cash unless bankrupt
- Turn Order: Current player is active & non-bankrupt
- Phase Validity: Only valid phase transitions
- Position Bounds: 0 <= position < board_size

**Usage:**
```python
from app.modules.sastadice.services.invariant_checker import InvariantChecker, StrictnessMode

checker = InvariantChecker(mode=StrictnessMode.STRICT)
violations = checker.check_all(game)
if violations:
    # Handle violations...
```

### 2. InflationMonitor

Detects economic stalemates and runaway inflation.

**Metrics Tracked:**
- System Cash Velocity (delta per round)
- Asset Turnover Rate (property ownership changes)
- Wealth Concentration (richest vs poorest)

**Failure Conditions:**
- RUNAWAY_INFLATION: Cash grows 10+ consecutive rounds after R20
- ECONOMIC_STALEMATE: No property changes for 20 turns
- WEALTH_IMBALANCE: Richest > 100x poorest

**Usage:**
```python
from app.modules.sastadice.services.inflation_monitor import InflationMonitor

monitor = InflationMonitor()

# At each round end:
monitor.record_round_end(game)
violations = monitor.check_economic_health(game)

# At game end:
report = monitor.generate_report(game)
print(monitor.format_report(report))
```

### 3. SnapshotManager

Captures game state with 5-frame rolling history for time-travel debugging.

**Features:**
- Rolling buffer of last 5 game states
- Full action history
- Replay to any historical frame
- JSON snapshot format

**Usage:**
```python
from app.modules.sastadice.services.snapshot_manager import SnapshotManager

snapshot_mgr = SnapshotManager(chaos_config)

# Record states continuously
snapshot_mgr.record_state(game, action)

# Capture on error
snapshot_path = snapshot_mgr.capture(
    game, 
    reason="invariant_violation",
    error="Cash integrity violation"
)

# Replay to frame 2 (3rd state in buffer)
game_state = snapshot_mgr.replay_to_frame(snapshot_path, frame_index=2)
```

### 4. MonkeyStrategy

CPU strategy that makes intentionally suboptimal/random decisions.

**Chaos Behaviors:**
- 30%: Bid entire cash in auction
- 20%: Pass on affordable properties
- 10%: Propose invalid trades
- 15%: Buy buffs without checking cost
- 25%: Skip optimal upgrades

**Usage:**
```python
from app.modules.sastadice.services.chaos_strategy import MonkeyStrategy
from app.modules.sastadice.schemas import ChaosConfig

config = ChaosConfig(seed=12345, chaos_probability=0.3)
strategy = MonkeyStrategy(config)

if strategy.should_buy_property(player, price):
    # Buy property
```

### 5. DynamicEconomyScaler

Scales rents and costs to counter GO inflation.

**Scaling Rules:**
- Rent: +10% per round after R10
- Buffs: +5% per round after R10
- GO Bonus: Capped at 3x base value

**Usage:**
```python
from app.modules.sastadice.services.economy_manager import DynamicEconomyScaler

# Calculate dynamic rent
rent = DynamicEconomyScaler.calculate_dynamic_rent(
    base_rent=100,
    upgrade_level=1,
    current_round=50,
    settings=game.settings
)

# Calculate capped GO bonus
go_bonus = DynamicEconomyScaler.calculate_capped_go_bonus(
    base_bonus=200,
    inflation_per_round=20,
    current_round=50
)
```

## Running Backend Chaos Tests

### Basic Simulation

```bash
# Standard simulation
python backend/scripts/simulate_games.py

# With specific seed
python backend/scripts/simulate_games.py --seed 12345
```

### Chaos Mode

```bash
# Enable chaos testing
python backend/scripts/simulate_games.py --chaos-mode --seed 42

# Adjust chaos probability
python backend/scripts/simulate_games.py --chaos-mode --chaos-probability 0.5

# Lenient mode (auto-correct violations)
python backend/scripts/simulate_games.py --chaos-mode --strictness lenient
```

### Fault Injection

```bash
# Simulate 10% DB write failures
python backend/scripts/simulate_games.py --chaos-mode --drop-db-writes 0.1

# Add 50ms network latency
python backend/scripts/simulate_games.py --chaos-mode --delay-ms 50

# Combined stress test
python backend/scripts/simulate_games.py --chaos-mode --drop-db-writes 0.05 --delay-ms 100
```

### Economic Monitoring

```bash
# Enable economic health tracking
python backend/scripts/simulate_games.py --enable-economic-monitoring

# Find inflation bugs
python backend/scripts/simulate_games.py --enable-economic-monitoring --chaos-mode
```

### Replay Snapshots

```bash
# Replay a saved snapshot
python backend/scripts/simulate_games.py --replay snapshots/invariant_violation_abc123_1706012345.json
```

## Frontend Chaos Tests

### Running E2E Tests

```bash
cd frontends/sastadice
npm run test:e2e
```

### Monkey Tests

```bash
# Run all monkey tests (Smart/Dumb/Hoarder)
npx playwright test monkey.spec.js

# Run specific mode
npx playwright test monkey.spec.js -g "Smart Monkey"
npx playwright test monkey.spec.js -g "Dumb Monkey"
npx playwright test monkey.spec.js -g "Hoarder"
```

### Stress Tests

```bash
# Run all stress tests
npx playwright test stress.spec.js

# Run zombie tests only
npx playwright test stress.spec.js -g "Zombie"

# Run concurrent tests only
npx playwright test stress.spec.js -g "Concurrent"
```

## Test Modes

### Smart Monkey
Weighted toward complex features (3x weight on Trade, Market, Upgrade).

**Purpose:** Exercise complex code paths that simple tests miss.

### Dumb Monkey
Purely random clicks with equal probability.

**Purpose:** Find unexpected crashes and edge cases.

### Hoarder Monkey
Never buys properties, hoards cash.

**Purpose:** Verify economy drains even passive players. If hoarder survives 100+ rounds, economy is broken.

## Expected Outputs

### Snapshot Files

Location: `snapshots/`

Format:
```
invariant_violation_abc12345_1706012345.json
economic_violation_def67890_1706012346.json
stuck_state_ghi23456_1706012347.json
```

Each snapshot contains:
- 5 historical game states (time-travel)
- Full action history
- Chaos config (seed for reproduction)
- Violation details

### Economic Reports

Location: `reports/`

Format:
```
economy_balance_Inflation_Stress_200R_1706012345.txt
```

Example output:
```
================================================================================
                        ECONOMIC BALANCE REPORT
================================================================================
Game ID:        abc123-def456
Rounds Played:  87
Diagnosis:      RUNAWAY_INFLATION

📈 CASH VELOCITY
  Round 1:   $7,200 total  (+$0)
  Round 20:  $15,400 total (+$410/round avg)
  Round 50:  $42,800 total (+$910/round avg)  ⚠️ ACCELERATION
  Round 87:  $98,200 total (+$1,200/round avg) 🔴 CRITICAL

🏥 RECOMMENDATIONS
  1. Cap GO bonus at 3x base ($600 max)
  2. Implement dynamic rent: base_rent * (1 + round * 0.1)
  3. Add "Wealth Tax" event: 10% of net worth
================================================================================
```

### Test Artifacts

Location: `frontends/sastadice/test-results/`

- `monkey_desync_detected_*.png` - Screenshot at desync moment
- `monkey_stuck_state_*.png` - Screenshot when game stuck
- `action_log.json` - Full action history

## Debugging Workflow

### Reproducing a Bug

1. Chaos test fails with snapshot saved:
   ```
   Snapshot saved to: snapshots/invariant_violation_abc123_1706012345.json
   ```

2. View snapshot summary:
   ```bash
   python -c "
   from app.modules.sastadice.services.snapshot_manager import SnapshotManager
   mgr = SnapshotManager()
   mgr.print_snapshot_summary('snapshots/invariant_violation_abc123_1706012345.json')
   "
   ```

3. Replay to specific frame:
   ```python
   # Load state at frame 2 (before bug manifested)
   game_state = snapshot_mgr.replay_to_frame(snapshot_path, frame_index=2)
   ```

4. Fix bug, re-run with same seed:
   ```bash
   python backend/scripts/simulate_games.py --seed 12345 --chaos-mode
   ```

## Property-Based Testing

Location: `backend/tests/modules/sastadice/test_property_based.py`

### Running Hypothesis Tests

```bash
# Run all property-based tests
pytest backend/tests/modules/sastadice/test_property_based.py

# Run with specific seed
pytest backend/tests/modules/sastadice/test_property_based.py --hypothesis-seed=42

# Increase examples for thorough testing
pytest backend/tests/modules/sastadice/test_property_based.py -v --hypothesis-profile=thorough
```

### Stateful Testing

The `SastaDiceStateMachine` explores random action sequences:

- Creates game with 2-4 players
- Executes 30 random actions per test
- Runs invariant checks after every action
- Finds sequence-dependent bugs

## Economic Balance Issues

### Known Issue: Runaway Inflation

**Problem:**
- GO Bonus: `$200 + Round * $20` (uncapped)
- Max Rent: ~$600 (with full upgrades)
- By Round 50: GO pays $1,200, rent costs $600
- Result: Players earn 2x more than they can lose

**Detection:**
```bash
python backend/scripts/simulate_games.py --enable-economic-monitoring
```

**Fix Applied:**
- `DynamicEconomyScaler.calculate_capped_go_bonus()` - Caps at 3x base
- `DynamicEconomyScaler.calculate_dynamic_rent()` - Scales 10%/round

### Hoarder Test

The Hoarder Monkey verifies economic balance:

```javascript
// If this test passes, economy is broken
test('Hoarder survives 100 rounds without buying');
```

**Current Status:** Economy balance needs tuning. Hoarders can survive too long.

## Troubleshooting

### Snapshots Not Saving

Check directory permissions:
```bash
mkdir -p snapshots
chmod 755 snapshots
```

### Economic Reports Not Generating

Enable monitoring:
```bash
python backend/scripts/simulate_games.py --enable-economic-monitoring
```

### Playwright Screenshots Failing

Create test-results directory:
```bash
mkdir -p frontends/sastadice/test-results
```

### Import Errors

Install hypothesis:
```bash
cd backend
pip install -e ".[dev]"
```

## Future Enhancements

1. **Wealth Tax Event** - Drain 10% of net worth to counter hoarding
2. **Hostile Takeover Event** - Force property changes in stalemates
3. **Network Partition Testing** - Test SSE reconnection logic
4. **Auction Time Extension** - Dynamic timeouts for slow networks
5. **Trade Timeout Handling** - Auto-cancel trades on disconnect

## Contributing

When adding new game features, ensure they:

1. Pass invariant checks (no orphaned state)
2. Don't cause economic imbalance (test with InflationMonitor)
3. Handle disconnects gracefully (test with zombie players)
4. Work under concurrent stress (test with 4-player simultaneous actions)
