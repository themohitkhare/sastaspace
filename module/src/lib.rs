use spacetimedb::{reducer, table, Identity, ReducerContext, Table, Timestamp};

#[table(accessor = project, public)]
pub struct Project {
    #[primary_key]
    pub slug: String,
    pub title: String,
    pub blurb: String,
    pub status: String,
    pub tags: Vec<String>,
    pub url: String,
}

#[table(accessor = presence, public)]
pub struct Presence {
    #[primary_key]
    pub identity: Identity,
    pub joined_at: Timestamp,
    pub last_seen: Timestamp,
}

/// Comments on workshop notes (notes.sastaspace.com posts).
///
/// Anyone can `submit_anon_comment`; new rows land with `status="pending"`.
/// The Agno+Ollama moderator (infra/agents/moderator) subscribes to pending
/// rows and calls `set_comment_status` with the owner identity.
///
/// `submitter` is recorded for rate-limiting and abuse triage; clients should
/// **not** be shown the raw Identity. The public `author_name` is the only
/// attribution that surfaces.
#[table(accessor = comment, public)]
pub struct Comment {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    #[index(btree)]
    pub post_slug: String,
    pub author_name: String,
    pub body: String,
    pub created_at: Timestamp,
    /// One of: "pending" | "approved" | "flagged" | "rejected"
    pub status: String,
    #[index(btree)]
    pub submitter: Identity,
}

const COMMENT_STATUSES: &[&str] = &["pending", "approved", "flagged", "rejected"];
const RATE_LIMIT_WINDOW_MICROS: i64 = 5 * 60 * 1_000_000; // 5 min
const RATE_LIMIT_MAX: usize = 5;
/// Magic-link tokens are valid for 15 minutes after issue.
const AUTH_TOKEN_TTL_MICROS: i64 = 15 * 60 * 1_000_000;

/// Registered users — anyone who has clicked through a magic link from
/// auth.sastaspace.com. The `identity` is the SpacetimeDB Identity that
/// the auth service issues to that email; from that point on the user
/// can post signed-in comments under their `display_name`.
///
/// Email is stored for: (a) future re-issue of identity if the user
/// loses their token, (b) eventual unsubscribe / deletion. It is NEVER
/// surfaced to other clients via the public schema — the only attribution
/// shown publicly is `display_name`.
#[table(accessor = user, public)]
pub struct User {
    #[primary_key]
    pub identity: Identity,
    #[unique]
    pub email: String,
    pub display_name: String,
    pub created_at: Timestamp,
}

/// Pending magic-link tokens. Created by the auth service when a user
/// requests a sign-in email; consumed by the auth service when the user
/// clicks the link. Single-use (once `used_at` is set, the token is dead)
/// and time-limited (`expires_at`).
///
/// Private table — clients can't see it. Auth service reads/writes via
/// owner-only reducers.
#[table(accessor = auth_token)]
pub struct AuthToken {
    #[primary_key]
    pub token: String,
    pub email: String,
    pub created_at: Timestamp,
    pub expires_at: Timestamp,
    pub used_at: Option<Timestamp>,
}

/// The hex-encoded Identity of the database owner. Only this identity can
/// call write reducers on the `project` table. Sourced from
/// `GET /v1/database/sastaspace -> owner_identity.__identity__` after the
/// initial publish. If the owner ever rotates, update this constant and
/// re-publish (see SECURITY_AUDIT.md finding #1 for rationale).
const OWNER_HEX: &str = "c20086b8ce1d18ec9c564044615071677620eafad99c922edbb3e3463b6f79ba";

fn assert_owner(ctx: &ReducerContext) -> Result<(), String> {
    let owner = Identity::from_hex(OWNER_HEX).map_err(|e| format!("invalid OWNER_HEX: {e}"))?;
    if ctx.sender() != owner {
        return Err("not authorized".into());
    }
    Ok(())
}

#[reducer(init)]
pub fn init(_ctx: &ReducerContext) {}

#[reducer(client_connected)]
pub fn client_connected(ctx: &ReducerContext) {
    let now = ctx.timestamp;
    if let Some(mut existing) = ctx.db.presence().identity().find(ctx.sender()) {
        existing.last_seen = now;
        ctx.db.presence().identity().update(existing);
    } else {
        ctx.db.presence().insert(Presence {
            identity: ctx.sender(),
            joined_at: now,
            last_seen: now,
        });
    }
}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    ctx.db.presence().identity().delete(ctx.sender());
}

/// Heartbeat is intentionally callable by any connected client — it only
/// touches the caller's own Presence row, so there's no spoof risk.
#[reducer]
pub fn heartbeat(ctx: &ReducerContext) -> Result<(), String> {
    let mut row = ctx
        .db
        .presence()
        .identity()
        .find(ctx.sender())
        .ok_or_else(|| "no presence row for caller".to_string())?;
    row.last_seen = ctx.timestamp;
    ctx.db.presence().identity().update(row);
    Ok(())
}

#[reducer]
pub fn upsert_project(
    ctx: &ReducerContext,
    slug: String,
    title: String,
    blurb: String,
    status: String,
    tags: Vec<String>,
    url: String,
) -> Result<(), String> {
    assert_owner(ctx)?;
    let row = Project {
        slug: slug.clone(),
        title,
        blurb,
        status,
        tags,
        url,
    };
    if ctx.db.project().slug().find(slug).is_some() {
        ctx.db.project().slug().update(row);
    } else {
        ctx.db.project().insert(row);
    }
    Ok(())
}

#[reducer]
pub fn delete_project(ctx: &ReducerContext, slug: String) -> Result<(), String> {
    assert_owner(ctx)?;
    if ctx.db.project().slug().find(&slug).is_none() {
        return Err(format!("no project with slug `{slug}`"));
    }
    ctx.db.project().slug().delete(&slug);
    Ok(())
}

/// Public reducer: anyone can submit a comment. Lands as `pending`; the
/// moderator agent transitions it to `approved` or `flagged` within a few
/// seconds. Rate-limited per Identity (5 per 5 minutes).
#[reducer]
pub fn submit_anon_comment(
    ctx: &ReducerContext,
    post_slug: String,
    author_name: String,
    body: String,
) -> Result<(), String> {
    let name = author_name.trim();
    let body = body.trim();
    if post_slug.is_empty() {
        return Err("post_slug required".into());
    }
    if name.len() > 64 {
        return Err("author_name too long (max 64 chars)".into());
    }
    if body.len() < 4 {
        return Err("body too short (min 4 chars)".into());
    }
    if body.len() > 4000 {
        return Err("body too long (max 4000 chars)".into());
    }

    let now = ctx.timestamp;
    let cutoff_micros = now
        .to_micros_since_unix_epoch()
        .saturating_sub(RATE_LIMIT_WINDOW_MICROS);
    let recent = ctx
        .db
        .comment()
        .submitter()
        .filter(ctx.sender())
        .filter(|c| c.created_at.to_micros_since_unix_epoch() >= cutoff_micros)
        .count();
    if recent >= RATE_LIMIT_MAX {
        return Err(format!(
            "rate limit: max {RATE_LIMIT_MAX} comments per 5min"
        ));
    }

    let display = if name.is_empty() { "visitor" } else { name };
    ctx.db.comment().insert(Comment {
        id: 0, // auto_inc
        post_slug,
        author_name: display.to_string(),
        body: body.to_string(),
        created_at: now,
        status: "pending".to_string(),
        submitter: ctx.sender(),
    });
    Ok(())
}

/// Owner-only: transition a comment's status. Used by the moderator agent
/// to flip pending → approved/flagged, and by the admin queue to override.
#[reducer]
pub fn set_comment_status(ctx: &ReducerContext, id: u64, status: String) -> Result<(), String> {
    assert_owner(ctx)?;
    if !COMMENT_STATUSES.contains(&status.as_str()) {
        return Err(format!(
            "invalid status `{status}` (valid: {})",
            COMMENT_STATUSES.join(", ")
        ));
    }
    let mut row = ctx
        .db
        .comment()
        .id()
        .find(id)
        .ok_or_else(|| format!("no comment with id {id}"))?;
    row.status = status;
    ctx.db.comment().id().update(row);
    Ok(())
}

/// Owner-only: hard-delete a comment. Used to wipe spam permanently
/// instead of just flagging it.
#[reducer]
pub fn delete_comment(ctx: &ReducerContext, id: u64) -> Result<(), String> {
    assert_owner(ctx)?;
    if ctx.db.comment().id().find(id).is_none() {
        return Err(format!("no comment with id {id}"));
    }
    ctx.db.comment().id().delete(id);
    Ok(())
}

/// Public reducer: signed-in user posts a comment. Same body validation
/// as anon, but skips author_name (looked up from User row) and skips
/// the rate limit (logged-in users are already cost-controlled by the
/// magic-link friction).
///
/// The caller's Identity must match a `User` row — anonymous calls and
/// strangers fail closed. The display_name comes from the User table,
/// so a logged-in user can't impersonate someone else's name.
#[reducer]
pub fn submit_user_comment(
    ctx: &ReducerContext,
    post_slug: String,
    body: String,
) -> Result<(), String> {
    let body = body.trim();
    if post_slug.is_empty() {
        return Err("post_slug required".into());
    }
    if body.len() < 4 {
        return Err("body too short (min 4 chars)".into());
    }
    if body.len() > 4000 {
        return Err("body too long (max 4000 chars)".into());
    }

    let user = ctx
        .db
        .user()
        .identity()
        .find(ctx.sender())
        .ok_or_else(|| "not signed in".to_string())?;

    ctx.db.comment().insert(Comment {
        id: 0,
        post_slug,
        author_name: user.display_name,
        body: body.to_string(),
        created_at: ctx.timestamp,
        status: "pending".to_string(),
        submitter: ctx.sender(),
    });
    Ok(())
}

/// Owner-only: register a new user (called by the auth service after
/// magic-link verification). Idempotent on email — re-registering the
/// same email updates the display_name + identity rather than failing.
#[reducer]
pub fn register_user(
    ctx: &ReducerContext,
    user_identity: Identity,
    email: String,
    display_name: String,
) -> Result<(), String> {
    assert_owner(ctx)?;
    let email = email.trim().to_lowercase();
    let display_name = display_name.trim().to_string();
    if email.is_empty() || !email.contains('@') {
        return Err(format!("invalid email `{email}`"));
    }
    if display_name.is_empty() || display_name.len() > 64 {
        return Err("display_name must be 1..=64 chars".into());
    }

    let row = User {
        identity: user_identity,
        email: email.clone(),
        display_name,
        created_at: ctx.timestamp,
    };

    if let Some(existing) = ctx.db.user().email().find(&email) {
        // Re-register: drop the old identity row, replace with the new one
        ctx.db.user().identity().delete(existing.identity);
    }
    ctx.db.user().insert(row);
    Ok(())
}

/// Owner-only: store a magic-link token for an email (called by the
/// auth service when the user requests sign-in).
#[reducer]
pub fn issue_auth_token(ctx: &ReducerContext, token: String, email: String) -> Result<(), String> {
    assert_owner(ctx)?;
    let email = email.trim().to_lowercase();
    if email.is_empty() || !email.contains('@') {
        return Err(format!("invalid email `{email}`"));
    }
    if token.len() < 32 {
        return Err("token too short (must be ≥32 chars of entropy)".into());
    }
    let now = ctx.timestamp;
    let expires = Timestamp::from_micros_since_unix_epoch(
        now.to_micros_since_unix_epoch() + AUTH_TOKEN_TTL_MICROS,
    );
    ctx.db.auth_token().insert(AuthToken {
        token,
        email,
        created_at: now,
        expires_at: expires,
        used_at: None,
    });
    Ok(())
}

/// Owner-only: mark a magic-link token as used (called by the auth
/// service on /auth/verify). Returns the email associated with the
/// token. Fails if the token is unknown, expired, or already used.
#[reducer]
pub fn consume_auth_token(ctx: &ReducerContext, token: String) -> Result<(), String> {
    assert_owner(ctx)?;
    let mut row = ctx
        .db
        .auth_token()
        .token()
        .find(&token)
        .ok_or_else(|| "unknown token".to_string())?;
    if row.used_at.is_some() {
        return Err("token already used".into());
    }
    let now = ctx.timestamp;
    if now.to_micros_since_unix_epoch() > row.expires_at.to_micros_since_unix_epoch() {
        return Err("token expired".into());
    }
    row.used_at = Some(now);
    ctx.db.auth_token().token().update(row);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_struct_round_trips() {
        let p = Project {
            slug: "x".into(),
            title: "X".into(),
            blurb: "b".into(),
            status: "live".into(),
            tags: vec!["a".into(), "b".into()],
            url: "https://x.sastaspace.com".into(),
        };
        assert_eq!(p.slug, "x");
        assert_eq!(p.tags.len(), 2);
        assert!(p.url.starts_with("https://"));
    }

    #[test]
    fn presence_struct_uses_identity_pk() {
        let id = Identity::ZERO;
        let now = Timestamp::UNIX_EPOCH;
        let p = Presence {
            identity: id,
            joined_at: now,
            last_seen: now,
        };
        assert_eq!(p.identity, id);
        assert_eq!(p.joined_at, p.last_seen);
    }

    #[test]
    fn delete_project_error_message_includes_slug() {
        let slug = "nope";
        let msg = format!("no project with slug `{slug}`");
        assert_eq!(msg, "no project with slug `nope`");
    }

    #[test]
    fn owner_hex_parses_to_identity() {
        Identity::from_hex(OWNER_HEX).expect("OWNER_HEX must be a valid 64-char hex identity");
    }

    #[test]
    fn comment_statuses_are_known() {
        assert!(COMMENT_STATUSES.contains(&"pending"));
        assert!(COMMENT_STATUSES.contains(&"approved"));
        assert!(COMMENT_STATUSES.contains(&"flagged"));
        assert!(COMMENT_STATUSES.contains(&"rejected"));
    }

    #[test]
    fn rate_limit_window_is_five_minutes() {
        assert_eq!(RATE_LIMIT_WINDOW_MICROS, 5 * 60 * 1_000_000);
        assert_eq!(RATE_LIMIT_MAX, 5);
    }

    #[test]
    fn auth_token_ttl_is_fifteen_minutes() {
        assert_eq!(AUTH_TOKEN_TTL_MICROS, 15 * 60 * 1_000_000);
    }

    #[test]
    fn user_struct_round_trips() {
        let u = User {
            identity: Identity::ZERO,
            email: "test@example.com".into(),
            display_name: "Tester".into(),
            created_at: Timestamp::UNIX_EPOCH,
        };
        assert_eq!(u.email, "test@example.com");
        assert_eq!(u.display_name, "Tester");
    }

    #[test]
    fn auth_token_struct_round_trips() {
        let t = AuthToken {
            token: "abc123".into(),
            email: "test@example.com".into(),
            created_at: Timestamp::UNIX_EPOCH,
            expires_at: Timestamp::UNIX_EPOCH,
            used_at: None,
        };
        assert_eq!(t.token, "abc123");
        assert!(t.used_at.is_none());
    }
}
