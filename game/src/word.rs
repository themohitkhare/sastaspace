use spacetimedb::{table, Timestamp, ReducerContext, Table, reducer, ScheduleAt};
use std::collections::HashSet;
use crate::words;
use crate::legion;
use crate::session::battle_session;
use crate::player::player;
use crate::region::region;

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
    let expires_at = Timestamp::from_micros_since_unix_epoch(
        ts.to_micros_since_unix_epoch() + 5_000_000,
    );

    for i in 0..count {
        let slot = spawn_start + i;
        let (difficulty, base_damage) = if inject_rare && i == 0 {
            (4u8, 100u64)
        } else {
            let d = difficulty_for_slot(slot);
            let dmg = match d { 1 => 10, 2 => 25, 3 => 50, 4 => 100, _ => 10 };
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
}

// ── Scheduled reducer: expire words every 2 seconds ──────────────────────────

pub fn init_word_expire_schedule(ctx: &ReducerContext) {
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

    let expired: Vec<Word> = ctx
        .db
        .word()
        .iter()
        .filter(|w| w.expires_at.to_micros_since_unix_epoch() <= ts_now)
        .collect();

    let mut affected: HashSet<u64> = HashSet::new();
    for w in expired {
        affected.insert(w.session_id);
        ctx.db.word().id().delete(w.id);
    }

    for sid in &affected {
        if let Some(mut s) = ctx.db.battle_session().id().find(*sid) {
            if s.active {
                s.streak = 0;
                s.multiplier = 1.0;
                ctx.db.battle_session().id().update(s);
            }
        }
    }

    let active: Vec<crate::session::BattleSession> = ctx
        .db
        .battle_session()
        .iter()
        .filter(|s| s.active)
        .collect();

    for s in active {
        let word_count = ctx.db.word().session_id().filter(&s.id).count();
        if word_count < 4 {
            let needed = 8usize.saturating_sub(word_count) as u32;
            if needed == 0 { continue; }
            let session_id = s.id;
            let spawn_start = s.words_spawned;
            let mut updated_s = s;
            updated_s.words_spawned += needed;
            ctx.db.battle_session().id().update(updated_s);
            spawn_words(ctx, session_id, spawn_start, needed, false);
        }
    }

    Ok(())
}
