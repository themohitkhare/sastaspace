use spacetimedb::{reducer, ReducerContext, Table};
use word::word_expire_schedule;

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
        scheduled_at: spacetimedb::ScheduleAt::from(std::time::Duration::from_secs(2)),
    });
    region::init_region_tick_schedule(ctx);
}

#[reducer(client_connected)]
pub fn client_connected(_ctx: &ReducerContext) {}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    session::auto_end_battle(ctx);
}
