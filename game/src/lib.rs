use spacetimedb::{reducer, ReducerContext};

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
    word::init_word_expire_schedule(ctx);
    region::init_region_tick_schedule(ctx);
}

#[reducer(client_connected)]
pub fn client_connected(_ctx: &ReducerContext) {}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    session::auto_end_battle(ctx);
}
