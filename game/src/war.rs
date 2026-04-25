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
