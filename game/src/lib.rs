use spacetimedb::{reducer, ReducerContext};

mod legion;
mod player;
mod region;
mod session;
mod war;
mod word;
mod words;

/// The hex-encoded Identity of the typewars module's owner — only this
/// identity can call owner-only reducers (currently `claim_progress`).
/// Sourced from `GET /v1/database/typewars -> owner_identity.__identity__`
/// after publish. Same operator as sastaspace, so the value is identical.
pub const OWNER_HEX: &str =
    "c20086b8ce1d18ec9c564044615071677620eafad99c922edbb3e3463b6f79ba";

pub fn assert_owner(ctx: &ReducerContext) -> Result<(), String> {
    let owner = spacetimedb::Identity::from_hex(OWNER_HEX)
        .map_err(|e| format!("invalid OWNER_HEX: {e}"))?;
    if ctx.sender() != owner {
        return Err("not authorized".into());
    }
    Ok(())
}

#[reducer(init)]
pub fn init(ctx: &ReducerContext) {
    region::seed_regions(ctx);
    war::init_global_war(ctx);
    word::init_word_expire_schedule(ctx);
    region::init_region_tick_schedule(ctx);
    war::init_war_tick_schedule(ctx);
}

#[reducer(client_connected)]
pub fn client_connected(_ctx: &ReducerContext) {}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    session::auto_end_battle(ctx);
}
