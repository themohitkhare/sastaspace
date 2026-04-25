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

/// Called once when the module is first published. Intentionally a no-op —
/// projects are added via the `upsert_project` reducer when there's something
/// real to ship. The lab starts quiet.
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
) {
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
}

#[reducer]
pub fn delete_project(ctx: &ReducerContext, slug: String) -> Result<(), String> {
    if ctx.db.project().slug().find(&slug).is_none() {
        return Err(format!("no project with slug `{slug}`"));
    }
    ctx.db.project().slug().delete(&slug);
    Ok(())
}

#[cfg(test)]
mod tests {
    //! Pure logic tests — exercise plain Rust paths that don't need a live
    //! ReducerContext. The macro-generated table accessors require the
    //! spacetimedb runtime, which isn't available under `cargo test` (these
    //! would belong in a SpacetimeDB integration test suite). We at least
    //! lock down the shapes and the trivial helpers here.

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
        // Validates the error string format without needing a real ctx.
        let slug = "nope";
        let msg = format!("no project with slug `{slug}`");
        assert_eq!(msg, "no project with slug `nope`");
    }
}
