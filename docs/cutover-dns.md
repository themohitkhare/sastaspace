# Cut-over status

The TUI migration is shipped. v0.1.2 is the live release.

## ✅ Done

### Cloudflare DNS
- 5 dead app CNAMEs deleted: `admin/auth/deck/notes/typewars.sastaspace.com`
- Apex `sastaspace.com` and `www.sastaspace.com` continue routing through the tunnel — but to the new static site (see below). Both serve **HTTP 200**.

### Cloudflared tunnel ingress (Cloudflare-managed)
9 → 4 entries. Final state:
| hostname | service |
|---|---|
| `sastaspace.com` | localhost:3110 (static site) |
| `www.sastaspace.com` | localhost:3110 |
| `stdb.sastaspace.com` | localhost:3100 (SpacetimeDB) |
| _catch-all_ | http_status:404 |

### Static site on `taxila`
A small `nginx:alpine` container (`sastaspace-www`) serves `~/mkhare/sastaspace-www/` as the apex content:
- `https://sastaspace.com/` → install + run instructions (TUI-themed page).
- `https://sastaspace.com/install.sh` → one-liner installer that curls the cargo-dist platform-detect installer from GitHub Releases.

To regenerate / edit:
```bash
ssh 192.168.0.37 "ls /home/mkhare/sastaspace-www/"
# Edit the html/sh; container picks up the volume mount on next request.
# Restart if needed:
ssh 192.168.0.37 "docker restart sastaspace-www"
```

### Prod box (`taxila`) — dead containers stopped
Stopped: `sastaspace-{landing,notes,typewars,admin,deck-static,auth-410}`. Survivors: `sastaspace-{stdb,moderator,workers,www}`.

To free disk on the stopped containers:
```bash
ssh 192.168.0.37 "docker rm sastaspace-landing sastaspace-notes sastaspace-typewars sastaspace-admin sastaspace-deck-static sastaspace-auth-410"
```

### Releases
- v0.1.1, v0.1.2 published with binaries for 5 platforms.
- Homebrew tap (`themohitkhare/homebrew-sastaspace`) up to date with v0.1.2.
- Latest release URLs:
  - https://github.com/themohitkhare/sastaspace/releases/latest
  - `curl -sSf https://sastaspace.com/install.sh | sh`
  - `brew install themohitkhare/sastaspace/sastaspace`
- Binary on `taxila` at `~/.local/bin/sastaspace` (v0.1.2).

### TUI binary (v0.1.2) bug fixes
- Non-TTY panic → graceful exit + `--version` / `--help` flags
- Typewars Esc trap on callsign input → fixed
- Global navigation: `Shift-N/T/D/A/P` between apps
- E2E coverage added for all 4 apps (notes, typewars, deck, admin) + version flag — 17 new scenarios.

---

## ⚠️ Last remaining manual item — Homebrew tap PAT

Auto-publish of the Homebrew formula on every tag still needs a cross-repo PAT. v0.1.1 and v0.1.2 formulas were pushed manually. To make it automatic:

1. Mint a fine-grained PAT at https://github.com/settings/personal-access-tokens/new
   - Resource owner: `themohitkhare`
   - Repository access: only `themohitkhare/homebrew-sastaspace`
   - Repository permissions → Contents: **Read and write**
2. Add as a repo secret on the source repo:
   ```bash
   gh secret set HOMEBREW_TAP_TOKEN --repo themohitkhare/sastaspace --body "<paste-pat>"
   ```
3. Done — next `git tag -a vX.Y.Z && git push origin vX.Y.Z` ships fully automated, including the tap update.

---

## Verify

```bash
# Web
curl -I https://sastaspace.com                    # 200
curl -I https://stdb.sastaspace.com               # 200/upgrade

# Install + run
curl -sSf https://sastaspace.com/install.sh | sh
sastaspace --version                              # sastaspace 0.1.2
sastaspace                                        # opens the TUI

# Or via Homebrew
brew install themohitkhare/sastaspace/sastaspace
sastaspace
```

## Mobile testing (today)

1. Install Termius (or any SSH client) on phone.
2. SSH to `192.168.0.37` (LAN, key auth already set up).
3. Type `sastaspace` — TUI opens.
4. Use `Shift-N/T/D/A/P` to switch between apps. `q` to quit.

For off-LAN access from your phone, set up Cloudflare Access SSH (a UI step I can walk you through if you want).
