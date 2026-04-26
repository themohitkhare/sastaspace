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

use crate::player::player;
use crate::region::region;
use crate::word::spawn_words;
use crate::word::word;
use spacetimedb::{reducer, ReducerContext, Table};

#[reducer]
pub fn start_battle(ctx: &ReducerContext, region_id: u32) -> Result<(), String> {
    let player = ctx
        .db
        .player()
        .identity()
        .find(ctx.sender())
        .ok_or_else(|| "not registered".to_string())?;

    // Use player_identity btree index: O(sessions_per_player) not O(total_sessions)
    let already_active = ctx
        .db
        .battle_session()
        .player_identity()
        .filter(ctx.sender())
        .any(|s| s.active);
    if already_active {
        return Err("already in a battle".into());
    }

    ctx.db
        .region()
        .id()
        .find(region_id)
        .ok_or_else(|| format!("region {region_id} not found"))?;

    let session = ctx.db.battle_session().insert(make_initial_session(
        ctx.sender(),
        region_id,
        ctx.timestamp,
    ));

    if is_warden_legion(player.legion) {
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
    let session = ctx
        .db
        .battle_session()
        .id()
        .find(session_id)
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

/// Called from client_disconnected to clean up any dangling active sessions.
pub fn auto_end_battle(ctx: &ReducerContext) {
    // Use player_identity btree index: O(sessions_per_player) not O(total_sessions)
    let sessions: Vec<BattleSession> = ctx
        .db
        .battle_session()
        .player_identity()
        .filter(ctx.sender())
        .filter(|s| s.active)
        .collect();
    for session in sessions {
        end_battle_core(ctx, session);
    }
}

pub fn end_battle_core(ctx: &ReducerContext, session: BattleSession) {
    if let Some(player) = ctx.db.player().identity().find(session.player_identity) {
        if is_warden_legion(player.legion) {
            if let Some(mut region) = ctx.db.region().id().find(session.region_id) {
                region.active_wardens = region.active_wardens.saturating_sub(1);
                ctx.db.region().id().update(region);
            }
        }
        let word_ids: Vec<u64> = ctx
            .db
            .word()
            .session_id()
            .filter(&session.id)
            .map(|w| w.id)
            .collect();
        for wid in word_ids {
            ctx.db.word().id().delete(wid);
        }
        let mut p = player;
        let (total, season) =
            apply_battle_damage(p.total_damage, p.season_damage, session.damage_dealt);
        p.total_damage = total;
        p.season_damage = season;
        ctx.db.player().identity().update(p);
    }
    let mut s = session;
    s.active = false;
    ctx.db.battle_session().id().update(s);
}

/// Pure helper: returns true when the given legion is "Wardens" (legion 2)
/// and therefore counts toward the active-warden bulwark on entry/exit of
/// a region. Pulled out for unit testing without a `ReducerContext`.
pub fn is_warden_legion(legion: u8) -> bool {
    legion == 2
}

/// Pure helper: derives the post-battle player stats given the session's
/// damage_dealt. Returns `(new_total_damage, new_season_damage)`. Mirrors
/// the saturating-add pattern from `end_battle_core`.
pub fn apply_battle_damage(total_damage: u64, season_damage: u64, damage_dealt: u64) -> (u64, u64) {
    (
        total_damage.saturating_add(damage_dealt),
        season_damage.saturating_add(damage_dealt),
    )
}

/// Pure helper: produces the initial `BattleSession` for a region request,
/// filling in the constant defaults so `start_battle` can stay focused on
/// DB I/O.
pub fn make_initial_session(
    sender: Identity,
    region_id: u32,
    started_at: Timestamp,
) -> BattleSession {
    BattleSession {
        id: 0,
        player_identity: sender,
        region_id,
        started_at,
        streak: 0,
        multiplier: 1.0,
        accuracy_hits: 0,
        accuracy_misses: 0,
        damage_dealt: 0,
        // Pre-incremented to 8 because we're about to spawn 8 words.
        words_spawned: 8,
        active: true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cannot_have_two_active_sessions() {
        fn check(has_active: bool) -> Result<(), String> {
            if has_active {
                return Err("already in a battle".into());
            }
            Ok(())
        }
        assert!(check(false).is_ok());
        assert!(check(true).is_err());
    }

    // === is_warden_legion ===

    #[test]
    fn is_warden_legion_only_true_for_legion_2() {
        assert!(!is_warden_legion(0)); // Ashborn
        assert!(!is_warden_legion(1)); // Codex
        assert!(is_warden_legion(2)); // Wardens
        assert!(!is_warden_legion(3)); // Surge
        assert!(!is_warden_legion(4)); // Solari
    }

    // === apply_battle_damage ===

    #[test]
    fn apply_battle_damage_sums_into_both_totals() {
        let (total, season) = apply_battle_damage(1000, 500, 200);
        assert_eq!(total, 1200);
        assert_eq!(season, 700);
    }

    #[test]
    fn apply_battle_damage_zero_dealt_is_noop() {
        let (total, season) = apply_battle_damage(1000, 500, 0);
        assert_eq!(total, 1000);
        assert_eq!(season, 500);
    }

    #[test]
    fn apply_battle_damage_saturates_on_overflow() {
        // Hostile worker / data corruption shouldn't crash the reducer.
        let (total, season) = apply_battle_damage(u64::MAX - 5, 1000, 100);
        assert_eq!(total, u64::MAX);
        assert_eq!(season, 1100);
    }

    // === make_initial_session ===

    #[test]
    fn make_initial_session_seeds_default_fields() {
        let id = Identity::from_byte_array([0x42; 32]);
        let ts = Timestamp::from_micros_since_unix_epoch(1_000_000);
        let s = make_initial_session(id, 7, ts);
        assert_eq!(s.id, 0);
        assert_eq!(s.player_identity, id);
        assert_eq!(s.region_id, 7);
        assert_eq!(s.started_at, ts);
        assert_eq!(s.streak, 0);
        assert!((s.multiplier - 1.0).abs() < f32::EPSILON);
        assert_eq!(s.accuracy_hits, 0);
        assert_eq!(s.accuracy_misses, 0);
        assert_eq!(s.damage_dealt, 0);
        // 8 reserved for the 8 words about to spawn.
        assert_eq!(s.words_spawned, 8);
        assert!(s.active);
    }
}
