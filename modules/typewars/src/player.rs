use spacetimedb::{table, Identity, Timestamp, reducer, ReducerContext, Table};
use crate::legion::LEGION_COUNT;

#[derive(Clone, Debug, PartialEq)]
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
    pub email: Option<String>,
}

pub fn validate_registration(
    username: &str,
    legion: u8,
    existing_usernames_lower: &[String],
) -> Result<(), String> {
    if username.is_empty() {
        return Err("username required".into());
    }
    if username.len() > 32 {
        return Err("username too long (max 32 chars)".into());
    }
    if legion >= LEGION_COUNT {
        return Err(format!("invalid legion {legion} (max {})", LEGION_COUNT - 1));
    }
    let lower = username.to_lowercase();
    if existing_usernames_lower.iter().any(|u| u == &lower) {
        return Err("username taken".into());
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
    let existing: Vec<String> = ctx.db.player()
        .iter()
        .map(|p| p.username.to_lowercase())
        .collect();
    validate_registration(&username, legion, &existing)?;
    ctx.db.player().insert(Player {
        identity: ctx.sender(),
        username,
        legion,
        total_damage: 0,
        season_damage: 0,
        best_wpm: 0,
        joined_at: ctx.timestamp,
        email: None,
    });
    Ok(())
}

/// Result of planning a claim_progress reducer call. Pure: no DB access.
#[derive(Debug, PartialEq)]
pub enum ClaimAction {
    /// Caller has a guest row and no email row yet — rekey the guest row.
    Rekey { delete_id: Identity, insert: Player },
    /// Caller already has a verified row and brought guest stats — merge.
    Merge { delete_id: Identity, update: Player },
    /// Caller has a verified row and no prior guest play — just stamp email.
    StampEmail { update: Player },
    /// Caller has nothing on either side — nothing to do.
    Noop,
}

pub fn plan_claim(
    guest: Option<Player>,
    existing: Option<Player>,
    new_id: Identity,
    email: String,
) -> ClaimAction {
    match (guest, existing) {
        (Some(g), None) => {
            let delete_id = g.identity;
            let mut row = g;
            row.identity = new_id;
            row.email = Some(email);
            ClaimAction::Rekey { delete_id, insert: row }
        }
        (Some(g), Some(mut e)) => {
            e.total_damage = e.total_damage.saturating_add(g.total_damage);
            e.season_damage = e.season_damage.saturating_add(g.season_damage);
            e.best_wpm = e.best_wpm.max(g.best_wpm);
            e.email = Some(email);
            ClaimAction::Merge { delete_id: g.identity, update: e }
        }
        (None, Some(mut e)) => {
            e.email = Some(email);
            ClaimAction::StampEmail { update: e }
        }
        (None, None) => ClaimAction::Noop,
    }
}

// SECURITY: Owner-only reducer. The auth service (services/auth/) is the
// only caller — it mints a fresh new_identity via STDB and passes both
// the prev_identity (the user's previous browser/guest identity) and
// new_identity (the freshly-minted email-bound one) explicitly. Gating
// on owner blocks any malicious client from forging claim_progress calls.
#[reducer]
pub fn claim_progress(
    ctx: &ReducerContext,
    prev_identity: Identity,
    new_identity: Identity,
    email: String,
) -> Result<(), String> {
    crate::assert_owner(ctx)?;
    if email.is_empty() || email.len() > 254 {
        return Err("invalid email".into());
    }
    let guest = ctx.db.player().identity().find(prev_identity);
    if let Some(g) = &guest {
        if g.email.is_some() {
            return Err("target row is already verified".into());
        }
    }
    let existing = ctx.db.player().identity().find(new_identity);
    match plan_claim(guest, existing, new_identity, email) {
        ClaimAction::Rekey { delete_id, insert } => {
            ctx.db.player().identity().delete(delete_id);
            ctx.db.player().insert(insert);
        }
        ClaimAction::Merge { delete_id, update } => {
            ctx.db.player().identity().delete(delete_id);
            ctx.db.player().identity().update(update);
        }
        ClaimAction::StampEmail { update } => {
            ctx.db.player().identity().update(update);
        }
        ClaimAction::Noop => {}
    }
    Ok(())
}

/// Self-service variant of claim_progress for the SpacetimeDB-native auth
/// flow. The caller's own identity (`ctx.sender()`) becomes the new_identity,
/// so a malicious caller can only ever claim a guest's progress *into their
/// own account* — not into someone else's. Same threat model as the legacy
/// auth service path, where the prev_identity arrived in the magic-link URL
/// the user themselves clicked.
///
/// Used by apps/typewars/src/app/auth/verify/page.tsx after the sastaspace
/// `verify_token` reducer has registered the new identity as a User.
#[reducer]
pub fn claim_progress_self(
    ctx: &ReducerContext,
    prev_identity: Identity,
    email: String,
) -> Result<(), String> {
    let new_identity = ctx.sender();
    if email.is_empty() || email.len() > 254 {
        return Err("invalid email".into());
    }
    let guest = ctx.db.player().identity().find(prev_identity);
    if let Some(g) = &guest {
        if g.email.is_some() {
            return Err("target row is already verified".into());
        }
    }
    let existing = ctx.db.player().identity().find(new_identity);
    match plan_claim(guest, existing, new_identity, email) {
        ClaimAction::Rekey { delete_id, insert } => {
            ctx.db.player().identity().delete(delete_id);
            ctx.db.player().insert(insert);
        }
        ClaimAction::Merge { delete_id, update } => {
            ctx.db.player().identity().delete(delete_id);
            ctx.db.player().identity().update(update);
        }
        ClaimAction::StampEmail { update } => {
            ctx.db.player().identity().update(update);
        }
        ClaimAction::Noop => {}
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legion_0_to_4_are_valid() {
        assert!(validate_registration("alice", 0, &[]).is_ok());
        assert!(validate_registration("alice", 4, &[]).is_ok());
    }

    #[test]
    fn legion_5_is_invalid() {
        assert!(validate_registration("alice", 5, &[]).is_err());
    }

    #[test]
    fn empty_username_is_invalid() {
        assert!(validate_registration("", 0, &[]).is_err());
    }

    #[test]
    fn username_max_32_chars() {
        assert!(validate_registration(&"a".repeat(32), 0, &[]).is_ok());
        assert!(validate_registration(&"a".repeat(33), 0, &[]).is_err());
    }

    #[test]
    fn validate_registration_rejects_duplicate_username_case_insensitive() {
        let existing = vec!["ash_q".to_string(), "smoketest".to_string()];
        assert!(validate_registration("ASH_Q", 0, &existing).is_err());
        assert!(validate_registration("Smoketest", 1, &existing).is_err());
        assert!(validate_registration("ash_q", 0, &existing).is_err());
        assert!(validate_registration("new_recruit", 2, &existing).is_ok());
    }

    fn mk_player(
        id_byte: u8,
        username: &str,
        legion: u8,
        total: u64,
        season: u64,
        wpm: u32,
        email: Option<&str>,
    ) -> Player {
        let mut bytes = [0u8; 32];
        bytes[0] = id_byte;
        Player {
            identity: Identity::from_byte_array(bytes),
            username: username.into(),
            legion,
            total_damage: total,
            season_damage: season,
            best_wpm: wpm,
            joined_at: Timestamp::from_micros_since_unix_epoch(0),
            email: email.map(Into::into),
        }
    }

    #[test]
    fn plan_claim_rekey_when_guest_has_row_and_email_does_not() {
        let guest = mk_player(0x01, "ash_q", 0, 1000, 500, 80, None);
        let new_id = Identity::from_byte_array([0x02; 32]);
        let action = plan_claim(Some(guest.clone()), None, new_id, "a@b.com".into());
        match action {
            ClaimAction::Rekey { delete_id, insert } => {
                assert_eq!(delete_id, guest.identity);
                assert_eq!(insert.identity, new_id);
                assert_eq!(insert.email, Some("a@b.com".into()));
                assert_eq!(insert.total_damage, 1000);
                assert_eq!(insert.username, "ash_q");
            }
            other => panic!("expected Rekey, got {:?}", other),
        }
    }

    #[test]
    fn plan_claim_merge_sums_damages_takes_max_wpm_keeps_email_row_legion() {
        let guest = mk_player(0x01, "guest_one", 3, 1000, 500, 80, None);
        let existing = mk_player(0x02, "real_name", 0, 5000, 2000, 100, Some("a@b.com"));
        let action = plan_claim(Some(guest.clone()), Some(existing.clone()), existing.identity, "a@b.com".into());
        match action {
            ClaimAction::Merge { delete_id, update } => {
                assert_eq!(delete_id, guest.identity);
                assert_eq!(update.identity, existing.identity);
                assert_eq!(update.username, "real_name");
                assert_eq!(update.legion, 0);
                assert_eq!(update.total_damage, 6000);
                assert_eq!(update.season_damage, 2500);
                assert_eq!(update.best_wpm, 100);
                assert_eq!(update.email, Some("a@b.com".into()));
            }
            other => panic!("expected Merge, got {:?}", other),
        }
    }

    #[test]
    fn plan_claim_stamp_email_when_only_existing() {
        let existing = mk_player(0x02, "real_name", 0, 5000, 2000, 100, None);
        let action = plan_claim(None, Some(existing.clone()), existing.identity, "a@b.com".into());
        match action {
            ClaimAction::StampEmail { update } => {
                assert_eq!(update.email, Some("a@b.com".into()));
                assert_eq!(update.total_damage, 5000);
            }
            other => panic!("expected StampEmail, got {:?}", other),
        }
    }

    #[test]
    fn plan_claim_noop_when_neither_exists() {
        let new_id = Identity::from_byte_array([0x09; 32]);
        let action = plan_claim(None, None, new_id, "a@b.com".into());
        assert_eq!(action, ClaimAction::Noop);
    }
}
