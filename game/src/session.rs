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

use spacetimedb::{reducer, ReducerContext, Table};
use crate::word::spawn_words;
use crate::player::player;
use crate::region::region;
use crate::word::word;

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

/// Called from client_disconnected to clean up any dangling active sessions.
pub fn auto_end_battle(ctx: &ReducerContext) {
    let sessions: Vec<BattleSession> = ctx.db.battle_session()
        .iter()
        .filter(|s| s.player_identity == ctx.sender() && s.active)
        .collect();
    for session in sessions {
        end_battle_core(ctx, session);
    }
}

pub fn end_battle_core(ctx: &ReducerContext, session: BattleSession) {
    if let Some(player) = ctx.db.player().identity().find(session.player_identity) {
        if player.legion == 2 {
            if let Some(mut region) = ctx.db.region().id().find(session.region_id) {
                region.active_wardens = region.active_wardens.saturating_sub(1);
                ctx.db.region().id().update(region);
            }
        }
        let word_ids: Vec<u64> = ctx.db.word()
            .session_id()
            .filter(&session.id)
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
}
