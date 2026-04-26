use spacetimedb::{reducer, table, ReducerContext, ScheduleAt, Table, Timestamp};
use std::time::Duration;
use crate::region::{region, end_season, reset_legion_damage};

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
    if ctx.db.global_war().id().find(1).is_some() {
        return;
    }
    ctx.db.global_war().insert(GlobalWar {
        id: 1,
        season: 1,
        enemy_territories: 25,
        liberated_territories: 0,
        season_start: ctx.timestamp,
    });
}

#[table(accessor = war_tick_schedule, scheduled(global_war_tick))]
pub struct WarTickSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduleAt,
}

#[reducer]
pub fn global_war_tick(ctx: &ReducerContext, _arg: WarTickSchedule) -> Result<(), String> {
    let Some(war) = ctx.db.global_war().id().find(1) else { return Ok(()); };

    if war.liberated_territories == 0 {
        return Ok(());
    }

    let target = ctx.db.region()
        .iter()
        .filter(|r| r.controlling_legion >= 0)
        .min_by_key(|r| r.active_wardens);

    let Some(mut victim) = target else { return Ok(()); };

    victim.controlling_legion = -1;
    victim.enemy_hp = fallen_region_hp(victim.enemy_max_hp);
    reset_legion_damage(&mut victim);
    ctx.db.region().id().update(victim);

    let (liberated_after, enemy_after) =
        apply_war_tick(war.liberated_territories, war.enemy_territories);
    let mut w = war;
    w.liberated_territories = liberated_after;
    w.enemy_territories = enemy_after;
    ctx.db.global_war().id().update(w);

    if liberated_after == 0 {
        end_season(ctx);
    }

    Ok(())
}

pub fn init_war_tick_schedule(ctx: &ReducerContext) {
    if ctx.db.war_tick_schedule().iter().next().is_some() { return; }
    ctx.db.war_tick_schedule().insert(WarTickSchedule {
        scheduled_id: 0,
        scheduled_at: ScheduleAt::from(Duration::from_secs(300)),
    });
}

/// Pure helper: produces the post-war-tick `(liberated_after, enemy_after)`
/// pair given the before-tick values. The war tick decrements liberated by
/// 1 (saturating) and increments enemy by 1 (saturating). Pulled out for
/// unit tests.
pub fn apply_war_tick(
    liberated_before: u32,
    enemy_before: u32,
) -> (u32, u32) {
    (
        liberated_before.saturating_sub(1),
        enemy_before.saturating_add(1),
    )
}

/// Pure helper: produces the post-fall region HP for a region the war tick
/// has just demoted from "liberated" back to "enemy-held". Mirrors
/// `victim.enemy_max_hp / 4` from `global_war_tick`.
pub fn fallen_region_hp(enemy_max_hp: u64) -> u64 {
    enemy_max_hp / 4
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn apply_war_tick_decrements_liberated_increments_enemy() {
        assert_eq!(apply_war_tick(5, 20), (4, 21));
    }

    #[test]
    fn apply_war_tick_saturates_liberated_at_zero() {
        // The reducer guards against ticking when liberated == 0, but
        // defence in depth: saturating_sub keeps us from underflow.
        assert_eq!(apply_war_tick(0, 25), (0, 26));
    }

    #[test]
    fn apply_war_tick_saturates_enemy_at_max() {
        assert_eq!(apply_war_tick(5, u32::MAX), (4, u32::MAX));
    }

    #[test]
    fn fallen_region_hp_quarters_max() {
        // A re-conquered region comes back at 25% HP.
        assert_eq!(fallen_region_hp(50_000), 12_500);
        assert_eq!(fallen_region_hp(100_000), 25_000);
        assert_eq!(fallen_region_hp(250_000), 62_500);
    }

    #[test]
    fn fallen_region_hp_handles_zero_max() {
        assert_eq!(fallen_region_hp(0), 0);
    }
}
