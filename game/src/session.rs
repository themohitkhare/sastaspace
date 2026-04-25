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

/// Called from client_disconnected to clean up any dangling active sessions.
pub fn auto_end_battle(_ctx: &spacetimedb::ReducerContext) {
    // Placeholder — full implementation added in Task 7
}
