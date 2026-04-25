use spacetimedb::{reducer, ReducerContext, ScheduleAt, Table};
use std::time::Duration;
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
        scheduled_at: ScheduleAt::from(Duration::from_secs(2)),
    });
}

#[reducer(client_connected)]
pub fn client_connected(_ctx: &ReducerContext) {}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    session::auto_end_battle(ctx);
}
