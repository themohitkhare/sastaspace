use spacetimedb::{table, Identity, Timestamp, reducer, ReducerContext, Table};
use crate::legion::LEGION_COUNT;

#[table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    pub identity: Identity,
    pub username: String,
    pub legion: u8,
    pub total_damage: u64,
    pub season_damage: u64,
    pub best_wpm: u32,
    pub joined_at: Timestamp,
}

pub fn validate_registration(username: &str, legion: u8) -> Result<(), String> {
    if username.is_empty() {
        return Err("username required".into());
    }
    if username.len() > 32 {
        return Err("username too long (max 32 chars)".into());
    }
    if legion >= LEGION_COUNT {
        return Err(format!("invalid legion {legion} (max {})", LEGION_COUNT - 1));
    }
    Ok(())
}

#[reducer]
pub fn register_player(
    ctx: &ReducerContext,
    username: String,
    legion: u8,
) -> Result<(), String> {
    if ctx.db.player().identity().find(ctx.sender()).is_some() {
        return Err("already registered".into());
    }
    validate_registration(&username, legion)?;
    ctx.db.player().insert(Player {
        identity: ctx.sender(),
        username,
        legion,
        total_damage: 0,
        season_damage: 0,
        best_wpm: 0,
        joined_at: ctx.timestamp,
    });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legion_0_to_4_are_valid() {
        assert!(validate_registration("alice", 0).is_ok());
        assert!(validate_registration("alice", 4).is_ok());
    }

    #[test]
    fn legion_5_is_invalid() {
        assert!(validate_registration("alice", 5).is_err());
    }

    #[test]
    fn empty_username_is_invalid() {
        assert!(validate_registration("", 0).is_err());
    }

    #[test]
    fn username_max_32_chars() {
        assert!(validate_registration(&"a".repeat(32), 0).is_ok());
        assert!(validate_registration(&"a".repeat(33), 0).is_err());
    }
}
