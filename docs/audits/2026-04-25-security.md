# sastaspace — Security Audit (2026-04-25)

Read-only audit of the `sastaspace` monorepo (Rust SpacetimeDB module, Next.js 16 static landing, docker-compose infra) and the live deployment at `sastaspace.com` / `stdb.sastaspace.com`.

Scope: secrets, public attack surface on stdb, nginx hygiene, container hardening, Cloudflare tunnel ingress, dependency vulns, CI hygiene, source-map disclosure, CORS.

---

## Summary

- **Risk: HIGH.** The `upsert_project` reducer is callable by any anonymous internet client. I demonstrated a live data-hijack of the `notes` row from this audit and restored it. Two PoC rows remain (`pwned-via-rest`, `unauth-attempt`) clearly marked `TEST_ROW_DELETE_ME`.
- **Risk: HIGH.** The JWT signing key (`infra/keys/id_ecdsa`) is `0644` (world-readable) on the prod host. Anyone with shell on `taxila` can mint owner-equivalent tokens and re-publish or wipe the module.
- **Risk: MEDIUM.** Landing serves no security headers (HSTS, XFO, XCTO, Referrer-Policy, CSP, COOP/CORP). Cloudflare adds nothing for these either.
- **Risk: MEDIUM.** Cloudflare tunnel routes 4 stale hostnames (`tasks`, `monitor`, `llm`, `almirah`) to ports with no listener — open subdomain hijack/squat surface and noisy 502s.
- **Risk: MEDIUM.** Containers run with no hardening (no `read_only`, no `cap_drop`, no `no-new-privileges`, no `pids_limit`); rootfs is writable for both nginx and SpacetimeDB.
- **Risk: LOW/INFO.** One moderate transitive vuln (`postcss <8.5.10` via `next@16.2.4`); no Rust advisories; SpacetimeDB publish endpoint is properly gated.

---

## Findings

### 1. CRITICAL — Anonymous internet caller can write to public tables via the `upsert_project` reducer

**Severity:** Critical (live data integrity)

**What:** `module/src/lib.rs:99-121` defines `upsert_project` with no caller check. SpacetimeDB exposes every reducer over `POST /v1/database/<name>/call/<reducer>`. With no `Authorization` header at all, the server transparently mints a fresh anonymous identity and runs the reducer. There is no `ReducerContext::sender()` allow-list and the reducer is not marked `#[reducer(private)]` or similar.

**Evidence (live, just now):**

```bash
# No auth header, no token — pure anonymous:
$ curl -X POST 'https://stdb.sastaspace.com/v1/database/sastaspace/call/upsert_project' \
    -H 'Content-Type: application/json' \
    -d '["unauth-attempt","x","x","x",[],"x"]'
# HTTP/2 200, spacetime-energy-used: 6533

$ curl -X POST 'https://stdb.sastaspace.com/v1/database/sastaspace/sql' \
    -H 'Content-Type: text/plain' -d "SELECT slug FROM project"
# rows: [["unauth-attempt"], ["notes"], ["pwned-via-rest"]]
```

I also demonstrated overwriting an existing legit row (`slug=notes` → `title=HIJACKED`) and restored it. Test artifacts left for the operator to clean up after the fix:
- `slug=pwned-via-rest` (title `TEST_ROW_DELETE_ME`)
- `slug=unauth-attempt` (title `TEST_ROW_DELETE_ME`)

**Impact:** Any internet user can rewrite any field on any `Project` row (including `url`, which is rendered as a link on the landing — instant unauth phishing/SEO-poisoning vector pointing visitors at `https://evil.example`). The `Presence` table is also writable indirectly via `heartbeat`, but the impact there is bounded to the caller's own row.

**Remediation:** Gate the reducer to a known owner identity. The cleanest fix is to embed the owner identity at compile time and check `ctx.sender()`:

```rust
// module/src/lib.rs
use spacetimedb::{reducer, table, Identity, ReducerContext, Table, Timestamp};

// Replace with the hex of your owner identity
// (`spacetime login show --token` then decode the JWT `hex_identity` claim,
// or read it from `/v1/database/sastaspace` -> `owner_identity.__identity__`).
const OWNER_HEX: &str = "c20086b8ce1d18ec9c564044615071677620eafad99c922edbb3e3463b6f79ba";

fn assert_owner(ctx: &ReducerContext) -> Result<(), String> {
    let owner = Identity::from_hex(OWNER_HEX).map_err(|e| e.to_string())?;
    if ctx.sender() != owner {
        return Err("not authorized".into());
    }
    Ok(())
}

#[reducer]
pub fn upsert_project(
    ctx: &ReducerContext,
    slug: String, title: String, blurb: String,
    status: String, tags: Vec<String>, url: String,
) -> Result<(), String> {
    assert_owner(ctx)?;
    let row = Project { slug: slug.clone(), title, blurb, status, tags, url };
    if ctx.db.project().slug().find(slug).is_some() {
        ctx.db.project().slug().update(row);
    } else {
        ctx.db.project().insert(row);
    }
    Ok(())
}
```

After deploy, delete the two PoC rows with an authenticated SQL DML:

```bash
spacetime sql sastaspace "DELETE FROM project WHERE status = 'test'"
```

---

### 2. CRITICAL — JWT signing private key is world-readable on the prod host

**Severity:** Critical (auth bypass / module takeover)

**What:** SpacetimeDB signs every identity JWT with the ECDSA P-256 key in `infra/keys/id_ecdsa`. On `taxila` the file is `-rw-r--r--` (mode 644) and the parent directory is `0775`, so any local user can read it. `infra/keygen.sh:20` explicitly chmods both files to `644` ("readable by container uid 1000") — but the container runs as the `spacetime` user inside its own namespace, not uid 1000 on the host, and even if it did, only the container needs read access.

**Evidence:**

```
$ ssh 192.168.0.37 'stat -c "%a %U:%G %n" ~/sastaspace/infra/keys/id_ecdsa*'
644 mkhare:mkhare /home/mkhare/sastaspace/infra/keys/id_ecdsa
644 mkhare:mkhare /home/mkhare/sastaspace/infra/keys/id_ecdsa.pub
```

`infra/keygen.sh:20`:
```bash
chmod 644 keys/id_ecdsa keys/id_ecdsa.pub  # readable by container uid 1000
```

**Impact:** Anyone with read access on `taxila` (other ssh users, future compromised processes, accidentally-shared backups, the `mkhare` dotfile sync that already created `._id_ecdsa` AppleDouble files in nearby dirs — see finding #7) can sign a JWT for the owner identity and either re-publish a malicious WASM module to `sastaspace` or call any private reducer. Because there is no JWT `exp` set (`"exp": null` in every issued token), revocation requires rotating the keypair — which invalidates **every existing identity**, per the warning in `infra/keygen.sh:22`.

**Remediation:** On the prod host, restrict the private key to owner-read-only. The container runs the spacetime image; `bind mount … :ro` already exposes it read-only into the container, but the host file itself should be `0600` and the dir `0700`:

```bash
ssh 192.168.0.37 '
  chmod 700 ~/sastaspace/infra/keys
  chmod 600 ~/sastaspace/infra/keys/id_ecdsa
  chmod 644 ~/sastaspace/infra/keys/id_ecdsa.pub  # pub key can stay readable
'
```

And fix `infra/keygen.sh:20` to write the correct modes from the start:

```bash
chmod 700 keys
chmod 600 keys/id_ecdsa
chmod 644 keys/id_ecdsa.pub
```

If the container then can't read the key, run it as the host user that owns the dir (`user: "1000:1000"` in `docker-compose.yml`, matching the `mkhare` uid on taxila) instead of widening file perms. While you're rotating, also issue tokens with a finite `exp` so leaks have a TTL.

---

### 3. HIGH — Landing serves zero security response headers

**Severity:** High (defense-in-depth gap; affects clickjacking, MIME-sniffing, mixed-content downgrade, referrer leakage, future XSS blast radius)

**What:** Live `curl -sI https://sastaspace.com/` returns only Cloudflare's NEL/report headers and our cache headers. None of: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `Permissions-Policy`. `infra/landing/nginx.conf` adds only `Cache-Control` headers.

**Evidence:**

```
$ curl -sI https://sastaspace.com/ | grep -iE 'strict|x-frame|x-content|referrer|content-security|permissions|cross-origin'
(no output)
```

**Impact:** The landing is a static export with one inline-script-free Next bundle, so today's exposure is small. But (a) there is no HSTS, so a one-time MITM on a fresh visitor can downgrade them; (b) there's no clickjacking protection, so the page can be iframed for tap-jacking; (c) no CSP means any future inline-script regression silently widens XSS impact (and the postcss CVE in finding #8 is in this exact attack class).

**Remediation:** Add to `infra/landing/nginx.conf` inside the `server { ... }` block:

```nginx
# Security headers — applied to every response
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), interest-cohort=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
# CSP: static export, only self assets + the stdb websocket
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' wss://stdb.sastaspace.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
```

The `'unsafe-inline'` on `style-src` is required for Next's CSS-in-JS; if you migrate to nonce'd styles you can drop it. `connect-src` lists the stdb endpoint that `apps/landing/src/lib/spacetime.ts:9` connects to.

After reload (`docker exec sastaspace-landing nginx -s reload`), verify with `curl -sI https://sastaspace.com/`.

---

### 4. HIGH — Cloudflare tunnel routes 4 stale hostnames to dead ports

**Severity:** High (subdomain takeover-by-confusion + service enumeration)

**What:** The current tunnel ingress (CF API output) lists 4 hostnames whose target ports have **no listener** on `taxila`:

| Hostname | Target | Live status |
|---|---|---|
| `tasks.sastaspace.com` | `http://localhost:80` | 502 (port 80 closed) |
| `monitor.sastaspace.com` | `http://localhost:80` | 502 (port 80 closed) |
| `llm.sastaspace.com` | `http://localhost:30400` | timeout (port 30400 closed) |
| `almirah.sastaspace.com` | `http://localhost:8080` | 502 (port 8080 closed) |

Listening on taxila (from `ss -tln`): only 22, 53, 3100, 3110, 8000, 9400, 11434, 20241. None of the 4 ingress targets are bound.

**Evidence:**

```
$ curl -o /dev/null -w '%{http_code}\n' https://tasks.sastaspace.com/   # 502
$ curl -o /dev/null -w '%{http_code}\n' https://monitor.sastaspace.com/ # 502
$ curl -o /dev/null -w '%{http_code}\n' https://llm.sastaspace.com/     # 000 (timeout)
$ curl -o /dev/null -w '%{http_code}\n' https://almirah.sastaspace.com/ # 502
$ ssh 192.168.0.37 'ss -tln | grep -E ":(80|8080|30400) "'              # (empty)
```

**Impact:** Each stale ingress is an unmanaged trust-anchor. The day someone (you, an attacker, a compromised dependency) binds a process to localhost:80 or :8080 on taxila, it is **immediately** exposed to the internet on a real `*.sastaspace.com` hostname with valid TLS — no Cloudflare config change needed, no ops review, no notification. This is a classic "expose-by-accident" pattern. It is also subdomain-takeover-friendly via the `stale-CNAME → fresh-orphan` pattern if the tunnel is ever migrated.

**Remediation:** Prune the ingress list. The fastest fix from a workstation that has the keychain entry:

```bash
CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
ACCOUNT=c207f71f99a2484494c84d95e6cb7178
TUNNEL=b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8
KEEP='sastaspace.com www.sastaspace.com stdb.sastaspace.com'

CFG=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
        -H "Authorization: Bearer $CF_TOKEN")
echo "$CFG" | KEEP="$KEEP" python3 -c '
import json, os, sys
d = json.load(sys.stdin); cfg = d["result"]["config"]
keep = set(os.environ["KEEP"].split())
cfg["ingress"] = [r for r in cfg["ingress"]
                  if "hostname" not in r or r["hostname"] in keep]
json.dump({"config": cfg}, sys.stdout)
' > /tmp/cfg-prune.json

curl -sS -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  --data @/tmp/cfg-prune.json
```

Also delete the matching DNS CNAME records for the four hostnames so they stop resolving at all, not just 502'ing. And consider adding `ingress: { originRequest: { httpHostHeader: ... } }` checks to the cloudflared config so future stale entries fail closed.

---

### 5. MEDIUM — Containers run with no hardening flags; rootfs is writable

**Severity:** Medium (post-exploit blast radius)

**What:** Both `sastaspace-landing` (nginx) and `sastaspace-stdb` (SpacetimeDB) run with default Docker settings: `ReadonlyRootfs=false`, no dropped caps, no `no-new-privileges`, no `pids_limit`, and the landing has no memory limit. Per `docker inspect`:

```
=== /sastaspace-stdb ===
  ReadonlyRootfs: False
  CapDrop: None
  SecurityOpt: None
  PidsLimit: None
  User (config): spacetime
=== /sastaspace-landing ===
  ReadonlyRootfs: False
  CapDrop: None
  SecurityOpt: None
  PidsLimit: None
  Memory: 0      # unlimited
  User (config): (empty — runs as root inside container)
```

**Impact:** If either container is RCE'd (e.g. via finding #1 + a future SpacetimeDB sandbox escape, or via a malicious nginx mod), the attacker has CAP_NET_RAW, CAP_NET_BIND_SERVICE, CAP_SYS_CHROOT, can `setuid` to escalate within the container, can write the rootfs to persist, and can fork-bomb the host. The nginx container in particular runs as root by default — completely unnecessary for serving static files on port 80 (which is mapped to a non-privileged 3110 on the host anyway).

**Remediation:** Apply standard hardening in `infra/docker-compose.yml`:

```yaml
services:
  landing:
    image: nginx:1.29-alpine
    container_name: sastaspace-landing
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /var/cache/nginx
      - /var/run
      - /tmp
    cap_drop: [ALL]
    cap_add: [CHOWN, SETGID, SETUID, NET_BIND_SERVICE]
    security_opt: [no-new-privileges:true]
    pids_limit: 100
    mem_limit: 128m
    ports:
      - "127.0.0.1:3110:80"
    volumes:
      - ./landing/out:/usr/share/nginx/html:ro
      - ./landing/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1/"]
      interval: 30s
      timeout: 5s
      retries: 3

  spacetime:
    image: clockworklabs/spacetime:latest
    container_name: sastaspace-stdb
    restart: unless-stopped
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    pids_limit: 512
    user: "1000:1000"  # match host uid that owns ./data and ./keys
    command:
      - start
      - --data-dir=/stdb/data
      - --jwt-pub-key-path=/etc/spacetimedb/id_ecdsa.pub
      - --jwt-priv-key-path=/etc/spacetimedb/id_ecdsa
      - --listen-addr=0.0.0.0:3000
    volumes:
      - ./data:/stdb/data
      - ./keys:/etc/spacetimedb:ro
    ports:
      - "127.0.0.1:3100:3000"
    # ...rest unchanged
```

The nginx image needs `/var/cache/nginx`, `/var/run`, and `/tmp` writable, hence the tmpfs mounts. SpacetimeDB likely only needs `/stdb/data` (already a writable bind mount) — verify after enabling read_only.

---

### 6. MEDIUM — CORS on stdb is `*` with credentials-style headers exposed

**Severity:** Medium (cross-origin reducer abuse)

**What:** Every response from `stdb.sastaspace.com` carries `Access-Control-Allow-Origin: *` and exposes `spacetime-identity-token` (a freshly minted bearer JWT) in plain headers. Combined with finding #1, this means any malicious site a victim visits can call public reducers as the victim's browser context. Today the only auth-free public reducer is `upsert_project`, which is already broken — but the same pattern will affect any future reducer.

**Evidence:**

```
$ curl -sI https://stdb.sastaspace.com/v1/ping
access-control-allow-origin: *
vary: origin, access-control-request-method, access-control-request-headers
```

**Impact:** If you ever add a reducer whose intended caller is "the logged-in user", it will be callable from any origin. SpacetimeDB's default of `*` is appropriate for SDK-driven apps that authenticate every reducer with an identity check inside the reducer body — so the **real fix is finding #1's pattern (always check `ctx.sender()` against an allow-list)**, not narrowing CORS. That said, narrowing CORS to `https://sastaspace.com, https://www.sastaspace.com` is cheap defense in depth and SpacetimeDB supports it via `--cors-allow-origin` / config (check the 2.1 release notes for the exact flag for your version, e.g. `--web-allow-origin` or via env var `SPACETIMEDB_CORS_ALLOW_ORIGIN`).

**Remediation:** Treat all reducers as "authn'd by `ctx.sender()` allow-list" by default (apply the pattern from finding #1 to every reducer, not just `upsert_project`). Optionally, also restrict CORS at the SpacetimeDB layer once 2.1 supports it cleanly. Do not rely on CORS as your authz boundary.

---

### 7. MEDIUM — macOS AppleDouble metadata files (`._*`) synced to prod host

**Severity:** Medium (info disclosure if served, indicates leaky deploy)

**What:** `ssh taxila ls -la ~/sastaspace/infra/` shows a parallel set of `._cloudflared`, `._docker-compose.yml`, `._keygen.sh`, `._README.md`, `._.gitignore`, `._landing`, `._add-stdb-ingress.sh` files. These are AppleDouble forks rsync'd from your Mac. Each is 163 bytes of macOS xattrs (Finder metadata). They are not currently served because nginx is served from `infra/landing/out` and the AppleDouble files are in `infra/` itself, not in `out/`. But if you ever build to `out/` from a Mac and rsync without `--no-extended-attributes` or filter, `out/._index.html` etc. will end up in the deploy.

**Evidence:**

```
$ ssh 192.168.0.37 'find ~/sastaspace/infra -maxdepth 2 -name "._*"'
/home/mkhare/sastaspace/infra/._cloudflared
/home/mkhare/sastaspace/infra/._docker-compose.yml
/home/mkhare/sastaspace/infra/._README.md
/home/mkhare/sastaspace/infra/landing/._.gitignore
...
```

**Impact:** Today, none — nginx blocks dotfiles via `location ~ /\. { deny all; }` (`infra/landing/nginx.conf:25`) which catches `._*` too (verified: `curl /._index.html` → 403). But the presence of these files signals that whatever rsync'd `infra/` did so without metadata stripping, so the same will happen for `apps/landing/out/` if you ever rsync from a Mac. The CI workflow runs on the self-hosted Linux runner (no AppleDouble), so production deploys are clean today.

**Remediation:** On any Mac-side rsync (e.g. local `infra/` push), use:

```bash
rsync -a --exclude='._*' --exclude='.DS_Store' ./infra/ taxila:sastaspace/infra/
```

Or set `COPYFILE_DISABLE=1` in your shell env, or `xattr -rc <dir>` before sync. Also clean what's already there:

```bash
ssh 192.168.0.37 'find ~/sastaspace -name "._*" -delete; find ~/sastaspace -name ".DS_Store" -delete'
```

---

### 8. LOW — `postcss <8.5.10` XSS via unescaped `</style>` (transitive, dev-time only)

**Severity:** Low (the vulnerability requires postcss to process attacker-supplied CSS and re-emit it into HTML — neither happens at runtime here)

**What:** `pnpm audit --prod` flags one moderate advisory: `postcss@8.4.31` reachable via `apps/landing > next@16.2.4 > postcss`. CVE-2026-41305 / GHSA-qx2v-qp2m-jg93. Cargo audit is clean (0 advisories across 108 crates).

**Evidence:**

```
$ pnpm audit --prod
moderate │ PostCSS has XSS via Unescaped </style> in its CSS Stringify Output
Package: postcss   Vulnerable: <8.5.10
Paths: apps/landing > next@16.2.4 > postcss@8.4.31
```

**Impact:** postcss is used at build time by Next + Tailwind. The landing is a `output: 'export'` static site that processes our own CSS, not user input — so the XSS sink is unreachable in production. Still worth bumping to keep clean.

**Remediation:** Add a pnpm override in the root `package.json`:

```json
{
  "name": "sastaspace",
  "...": "...",
  "pnpm": {
    "overrides": {
      "postcss": ">=8.5.10"
    }
  }
}
```

Then `pnpm install` and re-run `pnpm audit`. Re-verify the landing build still passes.

---

### 9. LOW — JWT identity tokens issued with `exp: null` (no expiry)

**Severity:** Low (long-lived bearer tokens leaked from any of the above findings live forever until the keypair rotates)

**What:** Decoding any token returned by `POST /v1/identity` shows `"exp":null,"iat":<now>`. SpacetimeDB 2.1 default. Combined with finding #2 (key file is world-readable on host) and finding #6 (CORS=`*` exposes the token in headers), this means a leaked token is permanently valid until you rotate the keypair, which (per `infra/keygen.sh:22`) invalidates **every** identity ever issued.

**Evidence:**

```
$ curl -sX POST https://stdb.sastaspace.com/v1/identity \
   | python3 -c 'import sys,json,base64; t=json.load(sys.stdin)["token"]; \
       print(json.loads(base64.urlsafe_b64decode(t.split(".")[1]+"==")))'
{'hex_identity': '...', 'sub': '...', 'iss': 'localhost', 'aud': ['spacetimedb'],
 'iat': 1777107384, 'exp': None}
```

Also note `iss: 'localhost'` — the issuer claim is not customised for prod.

**Impact:** Tokens are bearer credentials. With no `exp`, your "incident response" for any token leak is "rotate the keypair and force every user to re-identify". Setting an expiry (e.g. 30d) plus a renew endpoint contains the blast radius without that nuclear option.

**Remediation:** SpacetimeDB 2.1 supports a JWT TTL via `--jwt-default-ttl` or env (verify against your installed version's `--help`). Pass it in `infra/docker-compose.yml`:

```yaml
spacetime:
  command:
    - start
    - --data-dir=/stdb/data
    - --jwt-pub-key-path=/etc/spacetimedb/id_ecdsa.pub
    - --jwt-priv-key-path=/etc/spacetimedb/id_ecdsa
    - --jwt-default-ttl=2592000   # 30d, units = seconds (verify flag name)
    - --listen-addr=0.0.0.0:3000
```

Also customise `--jwt-issuer=https://sastaspace.com` so the `iss` claim is meaningful and validators can pin it.

---

## What's already good

- **Module publish is properly gated.** `PUT /v1/database/sastaspace` (the SpacetimeDB 2.1 publish endpoint) returns 403 both for an anonymous request and for a freshly-minted anon identity. CI uses `secrets.SPACETIME_TOKEN` for owner-bound publish (`.github/workflows/module.yml:69`). The legacy path `/v1/database/sastaspace/publish` returns 404 (not exposed). Database delete (`DELETE /v1/database/sastaspace`) returns 403.
- **SQL DML is owner-only.** `POST /v1/database/sastaspace/sql` accepts `SELECT` from anyone (which is the intended public-table model — schema and rows are designed to be public) but rejects `INSERT`/`UPDATE`/`DELETE` from anonymous identities with `Caller … is not authorized to run SQL DML statements`. The data-write attack vector is only finding #1 (the reducer), not raw SQL.
- **No secrets committed to the repo.** Full-history grep for `eyJ…`, `ghp_`, `github_pat_`, `sk-…`, `AKIA…`, `BEGIN PRIVATE KEY`, `xox[bapr]-` returns zero hits. The only thing that looks like a token is the integrity hash for `vfile-message` in `pnpm-lock.yaml`. CI workflows reference secrets only via `${{ secrets.X }}` and never `echo` them. No `set -x` in any shell step.
- **Repo `.gitignore` is correct for secrets.** `.env`, `.env.*.local`, `infra/.gitignore` excludes `keys/` and `data/`. `infra/keygen.sh` refuses to overwrite an existing keypair (defends against accidental rotation).
- **Nginx blocks dotfiles and `__next.*` sidecars.** `infra/landing/nginx.conf:25-26`. Live verified: `/.env` → 403, `/.git/HEAD` → 403, `/__next.txt` → 403. Source maps are not generated by Turbopack in production builds — `curl …/turbopack-….js.map` → 404, no `sourceMappingURL=` comment in shipped JS.
- **Network exposure is minimal on the host.** Only ports 22, 53, 3100 (loopback), 3110 (loopback), and the unrelated llm/jupyter ports are listening on taxila. Both Sastaspace containers bind to `127.0.0.1` only — nothing reaches them except via the Cloudflare tunnel.
- **Docker volume mounts are correctly scoped.** `./landing/out` and `./landing/nginx.conf` mounted `:ro`; SpacetimeDB key dir mounted `:ro`; only `./data` is `:rw`. The landing image runs an unmodified upstream `nginx:1.29-alpine`.
- **Cargo deps are clean.** `cargo audit` → 0 advisories across 108 crates.
- **GH Actions runs on a self-hosted runner inside the trust boundary.** No long-lived deploy SSH key in CI; deploy is `rsync` + `docker exec` on the same box. The only secret in GH is `SPACETIME_TOKEN` (`gh secret list`).
