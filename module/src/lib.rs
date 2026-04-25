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

#[reducer(init)]
pub fn init(ctx: &ReducerContext) {
    seed_project(ctx, "notes", "Notes",
        "Plain-text notes for people who type faster than they think. Keyboard-first, live-synced, zero ceremony.",
        "live", &["next", "spacetimedb"]);
    seed_project(ctx, "feed", "Feed",
        "A reader for the RSS corner of the web. Small, quiet, chronological. No algorithm, no logins you don't need.",
        "open source", &["go", "sqlite"]);
    seed_project(ctx, "pipes", "Pipes",
        "A visual builder for small data jobs. Drag boxes, connect them, watch rows flow through. Runs on your laptop too.",
        "wip", &["react", "spark"]);
    seed_project(ctx, "echo", "Echo",
        "Turn any URL into a podcast feed. Paste a link, get an audio episode, subscribe in your app of choice.",
        "live", &["go", "tts"]);
    seed_project(ctx, "scratch", "Scratch",
        "A whiteboard for one person. Infinite canvas, nothing to save, gone when you close the tab.",
        "paused", &["canvas", "svg"]);
    seed_project(ctx, "lab", "The Lab Log",
        "A firehose of tiny updates from the workshop. New experiments, half-finished thoughts, things that broke today.",
        "live", &["rss", "markdown"]);
}

fn seed_project(ctx: &ReducerContext, slug: &str, title: &str, blurb: &str, status: &str, tags: &[&str]) {
    if ctx.db.project().slug().find(slug.to_string()).is_some() {
        return;
    }
    ctx.db.project().insert(Project {
        slug: slug.to_string(),
        title: title.to_string(),
        blurb: blurb.to_string(),
        status: status.to_string(),
        tags: tags.iter().map(|t| t.to_string()).collect(),
        url: format!("https://{}.sastaspace.com", slug),
    });
}

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
    let row = Project { slug: slug.clone(), title, blurb, status, tags, url };
    if ctx.db.project().slug().find(slug).is_some() {
        ctx.db.project().slug().update(row);
    } else {
        ctx.db.project().insert(row);
    }
}
