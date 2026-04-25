use spacetimedb::{table, Timestamp, ReducerContext, Table};

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
    let expires_at = Timestamp::from_micros_since_unix_epoch(
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
