# sastaspace

A portfolio + projects you run in your terminal.

`sastaspace` is a single Rust binary. It opens a TUI splash with your projects, and routes between four small apps — typing game, notes, audio-pack generator, owner dashboard — all backed by one SpacetimeDB instance at `wss://stdb.sastaspace.com`.

## Install

```sh
brew install themohitkhare/sastaspace/sastaspace
```

Or:

```sh
curl -sSf https://sastaspace.com/install.sh | sh
```

Or grab a binary directly from [GitHub Releases](https://github.com/themohitkhare/sastaspace/releases/latest) — macOS (arm64+x86), Linux (x86+arm64), Windows.

## Run

```sh
sastaspace
```

Switch between apps:

| Key | App |
|---|---|
| `Shift-P` | Portfolio splash (default) |
| `Shift-N` | Notes — vim-style editor + comments |
| `Shift-T` | TypeWars — multiplayer typing game |
| `Shift-D` | Deck — text → audio packs |
| `Shift-A` | Admin (owner-only, Google OAuth) |
| `Shift-L` | Sign-in modal (magic-link email) |
| `q` / `Ctrl-C` | Quit |

The TUI connects to the live `stdb.sastaspace.com`. Anonymous use is fine for read-only views; signing in (magic-link) lets you post comments and play TypeWars under a callsign.

## Architecture

```
┌────────────────────────────┐    wss      ┌──────────────────────────┐
│   sastaspace TUI (local)   │ ◄─────────► │  SpacetimeDB modules     │
│   crates/shell + 4 apps    │             │  sastaspace + typewars   │
└────────────────────────────┘             └────────┬─────────────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────────────┐
                                           │  TypeScript workers      │
                                           │  (auth-mailer, deck-     │
                                           │   agent, moderator,      │
                                           │   admin-collector)       │
                                           └──────────────────────────┘
```

One Rust binary, one SpacetimeDB instance, four background workers running on the prod box. No web UI, no Python services, no per-app servers — the binary is the surface.

## Development

```sh
git clone https://github.com/themohitkhare/sastaspace
cd sastaspace
cargo build -p shell --release
target/release/sastaspace
```

Run tests:

```sh
cargo test --workspace                 # unit + snapshot tests
SPACETIME_PORT=3199 cargo test -p e2e  # PTY end-to-end against a local fixture
```

## Repo layout

```
sastaspace/
├── crates/
│   ├── shell/             # the binary entry point + router
│   ├── core/              # theme, keymap, App trait, Action enum
│   ├── stdb-client/       # spacetimedb-sdk wrapper + generated bindings
│   ├── auth/              # magic-link + Google OAuth device flow + keychain
│   ├── app-portfolio/     # splash screen
│   ├── app-notes/         # vim-style editor
│   ├── app-typewars/      # typing game
│   ├── app-deck/          # NLP→audio
│   └── app-admin/         # owner dashboard
├── modules/
│   ├── sastaspace/        # main STDB module — projects, comments, auth
│   └── typewars/          # game state — players, regions, words
├── workers/               # TypeScript STDB-side automation (runs on prod)
├── tests/e2e/             # Rust expectrl PTY scenarios
├── docs/                  # specs, plans, audits
└── infra/                 # Cloudflared tunnel config
```

## Releases

Tagged with cargo-dist. Each `vX.Y.Z` tag triggers a 5-platform release with a Homebrew formula auto-generated from workspace metadata.

```sh
git tag -a v0.1.3 -m "..."
git push origin v0.1.3
```

## License

MIT.
