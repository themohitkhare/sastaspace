use spacetimedb::{rand::Rng, reducer, table, Identity, ReducerContext, Table, Timestamp};

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
/// Comments are signed-in only — the submitter must have a User row.
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

/// Sole comment-submit reducer: caller must be a registered user.
/// Anonymous identities and strangers fail closed. The display_name
/// comes from the User table, so users can't impersonate each other.
/// Magic-link friction (15-min token, real email) handles rate-limiting.
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

// === auth-mailer (Phase 1 W1) ===

/// Outbound emails the auth-mailer worker drains.
/// status: "queued" | "sent" | "failed"
#[table(accessor = pending_email)]
pub struct PendingEmail {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub to_email: String,
    pub subject: String,
    pub body_html: String,
    pub body_text: String,
    pub created_at: Timestamp,
    pub status: String,
    pub provider_msg_id: Option<String>,
    pub error: Option<String>,
}

/// Frontend-callable reducer. Validates email, mints a token, queues the email.
/// callback_url is the app's /auth/callback URL (notes/typewars/admin) — the
/// worker stitches it into the magic-link.
#[reducer]
pub fn request_magic_link(
    ctx: &ReducerContext,
    email: String,
    app: String,
    prev_identity_hex: Option<String>,
    callback_url: String,
) -> Result<(), String> {
    let email = email.trim().to_lowercase();
    validate_magic_link_args(&email, &app, &callback_url)?;
    let token: String = (0..32)
        .map(|_| {
            let n: u32 = ctx.rng().gen_range(0..62);
            let c = if n < 26 {
                b'a' + n as u8
            } else if n < 52 {
                b'A' + (n - 26) as u8
            } else {
                b'0' + (n - 52) as u8
            };
            c as char
        })
        .collect();
    let now = ctx.timestamp;
    let expires = Timestamp::from_micros_since_unix_epoch(
        now.to_micros_since_unix_epoch() + AUTH_TOKEN_TTL_MICROS,
    );
    ctx.db.auth_token().insert(AuthToken {
        token: token.clone(),
        email: email.clone(),
        created_at: now,
        expires_at: expires,
        used_at: None,
    });
    let magic_link = build_magic_link(&callback_url, &token, &app, prev_identity_hex.as_deref());
    ctx.db.pending_email().insert(PendingEmail {
        id: 0,
        to_email: email.clone(),
        subject: "Your sign-in link to sastaspace".into(),
        body_html: render_magic_link_html(&magic_link),
        body_text: render_magic_link_text(&magic_link),
        created_at: now,
        status: "queued".into(),
        provider_msg_id: None,
        error: None,
    });
    Ok(())
}

/// Worker-only: marks an email as sent. assert_owner enforces.
#[reducer]
pub fn mark_email_sent(
    ctx: &ReducerContext,
    id: u64,
    provider_msg_id: String,
) -> Result<(), String> {
    assert_owner(ctx)?;
    let mut row = ctx
        .db
        .pending_email()
        .id()
        .find(id)
        .ok_or("unknown email id")?;
    row.status = "sent".into();
    row.provider_msg_id = Some(provider_msg_id);
    ctx.db.pending_email().id().update(row);
    Ok(())
}

/// Worker-only: records a send failure for retry/observability.
#[reducer]
pub fn mark_email_failed(ctx: &ReducerContext, id: u64, error: String) -> Result<(), String> {
    assert_owner(ctx)?;
    let mut row = ctx
        .db
        .pending_email()
        .id()
        .find(id)
        .ok_or("unknown email id")?;
    row.status = "failed".into();
    row.error = Some(error);
    ctx.db.pending_email().id().update(row);
    Ok(())
}

/// Atomic verify: consume token + register user under ctx.sender() identity.
/// The frontend mints a fresh identity via POST /v1/identity, reconnects with
/// that JWT, then calls this reducer. ctx.sender() is therefore the new identity.
#[reducer]
pub fn verify_token(
    ctx: &ReducerContext,
    token: String,
    display_name: String,
) -> Result<(), String> {
    let now = ctx.timestamp;
    let mut tok = ctx
        .db
        .auth_token()
        .token()
        .find(token.clone())
        .ok_or("unknown token")?;
    if tok.used_at.is_some() {
        return Err("token already used".into());
    }
    if tok.expires_at.to_micros_since_unix_epoch() < now.to_micros_since_unix_epoch() {
        return Err("token expired".into());
    }
    let email = tok.email.clone();
    tok.used_at = Some(now);
    ctx.db.auth_token().token().update(tok);

    let display_name = if display_name.trim().is_empty() {
        email.split('@').next().unwrap_or("user").to_string()
    } else {
        display_name.trim().chars().take(60).collect()
    };

    if let Some(existing) = ctx.db.user().email().find(email.clone()) {
        // Re-bind: drop the old identity row, re-insert under the new identity
        // so the User table's identity primary key stays consistent.
        ctx.db.user().identity().delete(existing.identity);
        ctx.db.user().insert(User {
            identity: ctx.sender(),
            email,
            display_name,
            created_at: existing.created_at,
        });
    } else {
        ctx.db.user().insert(User {
            identity: ctx.sender(),
            email,
            display_name,
            created_at: now,
        });
    }
    Ok(())
}

/// Pure helper: validates the inputs to `request_magic_link`. Pulled out so
/// it can be unit-tested on the host without a `ReducerContext`.
fn validate_magic_link_args(email: &str, app: &str, callback_url: &str) -> Result<(), String> {
    if !email.contains('@') || email.len() > 200 {
        return Err("invalid email".into());
    }
    if !matches!(app, "notes" | "typewars" | "admin") {
        return Err("unknown app".into());
    }
    if !callback_url.starts_with("https://") || callback_url.len() > 400 {
        return Err("invalid callback_url".into());
    }
    Ok(())
}

/// Pure helper: builds the magic-link URL given the validated inputs and a
/// freshly-minted token. Extracted for host-side testing.
fn build_magic_link(
    callback_url: &str,
    token: &str,
    app: &str,
    prev_identity_hex: Option<&str>,
) -> String {
    let prev_qs = prev_identity_hex
        .map(|p| format!("&prev={}", p.trim_start_matches("0x")))
        .unwrap_or_default();
    format!(
        "{}?t={}&app={}{}",
        callback_url.trim_end_matches('/'),
        token,
        app,
        prev_qs,
    )
}

fn render_magic_link_html(link: &str) -> String {
    format!(
        r#"<!doctype html><html><body style="margin:0;padding:32px;background:#f5f1e8;color:#1a1917;font-family:-apple-system,system-ui,sans-serif"><div style="max-width:520px;margin:0 auto;background:#fbf8f0;border:1px solid rgba(168,161,150,0.4);border-radius:16px;padding:28px 32px"><h1 style="font-size:24px;font-weight:500;margin:0 0 14px">Sign in to sastaspace.</h1><p style="font-size:15px;line-height:1.55;margin:0 0 20px">Click below to sign in. Good for 15 minutes, works once.</p><p style="margin:0 0 24px"><a href="{link}" style="display:inline-block;background:#1a1917;color:#f5f1e8;padding:12px 22px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:500">sign in &rarr;</a></p><p style="font-size:13px;color:#6b6458;margin:0 0 8px">If the button doesn't work, paste this URL:</p><p style="font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#6b6458;word-break:break-all;margin:0 0 24px">{link}</p><p style="font-size:12px;color:#a8a196;margin:0">If you didn't ask for this, ignore.</p></div></body></html>"#
    )
}

fn render_magic_link_text(link: &str) -> String {
    format!("Sign in to sastaspace.\n\nClick this link (good for 15 minutes, works once):\n\n  {link}\n\nIf you didn't ask for this, ignore.\n\n—\nsastaspace.com\n")
}

// === end auth-mailer (Phase 1 W1) ===

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

// === auth-mailer (Phase 1 W1) tests ===
//
// SpacetimeDB 2.1 ships no `TestContext`/`TestDb` harness, so we cannot drive
// reducers in-process here (the plan acknowledged this — see Task 1 Step 2's
// API-discovery note). Instead the integration paths are covered by:
//   - the worker Vitest suite (`workers/src/agents/auth-mailer.test.ts`),
//   - the Step 6 smoke test against a real local STDB.
//
// What we *can* unit-test on host: the pure helpers we extracted and the
// `PendingEmail` row's struct shape.
#[cfg(test)]
mod auth_mailer_tests {
    use super::*;

    #[test]
    fn validate_magic_link_args_accepts_well_formed() {
        assert!(validate_magic_link_args(
            "user@example.com",
            "notes",
            "https://notes.sastaspace.com/auth/callback",
        )
        .is_ok());
        assert!(validate_magic_link_args(
            "x@y.io",
            "typewars",
            "https://typewars.sastaspace.com/auth/callback",
        )
        .is_ok());
        assert!(validate_magic_link_args(
            "ops@sastaspace.com",
            "admin",
            "https://admin.sastaspace.com/auth/callback",
        )
        .is_ok());
    }

    #[test]
    fn validate_magic_link_args_rejects_bad_email() {
        assert!(validate_magic_link_args(
            "notanemail",
            "notes",
            "https://notes.sastaspace.com/auth/callback",
        )
        .is_err());
        let too_long = format!("{}@example.com", "a".repeat(250));
        assert!(validate_magic_link_args(
            &too_long,
            "notes",
            "https://notes.sastaspace.com/auth/callback",
        )
        .is_err());
    }

    #[test]
    fn validate_magic_link_args_rejects_unknown_app() {
        let r = validate_magic_link_args(
            "user@example.com",
            "wat",
            "https://notes.sastaspace.com/auth/callback",
        );
        assert!(r.is_err());
        assert_eq!(r.unwrap_err(), "unknown app");
    }

    #[test]
    fn validate_magic_link_args_rejects_non_https_callback() {
        assert!(validate_magic_link_args(
            "user@example.com",
            "notes",
            "http://notes.sastaspace.com/auth/callback",
        )
        .is_err());
        assert!(validate_magic_link_args("user@example.com", "notes", "javascript:evil").is_err());
    }

    #[test]
    fn build_magic_link_basic() {
        let link = build_magic_link(
            "https://notes.sastaspace.com/auth/callback",
            "tok123",
            "notes",
            None,
        );
        assert_eq!(
            link,
            "https://notes.sastaspace.com/auth/callback?t=tok123&app=notes"
        );
    }

    #[test]
    fn build_magic_link_includes_prev_when_supplied() {
        let link = build_magic_link(
            "https://typewars.sastaspace.com/auth/callback",
            "tok456",
            "typewars",
            Some("0xabcdef0123"),
        );
        assert_eq!(
            link,
            "https://typewars.sastaspace.com/auth/callback?t=tok456&app=typewars&prev=abcdef0123"
        );
    }

    #[test]
    fn build_magic_link_strips_trailing_slash() {
        let link = build_magic_link(
            "https://notes.sastaspace.com/auth/callback/",
            "tok",
            "notes",
            None,
        );
        assert!(!link.contains("//?"));
        assert!(link.starts_with("https://notes.sastaspace.com/auth/callback?"));
    }

    #[test]
    fn render_magic_link_html_contains_link() {
        let html = render_magic_link_html("https://example.com/auth?t=abc&app=notes");
        assert!(html.contains("https://example.com/auth?t=abc&app=notes"));
        assert!(html.contains("Sign in to sastaspace"));
        assert!(html.starts_with("<!doctype html>"));
    }

    #[test]
    fn render_magic_link_text_contains_link() {
        let text = render_magic_link_text("https://example.com/auth?t=abc&app=notes");
        assert!(text.contains("https://example.com/auth?t=abc&app=notes"));
        assert!(text.contains("good for 15 minutes"));
    }

    #[test]
    fn pending_email_struct_round_trips() {
        let e = PendingEmail {
            id: 7,
            to_email: "x@y.com".into(),
            subject: "s".into(),
            body_html: "<p>h</p>".into(),
            body_text: "h".into(),
            created_at: Timestamp::UNIX_EPOCH,
            status: "queued".into(),
            provider_msg_id: None,
            error: None,
        };
        assert_eq!(e.id, 7);
        assert_eq!(e.status, "queued");
        assert!(e.provider_msg_id.is_none());
        assert!(e.error.is_none());
    }
}
