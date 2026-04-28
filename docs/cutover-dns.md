# Cut-over status

The TUI migration is code-complete and v0.1.1 is published.

## ✅ Completed (autonomously, in this session)

### Cloudflare DNS — dead app subdomains deleted
The 5 subdomains that pointed at the now-deleted Next.js apps are gone:
- `admin.sastaspace.com` ✅ deleted
- `auth.sastaspace.com` ✅ deleted
- `deck.sastaspace.com` ✅ deleted
- `notes.sastaspace.com` ✅ deleted
- `typewars.sastaspace.com` ✅ deleted

`landing.sastaspace.com` was never created (the landing app was always served from apex).

Survives untouched: `stdb.sastaspace.com`, `api.sastaspace.com`, the apex `sastaspace.com` (still tunnel-routed), `*.sastaspace.com` wildcard, `www.sastaspace.com`, MX/TXT records for Resend.

### Cloudflared tunnel ingress — dead routes removed
Tunnel config (Cloudflare-managed) updated. Ingress went from 9 → 4 entries. Remaining:
| hostname | service |
|---|---|
| `sastaspace.com` | localhost:3110 (apex — see "Apex repoint" below) |
| `www.sastaspace.com` | localhost:3110 |
| `stdb.sastaspace.com` | localhost:3100 |
| _catch-all_ | http_status:404 |

### Prod box (`taxila`) — dead containers stopped
6 dead docker containers stopped:
- `sastaspace-landing`, `sastaspace-notes`, `sastaspace-typewars`, `sastaspace-admin`, `sastaspace-deck-static`, `sastaspace-auth-410`

Survivors (verified `docker ps`):
- `sastaspace-stdb` (healthy)
- `sastaspace-moderator` (healthy)
- `sastaspace-workers` (running; "unhealthy" status is pre-existing — 3 of 4 agents are disabled by env config, healthcheck expects all 4)

If you want the stopped containers gone for good (free disk):
```bash
ssh 192.168.0.37 "docker rm sastaspace-landing sastaspace-notes sastaspace-typewars sastaspace-admin sastaspace-deck-static sastaspace-auth-410"
```

### v0.1.1 release published
- All 5 platform binaries on https://github.com/themohitkhare/sastaspace/releases/tag/v0.1.1
- Homebrew tap published (`themohitkhare/homebrew-sastaspace`) — `brew install themohitkhare/sastaspace/sastaspace`
- Curl installer: `curl -sSf https://github.com/themohitkhare/sastaspace/releases/latest/download/shell-installer.sh | sh`

---

## ⚠️ Remaining — explicit user-facing decisions only

### 1. Apex `sastaspace.com` repoint
Currently still points to `localhost:3110` on taxila, where nothing listens. Visitors get a 502/404. The spec called for repointing to GitHub Pages serving install.sh + README.

**Blocker:** GitHub Pages requires a paid GitHub plan for private repos, and `themohitkhare/sastaspace` is private. Three options, in increasing complexity:

**Option A — Make the repo public.** GH Pages becomes free; once enabled, apex CNAME flips to `themohitkhare.github.io` and Cloudflare flattens it.
- Tradeoffs: history audit (no leaked secrets), ongoing visibility of all code.
- Steps: `gh repo edit themohitkhare/sastaspace --visibility public --accept-visibility-change-consequences`, then `gh api -X POST repos/themohitkhare/sastaspace/pages -f "source[branch]=main" -f "source[path]=/"`. The repo's `CNAME` file (already committed) is picked up automatically. Then via Cloudflare API: change apex DNS target from the tunnel to `themohitkhare.github.io`.

**Option B — Cloudflare Pages.** Connect Cloudflare Pages to the private repo (Cloudflare's GitHub app supports private repos on free plan). Build settings: no build command, output dir = repo root.
- Tradeoffs: requires installing Cloudflare's GH app via UI (one-time browser step at https://dash.cloudflare.com/?to=/:account/pages).
- After that, point apex DNS to the Pages project's *.pages.dev hostname.

**Option C — Tiny static site on `taxila:3110`.** Run an `nginx:alpine` container serving `install.sh` + a rendered README. Apex tunnel route already targets `localhost:3110`, just nothing listens there.
- Tradeoffs: prod-box dependency for the homepage; needs a deploy pipeline; simplest operationally (one `docker run`).

I'd recommend **B** — it's the simplest with the smallest blast radius (no public repo flip, no prod-box dependency).

### 2. Homebrew tap PAT (for future auto-releases)
v0.1.1's formula was pushed manually to the tap. The cargo-dist release workflow's `publish-homebrew-formula` job needs a cross-repo PAT to do this automatically on the next tag:

1. Create a fine-grained PAT at https://github.com/settings/personal-access-tokens/new
   - Resource owner: `themohitkhare`
   - Repository access: only `themohitkhare/homebrew-sastaspace`
   - Repository permissions → Contents: **Read and write**
2. Add to repo secrets:
   ```bash
   gh secret set HOMEBREW_TAP_TOKEN --repo themohitkhare/sastaspace --body "<paste-pat>"
   ```
3. After this, `git tag -a vX.Y.Z && git push origin vX.Y.Z` is enough — full release including tap update.

---

## Verify the binary

```bash
brew install themohitkhare/sastaspace/sastaspace
sastaspace                       # opens portfolio splash; q to quit
```
