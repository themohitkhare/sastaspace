# TypeWars Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the TypeWars SpacetimeDB Rust game module — 5 tables, 4 player reducers, 3 scheduled reducers, 5 legion combat mechanics — deployable to stdb.sastaspace.com as module `typewars`.

**Architecture:** `game/` is a standalone SpacetimeDB Rust module at the monorepo root, separate from `module/`. Pure combat math lives in `legion.rs` (no DB access, fully unit-testable). Domain reducers live in focused files: `player.rs`, `session.rs`, `word.rs`, `region.rs`, `war.rs`. Static word lists are embedded at compile time in `words/`. Three scheduled reducers fire at fixed intervals: every 2s (word expiry), 60s (region tick), 5min (global war). The existing `module/` is untouched.

**Tech Stack:** Rust 2021, `spacetimedb = "2.1"`, SpacetimeDB CLI (`spacetime`). Follow the exact patterns from `module/src/lib.rs`: `#[table(accessor = name, public)]`, `#[reducer]`, `ctx.db.table().pk().find()`, `ctx.db.table().iter()`.

---

## File Map

| File | Responsibility |
|------|---------------|
| `game/Cargo.toml` | crate config |
| `game/src/lib.rs` | init, lifecycle reducers, scheduler registration |
| `game/src/legion.rs` | pure combat math — multiplier, damage, legion bonuses |
| `game/src/player.rs` | `Player` table + `register_player` |
| `game/src/region.rs` | `Region` table + `seed_regions` + `region_tick` + `end_season` |
| `game/src/session.rs` | `BattleSession` table + `start_battle` + `end_battle` + `auto_end_battle` |
| `game/src/word.rs` | `Word` table + `spawn_words` + `submit_word` + `expire_words_tick` |
| `game/src/war.rs` | `GlobalWar` table + `global_war_tick` |
| `game/src/words/mod.rs` | word list module root |
| `game/src/words/easy.rs` | easy words (3–5 chars, base_damage=10) |
| `game/src/words/medium.rs` | medium words (6–8 chars, base_damage=25) |
| `game/src/words/hard.rs` | hard words (9–13 chars, base_damage=50) |
| `game/src/words/rare.rs` | Codex-only words (base_damage=100) |

---

## Task 1: Scaffold the game/ module

**Files:**
- Create: `game/Cargo.toml`
- Create: `game/src/lib.rs`

- [ ] **Step 1: Create game/Cargo.toml**

```toml
[package]
name = "typewars-module"
version = "0.1.0"
edition = "2021"
publish = false

[lib]
crate-type = ["cdylib"]

[dependencies]
spacetimedb = "2.1"
log = "0.4"

[profile.release]
opt-level = "z"
lto = true
strip = true
codegen-units = 1
```

- [ ] **Step 2: Create game/src/lib.rs**

```rust
use spacetimedb::{reducer, ReducerContext};

mod legion;
mod player;
mod region;
mod session;
mod war;
mod word;
mod words;

#[reducer(init)]
pub fn init(ctx: &ReducerContext) {
    region::seed_regions(ctx);
    war::init_global_war(ctx);
    // Schedulers registered here — filled in Tasks 9, 10, 11
}

#[reducer(client_connected)]
pub fn client_connected(_ctx: &ReducerContext) {}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    session::auto_end_battle(ctx);
}
```

- [ ] **Step 3: Verify scaffold compiles with expected errors**

```bash
cd game && cargo build 2>&1 | head -30
```

Expected: errors about missing modules (`legion`, `player`, etc.) — that's fine. No syntax errors in `lib.rs` itself.

- [ ] **Step 4: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/
git commit -m "feat(typewars): scaffold game/ SpacetimeDB module"
```

---

## Task 2: Word lists

**Files:**
- Create: `game/src/words/mod.rs`
- Create: `game/src/words/easy.rs`
- Create: `game/src/words/medium.rs`
- Create: `game/src/words/hard.rs`
- Create: `game/src/words/rare.rs`

- [ ] **Step 1: Create game/src/words/mod.rs**

```rust
pub mod easy;
pub mod hard;
pub mod medium;
pub mod rare;
```

- [ ] **Step 2: Create game/src/words/easy.rs** (3–5 char, base_damage=10)

```rust
pub const WORDS: &[&str] = &[
    "fire", "void", "war", "red", "ash", "run", "cut", "hit",
    "glow", "flux", "aim", "raw", "iron", "dust", "burn",
    "kill", "dark", "bolt", "claw", "wave", "edge", "core",
    "scar", "pulse", "node", "grip", "raze", "halt", "draw",
    "leap", "bind", "tear", "snap", "ward", "seal", "mark",
    "rush", "bane", "echo", "lock", "cast", "dusk", "dawn",
    "gate", "vex", "foe", "ruin", "arc", "step", "rock",
    "blaze", "clash", "crush", "drive", "earth", "faith", "forge",
    "ghost", "guard", "heart", "ignite", "lance", "march", "oath",
    "pact", "raise", "ridge", "rift", "siege", "skies", "slay",
    "smite", "storm", "surge", "swear", "sword", "titan", "torch",
    "trace", "trail", "tribe", "unity", "valor", "vault", "vigil",
    "vow", "wake", "wield", "wrath", "zone", "apex", "bear",
    "blade", "brave", "break", "crest", "cross", "cry", "deep",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}
```

- [ ] **Step 3: Create game/src/words/medium.rs** (6–8 char, base_damage=25)

```rust
pub const WORDS: &[&str] = &[
    "oblique", "cipher", "fractal", "embark", "fervent",
    "ignite", "herald", "invoke", "latent", "mortal",
    "nebula", "oblige", "pariah", "quartz", "resist",
    "solace", "thresh", "unfurl", "vertex", "warden",
    "zenith", "ablaze", "brazen", "combat", "dagger",
    "emblem", "falcon", "gambit", "hunter", "impact",
    "jagged", "kindle", "legion", "menace", "nether",
    "onrush", "pallor", "rankle", "scorch", "torment",
    "unbind", "vortex", "wither", "expose", "zealot",
    "abrupt", "beacon", "candor", "defiant", "eclipse",
    "flicker", "granite", "hostile", "igneous", "justice",
    "kinesis", "liberate", "monarch", "nuclear", "oblique",
    "phantom", "quantum", "rapture", "sanctum", "tempest",
    "unknown", "vagrant", "warfare", "xenolith", "yeoman",
    "abandon", "barrage", "crusade", "destiny", "eternal",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}
```

- [ ] **Step 4: Create game/src/words/hard.rs** (9–13 char, base_damage=50)

```rust
pub const WORDS: &[&str] = &[
    "obliterate", "devastate", "onslaught", "annihilate",
    "cataclysm", "resistance", "liberation", "subjugate",
    "terminate", "overpower", "incinerate", "catastrophe",
    "abominable", "belligerent", "conflagration", "dreadnought",
    "extinguish", "fortified", "groundswell", "hemisphere",
    "incursion", "jurisdiction", "knighthood", "lancehead",
    "marauding", "nightwatch", "occupation", "pioneering",
    "quarantine", "relentless", "stratagem", "threshold",
    "unbounded", "vanguard", "warlocked", "xenolith",
    "zealotry", "abscission", "battlefront", "commandeer",
    "decimation", "embattled", "frontlines", "galvanize",
    "harbinger", "infiltrate", "juggernaut", "kingslayer",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}
```

- [ ] **Step 5: Create game/src/words/rare.rs** (Codex-only, base_damage=100)

```rust
pub const WORDS: &[&str] = &[
    "sovereignty", "transcendence", "illumination", "annihilation",
    "omnipotence", "resurgence", "cataclysmic", "invincible",
    "apocalypse", "supernova", "singularity", "constellation",
    "dominion", "radiance", "omniscience", "ascendancy",
    "revelation", "primordial", "celestial", "unstoppable",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}
```

- [ ] **Step 6: Verify words module compiles**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -10
```

Expected: errors about other missing modules, but NO errors inside `words/`.

- [ ] **Step 7: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/words/
git commit -m "feat(typewars): add word lists easy/medium/hard/rare"
```

---

## Task 3: Legion logic (pure functions, fully unit-testable)

**Files:**
- Create: `game/src/legion.rs`

This module has zero DB imports — all pure functions. Unit tests run without `spacetimedb`.

- [ ] **Step 1: Write the failing tests**

Create `game/src/legion.rs` with tests first:

```rust
pub const LEGION_NAMES: [&str; 5] = ["Ashborn", "The Codex", "Wardens", "Surge", "Solari"];
pub const LEGION_COUNT: u8 = 5;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn surge_has_higher_multiplier_cap() {
        assert_eq!(multiplier_cap(3), 5.0_f32);
        assert_eq!(multiplier_cap(0), 3.0_f32);
        assert_eq!(multiplier_cap(1), 3.0_f32);
        assert_eq!(multiplier_cap(2), 3.0_f32);
        assert_eq!(multiplier_cap(4), 3.0_f32);
    }

    #[test]
    fn multiplier_grows_with_streak_and_caps() {
        assert!((compute_multiplier(0, 3.0) - 1.0).abs() < 0.001);
        assert!((compute_multiplier(1, 3.0) - 1.25).abs() < 0.001);
        assert!((compute_multiplier(4, 3.0) - 2.0).abs() < 0.001);
        assert!((compute_multiplier(8, 3.0) - 3.0).abs() < 0.001);
        assert!((compute_multiplier(100, 3.0) - 3.0).abs() < 0.001); // capped
        assert!((compute_multiplier(16, 5.0) - 5.0).abs() < 0.001);  // Surge capped
    }

    #[test]
    fn ashborn_burst_fires_at_10_20_not_9_or_11() {
        assert!(ashborn_burst_active(0, 10));
        assert!(ashborn_burst_active(0, 20));
        assert!(ashborn_burst_active(0, 30));
        assert!(!ashborn_burst_active(0, 9));
        assert!(!ashborn_burst_active(0, 11));
        assert!(!ashborn_burst_active(1, 10)); // wrong legion
        assert!(!ashborn_burst_active(0, 0));  // streak 0 never triggers
    }

    #[test]
    fn codex_rare_requires_90_percent_and_nonce_mod_7() {
        // 9 hits, 1 miss = 90% — qualifies; nonce 0 % 7 == 0 — triggers
        assert!(codex_can_inject_rare(1, 9, 1, 0));
        // 8 hits, 2 misses = 80% — does not qualify
        assert!(!codex_can_inject_rare(1, 8, 2, 0));
        // wrong legion
        assert!(!codex_can_inject_rare(0, 9, 1, 0));
        // right accuracy, wrong nonce
        assert!(!codex_can_inject_rare(1, 9, 1, 1));
        // no shots taken yet
        assert!(!codex_can_inject_rare(1, 0, 0, 0));
    }

    #[test]
    fn damage_is_base_times_multiplier() {
        assert_eq!(compute_damage(10, 2.0, 5, 1), 20); // non-Ashborn
    }

    #[test]
    fn ashborn_triples_damage_at_streak_10() {
        // base=10, multiplier=3.0 (streak 8 gives 3.0), streak=10, legion=Ashborn
        assert_eq!(compute_damage(10, 3.0, 10, 0), 90); // 10 * 3.0 * 3 = 90
    }
}
```

- [ ] **Step 2: Run tests, verify they fail (functions not yet defined)**

```bash
cd game && cargo test legion 2>&1 | tail -15
```

Expected: compile errors — `multiplier_cap`, `compute_multiplier`, etc. not found.

- [ ] **Step 3: Implement the functions**

Add above the `#[cfg(test)]` block in `game/src/legion.rs`:

```rust
/// Multiplier ceiling: Surge (legion 3) gets 5.0, all others 3.0.
pub fn multiplier_cap(legion: u8) -> f32 {
    if legion == 3 { 5.0 } else { 3.0 }
}

/// Streak-based damage multiplier, capped per legion.
pub fn compute_multiplier(streak: u32, cap: f32) -> f32 {
    (1.0 + streak as f32 * 0.25).min(cap)
}

/// True when Ashborn (legion 0) hits their 10-word burst trigger.
pub fn ashborn_burst_active(legion: u8, streak: u32) -> bool {
    legion == 0 && streak > 0 && streak % 10 == 0
}

/// True when a Codex (legion 1) player with ≥90% accuracy rolls the ~14% injection nonce.
pub fn codex_can_inject_rare(legion: u8, hits: u32, misses: u32, nonce: u64) -> bool {
    if legion != 1 {
        return false;
    }
    let total = hits + misses;
    if total == 0 {
        return false;
    }
    hits as f32 / total as f32 >= 0.90 && nonce % 7 == 0
}

/// Final damage after multiplier and legion bonuses.
/// `streak` is post-increment (the value after this word hit).
pub fn compute_damage(base_damage: u64, multiplier: f32, streak: u32, legion: u8) -> u64 {
    let mut dmg = base_damage as f32 * multiplier;
    if ashborn_burst_active(legion, streak) {
        dmg *= 3.0;
    }
    dmg as u64
}
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd game && cargo test legion 2>&1 | tail -15
```

Expected: `test legion::tests::... ok` for all 6 tests.

- [ ] **Step 5: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/legion.rs
git commit -m "feat(typewars): add legion combat math with unit tests"
```

---

## Task 4: Tables + init seeding

**Files:**
- Create: `game/src/player.rs`
- Create: `game/src/session.rs`
- Create: `game/src/word.rs` (tables only — reducers added in Tasks 6 and 7)
- Create: `game/src/region.rs` (tables + seed — tick added in Task 10)
- Create: `game/src/war.rs` (table + init — tick added in Task 11)

- [ ] **Step 1: Create game/src/player.rs**

```rust
use spacetimedb::{table, Identity, Timestamp};

#[table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    pub identity: Identity,
    pub username: String,
    pub legion: u8,
    pub total_damage: u64,
    pub season_damage: u64,
    pub best_wpm: u32,
    pub joined_at: Timestamp,
}
```

- [ ] **Step 2: Create game/src/session.rs**

```rust
use spacetimedb::{table, Identity, Timestamp};

#[table(accessor = battle_session, public)]
pub struct BattleSession {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    #[index(btree)]
    pub player_identity: Identity,
    pub region_id: u32,
    pub started_at: Timestamp,
    pub streak: u32,
    pub multiplier: f32,
    pub accuracy_hits: u32,
    pub accuracy_misses: u32,
    pub damage_dealt: u64,
    /// Running spawn counter — used as part of the deterministic word selection nonce.
    pub words_spawned: u32,
    pub active: bool,
}

/// Called from client_disconnected to clean up any dangling active sessions.
pub fn auto_end_battle(ctx: &spacetimedb::ReducerContext) {
    use spacetimedb::Table;
    let sessions: Vec<BattleSession> = ctx.db.battle_session()
        .iter()
        .filter(|s| s.player_identity == ctx.sender() && s.active)
        .collect();
    for session in sessions {
        end_battle_core(ctx, session);
    }
}

pub fn end_battle_core(ctx: &spacetimedb::ReducerContext, session: BattleSession) {
    use spacetimedb::Table;
    if let Some(player) = ctx.db.player().identity().find(session.player_identity) {
        if player.legion == 2 {
            if let Some(mut region) = ctx.db.region().id().find(session.region_id) {
                region.active_wardens = region.active_wardens.saturating_sub(1);
                ctx.db.region().id().update(region);
            }
        }
        let word_ids: Vec<u64> = ctx.db.word().session_id().filter(&session.id)
            .map(|w| w.id)
            .collect();
        for wid in word_ids {
            ctx.db.word().id().delete(wid);
        }
        let mut p = player;
        p.total_damage += session.damage_dealt;
        p.season_damage += session.damage_dealt;
        ctx.db.player().identity().update(p);
    }
    let mut s = session;
    s.active = false;
    ctx.db.battle_session().id().update(s);
}
```

- [ ] **Step 3: Create game/src/word.rs** (tables only for now)

```rust
use spacetimedb::{table, Timestamp};

#[table(accessor = word, public)]
pub struct Word {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    #[index(btree)]
    pub session_id: u64,
    pub text: String,
    pub difficulty: u8,      // 1=easy 2=medium 3=hard 4=rare
    pub base_damage: u64,
    pub spawned_at: Timestamp,
    pub expires_at: Timestamp,
}
```

- [ ] **Step 4: Create game/src/region.rs** (tables + seeding)

```rust
use spacetimedb::{table, ReducerContext, Table};

#[table(accessor = region, public)]
pub struct Region {
    #[primary_key]
    pub id: u32,
    pub name: String,
    pub tier: u8,
    pub controlling_legion: i8,   // -1 = enemy-held
    pub enemy_hp: u64,
    pub enemy_max_hp: u64,
    pub regen_rate: u64,
    pub damage_0: u64,
    pub damage_1: u64,
    pub damage_2: u64,
    pub damage_3: u64,
    pub damage_4: u64,
    pub active_wardens: u32,
}

const REGION_SEED: &[(&str, u8)] = &[
    ("Ashfall Reach", 1), ("Bone Wastes", 1), ("Cinder Plains", 1),
    ("Dusk Hollow", 1),   ("Ember Ridge", 1), ("Frost Gate", 1),
    ("Gloom Marches", 1), ("Haze Fields", 1), ("Iron Strand", 1),
    ("Jade Crossing", 1),
    ("Krell Depths", 2),  ("Lava Run", 2),    ("Murk Basin", 2),
    ("Null Shore", 2),    ("Obsidian Shelf", 2), ("Pale Summit", 2),
    ("Quake Line", 2),    ("Rift Corridor", 2),  ("Scorch Trail", 2),
    ("Tide Lock", 2),
    ("Umbral Spire", 3),  ("Void Cradle", 3), ("War Engine", 3),
    ("Xen Bastion", 3),   ("Zero Point", 3),
];

fn hp_for_tier(tier: u8) -> u64 {
    match tier { 1 => 50_000, 2 => 100_000, 3 => 250_000, _ => 50_000 }
}

fn regen_for_tier(tier: u8) -> u64 {
    match tier { 1 => 200, 2 => 500, 3 => 1_500, _ => 200 }
}

pub fn seed_regions(ctx: &ReducerContext) {
    for (i, (name, tier)) in REGION_SEED.iter().enumerate() {
        let max_hp = hp_for_tier(*tier);
        ctx.db.region().insert(Region {
            id: i as u32,
            name: name.to_string(),
            tier: *tier,
            controlling_legion: -1,
            enemy_hp: max_hp,
            enemy_max_hp: max_hp,
            regen_rate: regen_for_tier(*tier),
            damage_0: 0, damage_1: 0, damage_2: 0, damage_3: 0, damage_4: 0,
            active_wardens: 0,
        });
    }
}

pub fn add_legion_damage(region: &mut Region, legion: u8, amount: u64) {
    match legion {
        0 => region.damage_0 += amount,
        1 => region.damage_1 += amount,
        2 => region.damage_2 += amount,
        3 => region.damage_3 += amount,
        4 => region.damage_4 += amount,
        _ => {}
    }
}

pub fn winning_legion(region: &Region) -> u8 {
    let damages = [region.damage_0, region.damage_1, region.damage_2, region.damage_3, region.damage_4];
    damages.iter().enumerate().max_by_key(|(_, &d)| d).map(|(i, _)| i as u8).unwrap_or(0)
}

pub fn reset_legion_damage(region: &mut Region) {
    region.damage_0 = 0; region.damage_1 = 0; region.damage_2 = 0;
    region.damage_3 = 0; region.damage_4 = 0;
}

pub fn effective_regen(base_regen: u64, active_wardens: u32) -> u64 {
    if active_wardens >= 3 { base_regen / 2 } else { base_regen }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_region(d0: u64, d1: u64, d2: u64, d3: u64, d4: u64) -> Region {
        Region {
            id: 0, name: "Test".into(), tier: 1,
            controlling_legion: -1, enemy_hp: 0, enemy_max_hp: 50_000,
            regen_rate: 200, damage_0: d0, damage_1: d1, damage_2: d2,
            damage_3: d3, damage_4: d4, active_wardens: 0,
        }
    }

    #[test]
    fn winning_legion_picks_highest_damage() {
        let r = make_region(100, 500, 50, 200, 10);
        assert_eq!(winning_legion(&r), 1);
    }

    #[test]
    fn warden_bulwark_halves_regen_at_3_or_more() {
        assert_eq!(effective_regen(200, 3), 100);
        assert_eq!(effective_regen(200, 5), 100);
        assert_eq!(effective_regen(200, 2), 200);
        assert_eq!(effective_regen(200, 0), 200);
    }
}
```

- [ ] **Step 5: Create game/src/war.rs** (table + init only)

```rust
use spacetimedb::{table, ReducerContext, Table, Timestamp};

#[table(accessor = global_war, public)]
pub struct GlobalWar {
    #[primary_key]
    pub id: u32,
    pub season: u32,
    pub enemy_territories: u32,
    pub liberated_territories: u32,
    pub season_start: Timestamp,
}

pub fn init_global_war(ctx: &ReducerContext) {
    ctx.db.global_war().insert(GlobalWar {
        id: 1,
        season: 1,
        enemy_territories: 25,
        liberated_territories: 0,
        season_start: ctx.timestamp,
    });
}
```

- [ ] **Step 6: Run region unit tests**

```bash
cd game && cargo test region 2>&1 | tail -10
```

Expected: 2 tests pass (`winning_legion_picks_highest_damage`, `warden_bulwark_halves_regen_at_3_or_more`).

- [ ] **Step 7: Verify full build (expect errors only from unimplemented stubs)**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -20
```

Expected: zero `^error` lines.

- [ ] **Step 8: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/
git commit -m "feat(typewars): add all tables, region seeding, war init, region unit tests"
```

---

## Task 5: register_player reducer

**Files:**
- Modify: `game/src/player.rs`

- [ ] **Step 1: Write failing tests**

Append to `game/src/player.rs`:

```rust
pub fn validate_registration(username: &str, legion: u8) -> Result<(), String> {
    todo!()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legion_0_to_4_are_valid() {
        assert!(validate_registration("alice", 0).is_ok());
        assert!(validate_registration("alice", 4).is_ok());
    }

    #[test]
    fn legion_5_is_invalid() {
        assert!(validate_registration("alice", 5).is_err());
    }

    #[test]
    fn empty_username_is_invalid() {
        assert!(validate_registration("", 0).is_err());
    }

    #[test]
    fn username_max_32_chars() {
        assert!(validate_registration(&"a".repeat(32), 0).is_ok());
        assert!(validate_registration(&"a".repeat(33), 0).is_err());
    }
}
```

- [ ] **Step 2: Run tests to confirm they fail with todo!()**

```bash
cd game && cargo test player 2>&1 | tail -10
```

Expected: tests panic with `not yet implemented`.

- [ ] **Step 3: Implement validate_registration and register_player**

Replace the `todo!()` stub and add the reducer:

```rust
use spacetimedb::{reducer, ReducerContext, Table};
use crate::legion::LEGION_COUNT;

pub fn validate_registration(username: &str, legion: u8) -> Result<(), String> {
    if username.is_empty() {
        return Err("username required".into());
    }
    if username.len() > 32 {
        return Err("username too long (max 32 chars)".into());
    }
    if legion >= LEGION_COUNT {
        return Err(format!("invalid legion {legion} (max {})", LEGION_COUNT - 1));
    }
    Ok(())
}

#[reducer]
pub fn register_player(
    ctx: &ReducerContext,
    username: String,
    legion: u8,
) -> Result<(), String> {
    if ctx.db.player().identity().find(ctx.sender()).is_some() {
        return Err("already registered".into());
    }
    validate_registration(&username, legion)?;
    ctx.db.player().insert(Player {
        identity: ctx.sender(),
        username,
        legion,
        total_damage: 0,
        season_damage: 0,
        best_wpm: 0,
        joined_at: ctx.timestamp,
    });
    Ok(())
}
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd game && cargo test player 2>&1 | tail -10
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/player.rs
git commit -m "feat(typewars): add register_player with validation tests"
```

---

## Task 6: Word spawning helper

**Files:**
- Modify: `game/src/word.rs`

This helper is called from `start_battle`, `submit_word`, and `expire_words_tick`. Define it once here.

- [ ] **Step 1: Write unit tests**

Append to `game/src/word.rs`:

```rust
pub fn difficulty_for_slot(_slot: u32) -> u8 { todo!() }
pub fn select_word(_difficulty: u8, _session_id: u64, _spawn_count: u32, _timestamp_secs: u64) -> &'static str { todo!() }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slots_0_to_4_are_easy() {
        for i in 0u32..5 {
            assert_eq!(difficulty_for_slot(i), 1, "slot {i} should be easy");
        }
    }

    #[test]
    fn slots_5_and_6_are_medium() {
        assert_eq!(difficulty_for_slot(5), 2);
        assert_eq!(difficulty_for_slot(6), 2);
    }

    #[test]
    fn slot_7_is_hard() {
        assert_eq!(difficulty_for_slot(7), 3);
    }

    #[test]
    fn slot_8_wraps_to_easy() {
        assert_eq!(difficulty_for_slot(8), 1);
    }

    #[test]
    fn word_selection_is_deterministic() {
        assert_eq!(
            select_word(1, 42, 0, 1000),
            select_word(1, 42, 0, 1000)
        );
    }

    #[test]
    fn word_selection_varies_across_nonces() {
        let words: std::collections::HashSet<_> = (0u64..20)
            .map(|n| select_word(1, 1, 0, n))
            .collect();
        assert!(words.len() > 1);
    }
}
```

- [ ] **Step 2: Run tests, verify they fail (todo! panics)**

```bash
cd game && cargo test word 2>&1 | tail -10
```

Expected: tests panic with `not yet implemented`.

- [ ] **Step 3: Implement helpers and spawn_words**

Replace the `todo!()` stubs and add `spawn_words`:

```rust
use spacetimedb::{ReducerContext, Table};
use crate::words;

pub fn difficulty_for_slot(slot: u32) -> u8 {
    match slot % 8 {
        0 | 1 | 2 | 3 | 4 => 1,
        5 | 6 => 2,
        _ => 3,
    }
}

pub fn select_word(difficulty: u8, session_id: u64, spawn_count: u32, timestamp_secs: u64) -> &'static str {
    let nonce = session_id ^ spawn_count as u64 ^ timestamp_secs;
    match difficulty {
        1 => words::easy::select(nonce),
        2 => words::medium::select(nonce),
        3 => words::hard::select(nonce),
        4 => words::rare::select(nonce),
        _ => words::easy::select(nonce),
    }
}

/// Spawn `count` words for `session_id`, starting the slot counter at `spawn_start`.
/// If `inject_rare` is true, the first word is a rare Codex word regardless of distribution.
pub fn spawn_words(
    ctx: &ReducerContext,
    session_id: u64,
    spawn_start: u32,
    count: u32,
    inject_rare: bool,
) {
    let ts = ctx.timestamp;
    let ts_secs = ts.to_micros_since_unix_epoch() as u64 / 1_000_000;
    let expires_at = spacetimedb::Timestamp::from_micros_since_unix_epoch(
        ts.to_micros_since_unix_epoch() + 5_000_000,
    );

    for i in 0..count {
        let slot = spawn_start + i;
        let (difficulty, base_damage) = if inject_rare && i == 0 {
            (4u8, 100u64)
        } else {
            let d = difficulty_for_slot(slot);
            let dmg = match d { 1 => 10, 2 => 25, 3 => 50, _ => 10 };
            (d, dmg)
        };

        let text = select_word(difficulty, session_id, slot, ts_secs);
        ctx.db.word().insert(Word {
            id: 0,
            session_id,
            text: text.to_string(),
            difficulty,
            base_damage,
            spawned_at: ts,
            expires_at,
        });
    }
}
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd game && cargo test word 2>&1 | tail -10
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/word.rs
git commit -m "feat(typewars): add word spawning helper with deterministic selection"
```

---

## Task 7: start_battle and end_battle reducers

**Files:**
- Modify: `game/src/session.rs`

- [ ] **Step 1: Add reducers to session.rs**

Append to `game/src/session.rs`:

```rust
use spacetimedb::{reducer, ReducerContext, Table};
use crate::word::spawn_words;

#[reducer]
pub fn start_battle(ctx: &ReducerContext, region_id: u32) -> Result<(), String> {
    let player = ctx.db.player().identity().find(ctx.sender())
        .ok_or_else(|| "not registered".to_string())?;

    let already_active = ctx.db.battle_session()
        .iter()
        .any(|s| s.player_identity == ctx.sender() && s.active);
    if already_active {
        return Err("already in a battle".into());
    }

    ctx.db.region().id().find(region_id)
        .ok_or_else(|| format!("region {region_id} not found"))?;

    let session = ctx.db.battle_session().insert(BattleSession {
        id: 0,
        player_identity: ctx.sender(),
        region_id,
        started_at: ctx.timestamp,
        streak: 0,
        multiplier: 1.0,
        accuracy_hits: 0,
        accuracy_misses: 0,
        damage_dealt: 0,
        words_spawned: 8,  // pre-increment: we're about to spawn 8
        active: true,
    });

    if player.legion == 2 {
        if let Some(mut region) = ctx.db.region().id().find(region_id) {
            region.active_wardens += 1;
            ctx.db.region().id().update(region);
        }
    }

    spawn_words(ctx, session.id, 0, 8, false);
    Ok(())
}

#[reducer]
pub fn end_battle(ctx: &ReducerContext, session_id: u64) -> Result<(), String> {
    let session = ctx.db.battle_session().id().find(session_id)
        .ok_or_else(|| "session not found".to_string())?;
    if session.player_identity != ctx.sender() {
        return Err("not your session".into());
    }
    if !session.active {
        return Err("session already ended".into());
    }
    end_battle_core(ctx, session);
    Ok(())
}
```

- [ ] **Step 2: Verify compile**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -20
```

Expected: zero `^error` lines.

- [ ] **Step 3: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/session.rs
git commit -m "feat(typewars): add start_battle and end_battle reducers"
```

---

## Task 8: submit_word reducer (hot path)

**Files:**
- Modify: `game/src/word.rs`

- [ ] **Step 1: Write unit tests for hit/miss helpers**

Append to the `#[cfg(test)]` block in `game/src/word.rs`:

```rust
    #[test]
    fn miss_resets_streak_and_multiplier() {
        let (s, m) = apply_miss(8, 3.0);
        assert_eq!(s, 0);
        assert!((m - 1.0).abs() < 0.001);
    }

    #[test]
    fn hit_increments_streak_and_raises_multiplier() {
        let (s, m) = apply_hit(0, 3.0);
        assert_eq!(s, 1);
        assert!((m - 1.25).abs() < 0.001);
    }

    #[test]
    fn hit_at_cap_stays_capped() {
        let (s, m) = apply_hit(12, 3.0); // streak 12 → 1 + 12*0.25=4.0 → capped at 3.0
        assert_eq!(s, 13);
        assert!((m - 3.0).abs() < 0.001);
    }
```

- [ ] **Step 2: Run tests, verify new ones fail**

```bash
cd game && cargo test word 2>&1 | tail -15
```

Expected: compile error — `apply_miss` and `apply_hit` not defined.

- [ ] **Step 3: Implement apply_miss, apply_hit, and submit_word**

Append to `game/src/word.rs` (before `#[cfg(test)]`):

```rust
use spacetimedb::{reducer, ReducerContext, Table};
use crate::{legion, region};

pub fn apply_miss(_streak: u32, _multiplier: f32) -> (u32, f32) {
    (0, 1.0)
}

pub fn apply_hit(streak: u32, cap: f32) -> (u32, f32) {
    let new_streak = streak + 1;
    (new_streak, legion::compute_multiplier(new_streak, cap))
}

#[reducer]
pub fn submit_word(
    ctx: &ReducerContext,
    session_id: u64,
    word: String,
) -> Result<(), String> {
    let mut session = ctx.db.battle_session().id().find(session_id)
        .ok_or_else(|| "session not found".to_string())?;
    if session.player_identity != ctx.sender() {
        return Err("not your session".into());
    }
    if !session.active {
        return Err("session ended".into());
    }

    let player = ctx.db.player().identity().find(ctx.sender())
        .ok_or_else(|| "player not found".to_string())?;

    let ts_now = ctx.timestamp.to_micros_since_unix_epoch();

    // Find matching live word in this session
    let hit: Option<Word> = ctx.db.word()
        .iter()
        .find(|w| {
            w.session_id == session_id
                && w.text == word
                && w.expires_at.to_micros_since_unix_epoch() > ts_now
        });

    if hit.is_none() {
        // Miss path: reset streak
        session.accuracy_misses += 1;
        let (s, m) = apply_miss(session.streak, session.multiplier);
        session.streak = s;
        session.multiplier = m;
        ctx.db.battle_session().id().update(session);
        return Ok(());
    }

    let hit_word = hit.unwrap();
    session.accuracy_hits += 1;

    let cap = legion::multiplier_cap(player.legion);
    let (new_streak, new_mult) = apply_hit(session.streak, cap);
    session.streak = new_streak;
    session.multiplier = new_mult;

    let damage = legion::compute_damage(hit_word.base_damage, new_mult, new_streak, player.legion);

    // Ashborn burst resets streak after the bonus is applied
    if legion::ashborn_burst_active(player.legion, new_streak) {
        session.streak = 0;
        session.multiplier = 1.0;
    }

    session.damage_dealt += damage;
    session.words_spawned += 1;

    // Apply damage to region
    if let Some(mut reg) = ctx.db.region().id().find(session.region_id) {
        reg.enemy_hp = reg.enemy_hp.saturating_sub(damage);
        region::add_legion_damage(&mut reg, player.legion, damage);
        ctx.db.region().id().update(reg);
    }

    // Delete matched word
    ctx.db.word().id().delete(hit_word.id);

    // Codex rare word injection check (~14% when accuracy ≥ 90%)
    let ts_secs = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1_000_000;
    let inject_rare = legion::codex_can_inject_rare(
        player.legion,
        session.accuracy_hits,
        session.accuracy_misses,
        ts_secs,
    );

    // Capture values before session is moved into update()
    let sid = session.id;
    let spawn_start = session.words_spawned;
    ctx.db.battle_session().id().update(session);

    // Spawn 1 replacement word
    spawn_words(ctx, sid, spawn_start, 1, inject_rare);

    Ok(())
}
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
cd game && cargo test word 2>&1 | tail -15
```

Expected: 9 tests pass.

- [ ] **Step 5: Full compile check**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -20
```

Expected: zero `^error` lines.

- [ ] **Step 6: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/word.rs
git commit -m "feat(typewars): add submit_word hot path with all legion bonuses"
```

---

## Task 9: expire_words_tick scheduled reducer

**Files:**
- Modify: `game/src/word.rs`
- Modify: `game/src/lib.rs`

**Note on scheduled reducers in SpacetimeDB 2.1:** A scheduled reducer requires a companion scheduler table with a `scheduled_at: ScheduledAt` field and `#[table(name = ..., scheduled(fn_name))]`. The reducer receives the schedule row as its second arg. If `ScheduledAt` is not importable from `spacetimedb`, check the docs — it may need `use spacetimedb::scheduler::ScheduledAt` in some versions.

- [ ] **Step 1: Add scheduler table and reducer to word.rs**

Append to `game/src/word.rs`:

```rust
use spacetimedb::ScheduledAt;

#[table(name = word_expire_schedule, scheduled(expire_words_tick))]
pub struct WordExpireSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduledAt,
}

#[reducer]
pub fn expire_words_tick(ctx: &ReducerContext, _arg: WordExpireSchedule) -> Result<(), String> {
    let ts_now = ctx.timestamp.to_micros_since_unix_epoch();

    // Collect expired words and track which sessions they belong to
    let expired: Vec<Word> = ctx.db.word()
        .iter()
        .filter(|w| w.expires_at.to_micros_since_unix_epoch() <= ts_now)
        .collect();

    let mut affected: std::collections::HashSet<u64> = std::collections::HashSet::new();
    for w in expired {
        affected.insert(w.session_id);
        ctx.db.word().id().delete(w.id);
    }

    // Reset streak/multiplier for sessions that had words expire
    for sid in &affected {
        if let Some(mut s) = ctx.db.battle_session().id().find(*sid) {
            if s.active {
                s.streak = 0;
                s.multiplier = 1.0;
                ctx.db.battle_session().id().update(s);
            }
        }
    }

    // Refill active sessions that have fewer than 4 words remaining
    let active: Vec<crate::session::BattleSession> = ctx.db.battle_session()
        .iter()
        .filter(|s| s.active)
        .collect();

    for s in active {
        let word_count = ctx.db.word().iter().filter(|w| w.session_id == s.id).count();
        if word_count < 4 {
            let needed = (8 - word_count) as u32;
            let spawn_start = s.words_spawned;
            let mut updated_s = s.clone();
            updated_s.words_spawned += needed;
            ctx.db.battle_session().id().update(updated_s);
            spawn_words(ctx, s.id, spawn_start, needed, false);
        }
    }

    Ok(())
}
```

`BattleSession` needs `#[derive(Clone)]` for the `.clone()` call above. Add it to the struct in `session.rs`:

```rust
#[derive(Clone)]
#[table(accessor = battle_session, public)]
pub struct BattleSession { ... }
```

- [ ] **Step 2: Register the scheduler in lib.rs init**

Replace `game/src/lib.rs`:

```rust
use spacetimedb::{reducer, ReducerContext, ScheduledAt};
use std::time::Duration;

mod legion;
mod player;
mod region;
mod session;
mod war;
mod word;
mod words;

#[reducer(init)]
pub fn init(ctx: &ReducerContext) {
    region::seed_regions(ctx);
    war::init_global_war(ctx);

    ctx.db.word_expire_schedule().insert(word::WordExpireSchedule {
        scheduled_id: 0,
        scheduled_at: ScheduledAt::Interval(Duration::from_secs(2)),
    });
    ctx.db.region_tick_schedule().insert(region::RegionTickSchedule {
        scheduled_id: 0,
        scheduled_at: ScheduledAt::Interval(Duration::from_secs(60)),
    });
    ctx.db.war_tick_schedule().insert(war::WarTickSchedule {
        scheduled_id: 0,
        scheduled_at: ScheduledAt::Interval(Duration::from_secs(300)),
    });
}

#[reducer(client_connected)]
pub fn client_connected(_ctx: &ReducerContext) {}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    session::auto_end_battle(ctx);
}
```

- [ ] **Step 3: Verify compile**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -20
```

Expected: zero `^error` lines.

- [ ] **Step 4: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/word.rs game/src/session.rs game/src/lib.rs
git commit -m "feat(typewars): add expire_words_tick scheduled reducer (2s interval)"
```

---

## Task 10: region_tick and end_season

**Files:**
- Modify: `game/src/region.rs`

- [ ] **Step 1: Add scheduler table and reducer**

Append to `game/src/region.rs`:

```rust
use spacetimedb::{reducer, ReducerContext, ScheduledAt, Table};

#[table(name = region_tick_schedule, scheduled(region_tick))]
pub struct RegionTickSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduledAt,
}

#[reducer]
pub fn region_tick(ctx: &ReducerContext, _arg: RegionTickSchedule) -> Result<(), String> {
    let regions: Vec<Region> = ctx.db.region().iter().collect();

    for mut region in regions {
        if region.controlling_legion != -1 {
            continue; // Legion-held, skip regen
        }

        if region.enemy_hp == 0 {
            // Liberation: award to highest-contributing legion
            let winner = winning_legion(&region);
            region.controlling_legion = winner as i8;
            reset_legion_damage(&mut region);
            ctx.db.region().id().update(region);

            if let Some(mut war) = ctx.db.global_war().id().find(1) {
                war.liberated_territories += 1;
                war.enemy_territories = war.enemy_territories.saturating_sub(1);
                ctx.db.global_war().id().update(war.clone());

                if war.liberated_territories >= 20 {
                    end_season(ctx);
                    return Ok(());
                }
            }
        } else {
            // Apply regen (Warden bulwark may halve it)
            let regen = effective_regen(region.regen_rate, region.active_wardens);
            region.enemy_hp = (region.enemy_hp + regen).min(region.enemy_max_hp);
            ctx.db.region().id().update(region);
        }
    }

    Ok(())
}

pub fn end_season(ctx: &ReducerContext) {
    // Advance season counter
    if let Some(mut war) = ctx.db.global_war().id().find(1) {
        war.season += 1;
        war.liberated_territories = 0;
        war.enemy_territories = 25;
        war.season_start = ctx.timestamp;
        ctx.db.global_war().id().update(war);
    }

    // Reset all regions to enemy-held at full HP
    let regions: Vec<Region> = ctx.db.region().iter().collect();
    for mut region in regions {
        region.controlling_legion = -1;
        region.enemy_hp = region.enemy_max_hp;
        reset_legion_damage(&mut region);
        ctx.db.region().id().update(region);
    }

    // Reset all player season_damage
    let players: Vec<crate::player::Player> = ctx.db.player().iter().collect();
    for mut player in players {
        player.season_damage = 0;
        ctx.db.player().identity().update(player);
    }
}
```

`GlobalWar` needs `#[derive(Clone)]` for the `war.clone()` call. Add it to the struct in `war.rs`:

```rust
#[derive(Clone)]
#[table(accessor = global_war, public)]
pub struct GlobalWar { ... }
```

- [ ] **Step 2: Run region tests**

```bash
cd game && cargo test region 2>&1 | tail -10
```

Expected: 2 tests pass.

- [ ] **Step 3: Full compile**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -20
```

Expected: zero `^error` lines.

- [ ] **Step 4: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/region.rs game/src/war.rs
git commit -m "feat(typewars): add region_tick, liberation logic, end_season"
```

---

## Task 11: global_war_tick scheduled reducer

**Files:**
- Modify: `game/src/war.rs`

- [ ] **Step 1: Add scheduler table and reducer**

Append to `game/src/war.rs`:

```rust
use spacetimedb::{reducer, ReducerContext, ScheduledAt, Table};

#[table(name = war_tick_schedule, scheduled(global_war_tick))]
pub struct WarTickSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduledAt,
}

#[reducer]
pub fn global_war_tick(ctx: &ReducerContext, _arg: WarTickSchedule) -> Result<(), String> {
    let war = match ctx.db.global_war().id().find(1) {
        Some(w) => w,
        None => return Ok(()),
    };

    if war.liberated_territories == 0 {
        return Ok(()); // Nothing to invade
    }

    // Enemy invades the liberated region with fewest active defenders
    let target = ctx.db.region()
        .iter()
        .filter(|r| r.controlling_legion >= 0)
        .min_by_key(|r| r.active_wardens);

    if let Some(mut region) = target {
        region.controlling_legion = -1;
        region.enemy_hp = region.enemy_max_hp / 4; // Partial re-invasion
        crate::region::reset_legion_damage(&mut region);
        ctx.db.region().id().update(region);

        let mut w = war;
        w.liberated_territories = w.liberated_territories.saturating_sub(1);
        w.enemy_territories += 1;

        if w.liberated_territories == 0 {
            // Enemy wins — trigger season reset
            ctx.db.global_war().id().update(w);
            crate::region::end_season(ctx);
        } else {
            ctx.db.global_war().id().update(w);
        }
    }

    Ok(())
}
```

- [ ] **Step 2: Full compile**

```bash
cd game && cargo build 2>&1 | grep "^error" | head -20
```

Expected: zero `^error` lines.

- [ ] **Step 3: Run all tests**

```bash
cd game && cargo test 2>&1 | tail -20
```

Expected: all legion, region, word, player, and session tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/src/war.rs
git commit -m "feat(typewars): add global_war_tick enemy invasion reducer"
```

---

## Task 12: Release build + publish + smoke tests

**Files:** none (CLI only)

- [ ] **Step 1: Release build**

```bash
cd game && cargo build --release 2>&1 | tail -5
```

Expected: `Finished release [optimized] target(s)...`

- [ ] **Step 2: Publish module to SpacetimeDB**

```bash
spacetime publish typewars --project-path game/ --server stdb.sastaspace.com
```

Expected: `Published module 'typewars'` (no error lines).

- [ ] **Step 3: Register a test player**

```bash
spacetime call typewars register_player '{"username":"smoketest","legion":0}' --server stdb.sastaspace.com
```

Expected: no error output.

- [ ] **Step 4: Start a battle in region 0**

```bash
spacetime call typewars start_battle '{"region_id":0}' --server stdb.sastaspace.com
```

Expected: no error output.

- [ ] **Step 5: Query spawned words**

```bash
spacetime sql typewars "SELECT id, text, difficulty FROM word" --server stdb.sastaspace.com
```

Expected: 8 rows — 5 easy (difficulty=1), 2 medium (difficulty=2), 1 hard (difficulty=3).

- [ ] **Step 6: Submit a word and verify region damage**

```bash
# Use one of the word texts returned above, e.g. "fire"
spacetime call typewars submit_word '{"session_id":1,"word":"fire"}' --server stdb.sastaspace.com

# Verify enemy_hp decreased
spacetime sql typewars "SELECT id, enemy_hp, damage_0 FROM region WHERE id = 0" --server stdb.sastaspace.com
```

Expected: `enemy_hp` < 50000, `damage_0` > 0 (Ashborn legion is id 0).

- [ ] **Step 7: End battle**

```bash
spacetime call typewars end_battle '{"session_id":1}' --server stdb.sastaspace.com
```

Expected: no error. Word rows for session 1 should be deleted.

- [ ] **Step 8: Verify word cleanup**

```bash
spacetime sql typewars "SELECT COUNT(*) FROM word WHERE session_id = 1" --server stdb.sastaspace.com
```

Expected: `0`.

- [ ] **Step 9: Final commit**

```bash
cd /Users/mkhare/Development/sastaspace
git add game/
git commit -m "feat(typewars): complete TypeWars backend — all reducers and smoke tests passing"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|-----------|
| 5 legions with mechanics | Task 3 (legion.rs) + Tasks 7–8 (submit_word) |
| Ashborn 3× burst at streak 10 | Task 3 + Task 8 |
| Codex rare word at ≥90% accuracy | Task 3 + Task 8 |
| Wardens bulwark (3+ → half regen) | Task 4 (effective_regen) + Task 10 (region_tick) |
| Surge 5× multiplier cap | Task 3 (multiplier_cap) |
| Solari grace window | **Not implemented** — requires a client-side timing signal. Deferred to frontend Task. No backend change needed. |
| 25 regions, 3 tiers, seeded at init | Task 4 (seed_regions) |
| Word rain + 5s expiry | Tasks 6, 9 |
| Streak + multiplier | Task 8 (submit_word) |
| Difficulty distribution (5e/2m/1h per 8) | Task 6 (difficulty_for_slot) |
| Contribution race → winning legion | Task 4 (winning_legion) + Task 10 (region_tick) |
| Enemy regen per tick | Task 10 |
| Enemy invasion (global_war_tick) | Task 11 |
| Season reset (end_season) | Task 10 |
| client_disconnected cleanup | Task 9 (lib.rs) + Task 4 (auto_end_battle) |
| Anti-cheat min submission interval | **Not implemented** — deferred. Low risk for initial launch. Add `last_submit_at: Timestamp` to BattleSession + check `(ctx.timestamp - last_submit_at) >= 100ms` in submit_word if needed later. |

**Placeholder scan:** None found — all steps include actual code.

**Type consistency:** `BattleSession.words_spawned: u32` used consistently in Tasks 4, 7, 8, 9. `spawn_words(ctx, session_id: u64, spawn_start: u32, count: u32, inject_rare: bool)` signature identical across all call sites. `controlling_legion: i8` (-1 for enemy, 0–4 for legions) consistent throughout.
