# 🐒 Sastadice Chaos & Fuzzing Guide

This guide details the advanced testing framework for **Sastadice**, designed to uncover soft locks, economic exploits, and mathematical inconsistencies through combinatorial fuzzing and chaos engineering.

## 1. Backend Matrix Simulation (`simulate_games.py`)

Run exhaustive simulations covering a combinatorial matrix of game settings.

### 🔥 Fuzzing Mode
Fuzzing generates simulations across 5 dimensions:
- **Players**: 2, 3, 4, 5, 8
- **Wealth**: Poverty (0.1x), Normal (1x), Rich (10x)
- **Inflation**: 0% - 50%
- **Chaos**: 0% - 100%
- **Rounds**: Sudden Death vs Infinite

```bash
# Run all combinations (approx 150+ games)
python backend/scripts/simulate_games.py --fuzz --chaos-mode

# Run a specific number of random fuzzed configs
python backend/scripts/simulate_games.py --fuzz --num-games 20
```

### 🚨 Invariant & Integrity Checks
Every simulation enforces strict mathematical laws after **each turn**:
1.  **Conservation of Mass**: `System Cash (t)` must exactly equal `System Cash (t-1) + Sources - Sinks`. If $1 vanishes without a log, the simulation crashes.
2.  **Asset Integrity**: Tiles cannot lose owners without a transfer event.
3.  **Economic Stalemate**: Fails if **Gini Coefficient > 0.9** after Round 100 (detected "Hoarding Soft Lock").

### 📂 Crash Dumps
If a simulation fails, a JSON replay file is saved automatically:
`CRASH_DUMP_<game_num>_<config_name>.json`
Contains: Seed, Settings, Error Trace, and Player State.

To replay (feature pending fully deterministic replay loader):
```bash
python backend/scripts/simulate_games.py --replay CRASH_DUMP_....json
```

---

## 2. Frontend Monkey Testing (`monkey.spec.js`)

Uses Playwright to unleash "Monkeys" on the UI. They click random buttons, reload pages, and try to break the game.

### Quick Start
```bash
npx playwright test frontends/sastadice/tests/e2e/monkey.spec.js
```

### 🐵 Monkey Types
| Type | Behavior | Purpose |
|------|----------|---------|
| **Smart Monkey** | Prefers Trade, Upgrade, Market actions (Weights: 3x) | Test complex logic paths |
| **Dumb Monkey** | Purely random clicks | Baseline noise testing |
| **Hoarder Monkey** | NEVER buys properties | Test economy drain & anti-hoarding mechanics |
| **Chaos Monkey** | Randomly **RELOADS PAGE** (10% chance) | Test reconnection & state recovery |

### ⚔️ 4-Player Chaos Scenario
Run the **"4-Player Chaos Game"** test to spawn:
- **1 Observer** (Host, verifying UI)
- **3 Chaos Monkeys** (Clients, reloading and spamming)
This stress-tests the WebSocket server and synchronization logic under heavy load.

---

## 3. Troubleshooting

- **Desync Errors**: If frontend logs "DESYNC", check `server_state_hash` vs `client_state_hash`.
- **Inflation Failures**: If `INFLATION_RUNAWAY` occurs, check if `Rent` > `Go Bonus` in late game.
- **Syntax Errors in Tests**: Ensure `playwright.config.js` has appropriate timeouts (Chaos tests take longer).
