# TypeWars — Backend & System Design

**Date:** 2026-04-25
**Scope:** SpacetimeDB game module only. No frontend, no visuals.

---

## Overview

TypeWars is a cooperative PvE typing MMO where all players unite to reclaim a galactic territory map from a global enemy force. Players join one of five Legions, each with a distinct combat mechanic. Territory is won by whichever Legion deals the most cumulative damage during a liberation — pure contribution race, no direct Legion-vs-Legion combat.

The core typing loop: words appear in batches, you type them before they expire (5s window), each typed word deals damage to the enemy controlling the region you're fighting in. Streak multipliers amplify damage; missing a word breaks your streak.

---

## The Five Legions

Inspired by Hindu cosmic archetypes, renamed for the game universe:

| ID | Name | Source | Mechanic |
|----|------|--------|----------|
| 0 | **Ashborn** | Shiva (destruction) | Every 10-word streak: next word deals 3× damage, streak counter resets |
| 1 | **The Codex** | Brahma (creation) | Maintain ≥90% session accuracy → rare high-damage words occasionally spawn |
| 2 | **Wardens** | Vishnu (preservation) | When ≥3 Wardens are active in a region, enemy regen rate is halved |
| 3 | **Surge** | Shakti (power) | Multiplier cap raised from 3.0× to 5.0× |
| 4 | **Solari** | Surya (light) | Word difficulty tier always shown; 500ms grace window to backspace-correct a typo |

Legion is chosen once at registration and is permanent.

---

## Territory Map

25 regions total, seeded at `init`. Enemy controls all at season start.

| Tier | Count | enemy_max_hp | regen_rate/tick |
|------|-------|-------------|-----------------|
| 1 — Outer | 10 | 50,000 | 200 |
| 2 — Middle | 10 | 100,000 | 500 |
| 3 — Core | 5 | 250,000 | 1,500 |

A season ends when ≥80% of regions are liberated or 30 days elapse. The Legion holding the most territories at season end wins the season banner.

---

## SpacetimeDB Schema

New module: `game/` in the monorepo root. Separate from the sastaspace module.

```rust
// Player — one row per registered user
#[table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    pub identity: Identity,
    pub username: String,
    pub legion: u8,
    pub total_damage: u64,
    pub season_damage: u64,    // reset each season
    pub best_wpm: u32,
    pub joined_at: Timestamp,
}

// Region — 25 rows seeded at init
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
    // Per-legion damage tally for this liberation cycle
    pub damage_0: u64,
    pub damage_1: u64,
    pub damage_2: u64,
    pub damage_3: u64,
    pub damage_4: u64,
    pub active_wardens: u32,      // live player count, for Bulwark mechanic
}

// BattleSession — one row per active player-in-region
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
    pub multiplier: f32,          // 1.0 → 3.0 (5.0 for Surge)
    pub accuracy_hits: u32,
    pub accuracy_misses: u32,
    pub damage_dealt: u64,
    pub active: bool,
}

// Word — current batch (≤8 rows per session)
#[table(accessor = word, public)]
pub struct Word {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    #[index(btree)]
    pub session_id: u64,
    pub text: String,
    pub difficulty: u8,           // 1=easy 2=medium 3=hard 4=rare
    pub base_damage: u64,
    pub spawned_at: Timestamp,
    pub expires_at: Timestamp,    // spawned_at + 5s
}

// GlobalWar — singleton (id = 1)
#[table(accessor = global_war, public)]
pub struct GlobalWar {
    #[primary_key]
    pub id: u32,
    pub season: u32,
    pub enemy_territories: u32,
    pub liberated_territories: u32,
    pub season_start: Timestamp,
}

// Scheduler tables (SpacetimeDB 2.x pattern)
#[table(name = word_expire_schedule, scheduled(expire_words_tick))]
pub struct WordExpireSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduledAt,
}

#[table(name = region_tick_schedule, scheduled(region_tick))]
pub struct RegionTickSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduledAt,
}

#[table(name = war_tick_schedule, scheduled(global_war_tick))]
pub struct WarTickSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_Id: u64,
    pub scheduled_at: ScheduledAt,
}
```

---

## Reducers

### Player reducers

**`register_player(username: String, legion: u8)`**
- Reject if `Player` row already exists for `ctx.sender()`
- Reject if legion > 4
- Insert Player, increment GlobalWar (no-op for now)

**`start_battle(region_id: u32)`**
- Reject if player already has an active BattleSession
- Create BattleSession (streak=0, multiplier=1.0, active=true)
- If player.legion == 2 (Wardens): increment `region.active_wardens`
- Spawn initial batch of 8 words (see Word Spawning below)

**`submit_word(session_id: u64, word: String)`** — the hot path
1. Verify `ctx.sender() == session.player_identity`
2. Find Word where `session_id = session_id AND text = word AND expires_at > ctx.timestamp`
3. **Miss path** (not found or expired): `accuracy_misses++`, streak → 0, multiplier → 1.0, return Ok
4. **Hit path:**
   - `accuracy_hits++`, `streak++`
   - `multiplier = min(cap, 1.0 + streak as f32 * 0.25)` where cap = 5.0 for Surge, 3.0 otherwise
   - `damage = word.base_damage as f32 × multiplier`
   - **Ashborn bonus:** if `streak % 10 == 0` → `damage *= 3.0`, streak resets to 0
   - **Codex bonus:** if `accuracy_hits / (accuracy_hits + accuracy_misses) >= 0.90` → 15% chance to inject a rare word (difficulty=4, base_damage=100) into next spawn
   - Subtract damage from `region.enemy_hp` (floor at 0)
   - Add damage to `region.damage_{player.legion}`
   - Add damage to `session.damage_dealt`
   - Delete matched Word row
   - Spawn 1 replacement word immediately

**`end_battle(session_id: u64)`**
- Verify caller owns session
- Set `session.active = false`
- If Warden: decrement `region.active_wardens`
- Delete all remaining Word rows for this session
- Update `player.total_damage`, `player.season_damage`

### Scheduled reducers

**`expire_words_tick`** — every 2 seconds
- Delete all Word rows where `expires_at < ctx.timestamp`
- For each orphaned session (word deleted but session active), reset streak/multiplier and spawn replacement
- Spawn replacement: for each active session with fewer than 4 words remaining, fill back to 8

**`region_tick`** — every 60 seconds
- For each region where `controlling_legion == -1` (enemy-held):
  - Apply Warden Bulwark: if `active_wardens >= 3` → `regen = regen_rate / 2` else `regen = regen_rate`
  - `enemy_hp = min(enemy_max_hp, enemy_hp + regen)`
- For each region where `enemy_hp == 0`:
  - Find `max(damage_0..damage_4)` → winning legion
  - Set `controlling_legion = winner`
  - Increment `GlobalWar.liberated_territories`; decrement `enemy_territories`
  - Reset all `damage_N` to 0 for next cycle
- Check win condition: if `liberated_territories >= 20` (80% of 25) → call `end_season()`

**`global_war_tick`** — every 300 seconds
- Enemy counter-invades: find the liberated region with lowest `active_wardens` (fewest defenders)
- Set `controlling_legion = -1`, restore `enemy_hp = enemy_max_hp / 4` (partial invasion)
- Decrement `GlobalWar.liberated_territories`
- If `liberated_territories == 0`: enemy wins, call `end_season()`

**`end_season()` (internal helper, not a public reducer)**
- Find legion with most currently-controlled regions → season winner
- Increment `GlobalWar.season`
- Reset all regions to enemy-held
- Reset all player `season_damage` to 0
- Reset scheduler intervals

---

## Word Spawning

Static word lists embedded in the module binary:

| Difficulty | Char range | Count | base_damage |
|-----------|-----------|-------|-------------|
| 1 — Easy | 3–5 | 500 words | 10 |
| 2 — Medium | 6–8 | 500 words | 25 |
| 3 — Hard | 9–13 | 200 words | 50 |
| 4 — Rare (Codex) | 8–12 complex | 50 words | 100 |

**Selection:** `word_index = (session_id ^ words_typed_count ^ timestamp_secs) % list_len`
Deterministic, reproducible, no stored seed needed. Difficulty distribution per batch: 5 easy, 2 medium, 1 hard.

---

## Module File Structure

```
game/
  Cargo.toml              (spacetimedb = "2.1")
  src/
    lib.rs                init, lifecycle reducers, scheduler setup
    player.rs             Player table, register_player
    region.rs             Region table, region_tick, end_season
    session.rs            BattleSession, start_battle, end_battle
    word.rs               Word table, submit_word, spawn_words, expire_words_tick
    war.rs                GlobalWar, global_war_tick
    legion.rs             Legion bonus logic (pure functions, no DB access)
    words/
      mod.rs
      easy.rs
      medium.rs
      hard.rs
      rare.rs
```

---

## Data Flow Summary

```
Client                    SpacetimeDB
  |                           |
  |-- start_battle(region) -->|-- insert BattleSession
  |                           |-- insert 8 Words
  |<-- subscription update ---|
  |
  |-- submit_word(id, "cat") ->|-- find Word, compute damage
  |                            |-- update Region.enemy_hp
  |                            |-- update Region.damage_N
  |                            |-- delete Word, spawn 1 new
  |<-- subscription update  --|
  |
  |                           |-- [60s tick] region_tick
  |                           |-- enemy regen / liberation check
  |<-- subscription update ---|-- Region.controlling_legion changes
```

Clients subscribe to: their active `BattleSession`, `Word` rows for their session, and the `Region` they're fighting in. Global leaderboard: subscribe to `Region` table and `GlobalWar`.

---

## UI / Design Handoff

This section exists so a designer can build the frontend without needing to read the backend code.

### Screens

**1. Legion Select** (one-time, on registration)
- Show all 5 legions with name, mechanic description, and thematic colour
- Single selection, permanent — make it feel weighty
- Legion colours (suggestion): Ashborn=red-orange, Codex=gold, Wardens=teal, Surge=purple, Solari=yellow-white

**2. War Map** (lobby / between battles)
- 25 regions arranged as a spatial map (grid or hex tiles)
- Each region shows: name, tier (1-3), controlling faction (legion colour or enemy red), HP bar
- Active player count per region as a subtle indicator
- Click a region → enter Battle screen
- Global stats bar: liberated X/25, season timer, winning legion

**3. Battle Screen** (active session)
- Central input field — always focused, no click needed
- 8 word "lanes" or floating words, each with a 5s countdown bar
- Streak counter + multiplier badge (glows on Ashborn burst, pulses on Surge overdrive)
- Region HP bar at top, showing enemy HP and per-legion colour bars underneath (contribution race visualisation)
- Legion-specific UI hint: Codex shows accuracy %, Solari shows difficulty tier on each word

**4. Region Liberated Splash**
- Fullscreen moment when a region flips — shows winning legion, new territory count, top 3 contributors

**5. Leaderboard / Season Tab**
- Per-legion damage totals, regions held, season rank
- Personal stats: total damage, best WPM, season damage

### Data the UI Reads (SpacetimeDB subscriptions)

| Screen | Subscribed tables |
|--------|-------------------|
| War Map | `region` (all rows), `global_war` |
| Battle | `battle_session` (own row), `word` (own session), `region` (active region) |
| Leaderboard | `player` (all), `region` (all), `global_war` |

### Reducers the UI Calls

| Action | Reducer |
|--------|---------|
| First launch | `register_player(username, legion)` |
| Enter region | `start_battle(region_id)` |
| Type a word | `submit_word(session_id, word)` |
| Leave region | `end_battle(session_id)` |

### SpacetimeDB SDK Notes (for frontend dev)

- SDK: `@clockworklabs/spacetimedb-sdk` v2.1 (already used in `apps/notes`)
- Pattern: `useReducer` hooks from SDK; subscribe via `DbConnection`
- Auth: reuse existing identity from the main sastaspace session or generate a fresh one for the game module
- Module host: same stdb.sastaspace.com, different module name (`typewars`)

---

## Open Questions for Implementation

1. **Scheduled reducer syntax** — SpacetimeDB 2.1 scheduled reducer API needs verification against latest docs; the `#[table(scheduled(fn))]` pattern may have changed.
2. **Word list source** — use a curated game-appropriate word list (not generic dictionary) to match the aesthetic.
3. **Anti-cheat threshold** — `submit_word` could add a minimum submission interval (e.g., reject if two submissions < 100ms apart) to prevent scripted bots.
4. **Session cleanup** — on `client_disconnected`, auto-call `end_battle` for any active session owned by that identity.
