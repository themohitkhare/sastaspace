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
    victim.enemy_hp = victim.enemy_max_hp / 4;
    reset_legion_damage(&mut victim);
    ctx.db.region().id().update(victim);

    let mut w = war;
    w.liberated_territories = w.liberated_territories.saturating_sub(1);
    w.enemy_territories = w.enemy_territories.saturating_add(1);
    let liberated_after = w.liberated_territories;
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
