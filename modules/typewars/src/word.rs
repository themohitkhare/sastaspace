use crate::legion;
use crate::player::player;
use crate::region::region;
use crate::session::battle_session;
use crate::words;
use spacetimedb::{reducer, table, ReducerContext, ScheduleAt, Table, Timestamp};

#[table(accessor = word, public)]
pub struct Word {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    #[index(btree)]
    pub session_id: u64,
    pub text: String,
    pub difficulty: u8, // 1=easy 2=medium 3=hard 4=rare
    pub base_damage: u64,
    pub spawned_at: Timestamp,
    pub expires_at: Timestamp,
}

pub fn apply_miss(_streak: u32, _multiplier: f32) -> (u32, f32) {
    (0, 1.0)
}

pub fn apply_hit(streak: u32, cap: f32) -> (u32, f32) {
    let new_streak = streak + 1;
    (new_streak, legion::compute_multiplier(new_streak, cap))
}

/// Pure helper: returns true if a candidate word matches the live-word
/// criteria used in `submit_word`'s scan. Centralised so tests can pin
/// the three conjuncts (session id, text equality, not-yet-expired).
pub fn is_word_match(
    candidate_session: u64,
    candidate_text: &str,
    candidate_expires_micros: i64,
    target_session: u64,
    target_text: &str,
    now_micros: i64,
) -> bool {
    candidate_session == target_session
        && candidate_text == target_text
        && candidate_expires_micros > now_micros
}

/// Pure helper: applies a hit's damage to a region's enemy_hp via
/// saturating subtraction. Pulled out for unit tests.
pub fn apply_damage_to_region(enemy_hp: u64, damage: u64) -> u64 {
    enemy_hp.saturating_sub(damage)
}

/// Pure helper: produces the (difficulty, base_damage) pair for a spawn
/// slot, accounting for Codex rare-injection. Pulled out of `spawn_words`
/// so the slot→difficulty + injection logic can be unit tested without a
/// `ReducerContext`.
pub fn slot_difficulty_and_damage(slot: u32, inject_rare: bool, is_first: bool) -> (u8, u64) {
    if inject_rare && is_first {
        (4u8, 100u64)
    } else {
        let d = difficulty_for_slot(slot);
        let dmg = match d {
            1 => 10,
            2 => 25,
            3 => 50,
            4 => 100,
            _ => 10,
        };
        (d, dmg)
    }
}

/// Pure helper: returns the spawn count needed to refill an active session
/// to 8 visible words after expiries. Mirrors the ceiling logic in
/// `expire_words_tick`. Returns 0 when the session is already at or above
/// the floor.
pub fn refill_count(visible_words: usize) -> u32 {
    if visible_words >= 4 {
        0
    } else {
        8usize.saturating_sub(visible_words) as u32
    }
}

/// Pure helper: computes the `expires_at` micros for a freshly spawned
/// word, which is `spawned_at + 5s` per the design spec. Pulled out so the
/// constant lives in one named place and is independently testable.
pub const WORD_LIFETIME_MICROS: i64 = 5_000_000;
pub fn word_expires_at_micros(spawned_at_micros: i64) -> i64 {
    spawned_at_micros + WORD_LIFETIME_MICROS
}

#[reducer]
pub fn submit_word(ctx: &ReducerContext, session_id: u64, word: String) -> Result<(), String> {
    let mut session = ctx
        .db
        .battle_session()
        .id()
        .find(session_id)
        .ok_or_else(|| "session not found".to_string())?;
    if session.player_identity != ctx.sender() {
        return Err("not your session".into());
    }
    if !session.active {
        return Err("session ended".into());
    }

    let player = ctx
        .db
        .player()
        .identity()
        .find(ctx.sender())
        .ok_or_else(|| "player not found".to_string())?;

    let ts_now = ctx.timestamp.to_micros_since_unix_epoch();

    // Find matching live word in this session — use session_id btree index (O(8) not O(8N))
    let hit: Option<Word> = ctx.db.word().session_id().filter(&session_id).find(|w| {
        is_word_match(
            w.session_id,
            &w.text,
            w.expires_at.to_micros_since_unix_epoch(),
            session_id,
            &word,
            ts_now,
        )
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
        reg.enemy_hp = apply_damage_to_region(reg.enemy_hp, damage);
        crate::region::add_legion_damage(&mut reg, player.legion, damage);
        ctx.db.region().id().update(reg);
    } else {
        // Region not found - this shouldn't happen, but we'll allow the word match
    }

    // Delete matched word
    ctx.db.word().id().delete(hit_word.id);

    // Codex rare word injection check (~14% when accuracy >= 90%)
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

pub fn difficulty_for_slot(slot: u32) -> u8 {
    match slot % 8 {
        0..=4 => 1,
        5..=6 => 2,
        _ => 3,
    }
}

pub fn select_word(
    difficulty: u8,
    session_id: u64,
    spawn_count: u32,
    timestamp_secs: u64,
) -> &'static str {
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
    let expires_at = Timestamp::from_micros_since_unix_epoch(word_expires_at_micros(
        ts.to_micros_since_unix_epoch(),
    ));

    for i in 0..count {
        let slot = spawn_start + i;
        let (difficulty, base_damage) = slot_difficulty_and_damage(slot, inject_rare, i == 0);

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
        assert_eq!(select_word(1, 42, 0, 1000), select_word(1, 42, 0, 1000));
    }

    #[test]
    fn word_selection_varies_across_nonces() {
        let words: std::collections::HashSet<_> =
            (0u64..20).map(|n| select_word(1, 1, 0, n)).collect();
        assert!(words.len() > 1);
    }

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
        let (s, m) = apply_hit(12, 3.0);
        assert_eq!(s, 13);
        assert!((m - 3.0).abs() < 0.001);
    }

    // === slot_difficulty_and_damage ===

    #[test]
    fn slot_difficulty_and_damage_easy_slot() {
        // Slot 0 → easy (difficulty 1, 10 damage).
        assert_eq!(slot_difficulty_and_damage(0, false, false), (1, 10));
    }

    #[test]
    fn slot_difficulty_and_damage_medium_slot() {
        // Slot 5 → medium (2, 25 damage).
        assert_eq!(slot_difficulty_and_damage(5, false, false), (2, 25));
    }

    #[test]
    fn slot_difficulty_and_damage_hard_slot() {
        // Slot 7 → hard (3, 50 damage).
        assert_eq!(slot_difficulty_and_damage(7, false, false), (3, 50));
    }

    #[test]
    fn slot_difficulty_and_damage_codex_first_word_is_rare() {
        // inject_rare + first → always rare (difficulty 4, 100 damage)
        // regardless of slot.
        assert_eq!(slot_difficulty_and_damage(0, true, true), (4, 100));
        assert_eq!(slot_difficulty_and_damage(7, true, true), (4, 100));
    }

    #[test]
    fn slot_difficulty_and_damage_codex_only_affects_first_in_burst() {
        // inject_rare flag set but is_first=false → falls through to slot.
        assert_eq!(slot_difficulty_and_damage(0, true, false), (1, 10));
        assert_eq!(slot_difficulty_and_damage(7, true, false), (3, 50));
    }

    // === refill_count ===

    #[test]
    fn refill_count_spawns_to_eight_when_below_floor() {
        // Visible 0 → spawn 8.
        assert_eq!(refill_count(0), 8);
        // Visible 1 → spawn 7.
        assert_eq!(refill_count(1), 7);
        // Visible 3 → spawn 5.
        assert_eq!(refill_count(3), 5);
    }

    #[test]
    fn refill_count_zero_at_or_above_floor() {
        assert_eq!(refill_count(4), 0);
        assert_eq!(refill_count(5), 0);
        assert_eq!(refill_count(8), 0);
        assert_eq!(refill_count(100), 0);
    }

    // === word_expires_at_micros ===

    #[test]
    fn word_lifetime_is_five_seconds() {
        assert_eq!(WORD_LIFETIME_MICROS, 5_000_000);
    }

    #[test]
    fn word_expires_at_micros_adds_lifetime() {
        assert_eq!(word_expires_at_micros(0), 5_000_000);
        assert_eq!(word_expires_at_micros(1_000_000), 6_000_000);
    }

    // === select_word integration ===

    #[test]
    fn select_word_routes_unknown_difficulty_to_easy_pool() {
        // The fallback arm (difficulty 5..=255) returns from the easy
        // pool — pin that behaviour so a future "hyper" tier doesn't
        // accidentally crash.
        let _w = select_word(7, 1, 0, 0);
        // No panic = pass.
    }

    #[test]
    fn select_word_routes_each_known_difficulty() {
        // Each branch must return a non-empty &'static str.
        for d in 1u8..=4 {
            let w = select_word(d, 1, 0, 0);
            assert!(!w.is_empty(), "difficulty {d} returned empty word");
        }
    }

    // === is_word_match ===

    #[test]
    fn is_word_match_all_three_conjuncts_must_hold() {
        // happy path: same session, same text, not yet expired.
        assert!(is_word_match(1, "fire", 1_000, 1, "fire", 500));
    }

    #[test]
    fn is_word_match_rejects_wrong_session_id() {
        assert!(!is_word_match(1, "fire", 1_000, 2, "fire", 500));
    }

    #[test]
    fn is_word_match_rejects_wrong_text() {
        assert!(!is_word_match(1, "fire", 1_000, 1, "ice", 500));
    }

    #[test]
    fn is_word_match_rejects_expired_word() {
        // ts_now == expires → strictly past, not allowed.
        assert!(!is_word_match(1, "fire", 1_000, 1, "fire", 1_000));
        // ts_now > expires → also rejected.
        assert!(!is_word_match(1, "fire", 1_000, 1, "fire", 1_500));
    }

    #[test]
    fn is_word_match_text_compare_is_case_sensitive() {
        // The reducer's strict-equal trims nothing — case matters.
        assert!(!is_word_match(1, "FIRE", 1_000, 1, "fire", 500));
    }

    // === apply_damage_to_region ===

    #[test]
    fn apply_damage_to_region_subtracts_normally() {
        assert_eq!(apply_damage_to_region(1000, 100), 900);
    }

    #[test]
    fn apply_damage_to_region_saturates_at_zero() {
        // Damage exceeds HP — clamp to 0 rather than underflow.
        assert_eq!(apply_damage_to_region(50, 200), 0);
    }

    #[test]
    fn apply_damage_to_region_zero_damage_is_noop() {
        assert_eq!(apply_damage_to_region(1000, 0), 1000);
    }
}

// ── Scheduled reducer: expire words every 2 seconds ──────────────────────────

pub fn init_word_expire_schedule(ctx: &ReducerContext) {
    if ctx.db.word_expire_schedule().iter().next().is_some() {
        return;
    }
    ctx.db.word_expire_schedule().insert(WordExpireSchedule {
        scheduled_id: 0,
        scheduled_at: ScheduleAt::from(std::time::Duration::from_secs(2)),
    });
}

#[table(accessor = word_expire_schedule, scheduled(expire_words_tick))]
pub struct WordExpireSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduleAt,
}

#[reducer]
pub fn expire_words_tick(ctx: &ReducerContext, _arg: WordExpireSchedule) -> Result<(), String> {
    let ts_now = ctx.timestamp.to_micros_since_unix_epoch();

    // Iterate active sessions once (unavoidable — no index on `active` bool).
    // For each session use the session_id btree index to scan only that session's
    // words (O(8) per session) rather than doing a global word table scan (O(8N)).
    let active: Vec<crate::session::BattleSession> = ctx
        .db
        .battle_session()
        .iter()
        .filter(|s| s.active)
        .collect();

    for s in active {
        // Collect expired words for this session via indexed lookup.
        let expired_ids: Vec<u64> = ctx
            .db
            .word()
            .session_id()
            .filter(&s.id)
            .filter(|w| w.expires_at.to_micros_since_unix_epoch() <= ts_now)
            .map(|w| w.id)
            .collect();

        let had_expiry = !expired_ids.is_empty();
        for wid in expired_ids {
            ctx.db.word().id().delete(wid);
        }

        // Reset streak on expiry (re-fetch to get fresh state after word deletes).
        let sid = s.id;
        if had_expiry {
            if let Some(mut fresh) = ctx.db.battle_session().id().find(sid) {
                fresh.streak = 0;
                fresh.multiplier = 1.0;
                ctx.db.battle_session().id().update(fresh);
            } else {
                continue;
            }
        }

        // Refill words to keep 8 visible — use indexed word count for this session.
        let word_count = ctx.db.word().session_id().filter(&sid).count();
        let needed = refill_count(word_count);
        if needed == 0 {
            continue;
        }
        if let Some(mut sess) = ctx.db.battle_session().id().find(sid) {
            let spawn_start = sess.words_spawned;
            sess.words_spawned += needed;
            ctx.db.battle_session().id().update(sess);
            spawn_words(ctx, sid, spawn_start, needed, false);
        }
    }

    Ok(())
}
