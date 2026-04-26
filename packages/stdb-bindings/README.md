# @sastaspace/stdb-bindings

Typed TypeScript bindings for the `sastaspace` SpacetimeDB module.

## Regenerate

```bash
# from repo root, after `spacetime publish` succeeds
pnpm bindings:generate
```

This runs `spacetime generate --lang typescript --out-dir packages/stdb-bindings/src/generated --project-path modules/sastaspace`.

The `src/generated/` folder is gitignored — CI regenerates it on every module publish and bundles it into the landing build.

## What this package exports

Whatever `spacetime generate` produces from `modules/sastaspace/src/lib.rs` — at the time of writing:

- `DbConnection` — connection builder
- `Project`, `Presence` — typed row classes
- `heartbeatReducer`, `upsertProjectReducer` — typed reducer call helpers
