# Cutover Runbook: MicroK8s nginx-ingress → kamal-proxy

**Version:** 1.0  
**Date:** 2026-04-24  
**Applies to:** sastaspace.com path-routed Rails migration (design-log 006)

---

## Overview

This runbook flips `sastaspace.com` (and `www.sastaspace.com`) from the current
MicroK8s nginx-ingress stack to kamal-proxy running directly on the host. The
Cloudflare tunnel entry for `sastaspace.com` currently points at
`http://localhost:80`, which is nginx-ingress. After cutover it points at the
same address — kamal-proxy also binds port 80 — but nginx-ingress is stopped
first so there is no conflict.

The entire change is a single Cloudflare API call (Step 1b) plus stopping one
k8s service. Rollback is reversing both in the opposite order.

**Estimated downtime:** 10–30 seconds (time to run Step 1b and for the
tunnel to propagate the new routing target to Cloudflare's edge). In practice
kamal-proxy will already be serving traffic on port 8080 during pre-flight, so
the gap is purely the port swap.

**Estimated rollback time:** 5 minutes (restart nginx-ingress NodePort,
re-point Cloudflare tunnel entry back to port 80).

---

## Prerequisites

These must be true before starting the cutover. Verify each one.

```
[ ] 1. Rails landing app container built and pushed to localhost:32000/sastaspace-landing-rails:latest
[ ] 2. Rails almirah app container built and pushed to localhost:32000/sastaspace-almirah-rails:latest
[ ] 3. kamal-proxy is running on the host (verify: ssh 192.168.0.37 "docker ps | grep kamal-proxy")
[ ] 4. kamal-proxy is bound to port 8080 (NOT 80) during pre-flight to avoid nginx-ingress conflict
[ ] 5. Both Rails apps deployed via `kamal deploy` and healthy on port 8080 (curl http://192.168.0.37:8080/ and curl http://192.168.0.37:8080/almirah/up both return 200)
[ ] 6. Cloudflare API token available: CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
[ ] 7. Postgres is still running: ssh 192.168.0.37 "sudo microk8s kubectl -n sastaspace get pod -l app=postgres"
[ ] 8. Git branch team5/kamal-deploy-path-routing is merged to develop; CI has run once.
```

**Environment variables** (set these in your shell before running steps):

```bash
export CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
export ZONE=f90dcc0f12180c1d2b5fb5d488887c24
export ACCOUNT=c207f71f99a2484494c84d95e6cb7178
export TUNNEL=b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8
export HOST=192.168.0.37
```

---

## Step 0 — Snapshot current tunnel ingress config (safety checkpoint)

Before touching anything, save the current tunnel config to disk. If something
goes wrong you can restore from this file.

```bash
curl -sS \
  "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" \
  | python3 -m json.tool > /tmp/tunnel-config-before-cutover.json

echo "Saved $(wc -c < /tmp/tunnel-config-before-cutover.json) bytes"
# Should be several hundred bytes — if it's tiny, the token or account ID is wrong.
```

Verify the current ingress list looks like:

```
sastaspace.com      → http://localhost:80
almirah.sastaspace.com → http://localhost:80
...
<catchall>          → http_status:404
```

---

## Step 1 — Stop nginx-ingress and hand port 80 to kamal-proxy

### Step 1a — Scale nginx-ingress NodePort to 0

nginx-ingress binds port 80 on the host via a NodePort/DaemonSet. We scale it
to 0 replicas so port 80 is freed.

```bash
# Check current nginx-ingress controller name
ssh $HOST "sudo microk8s kubectl -n ingress get pod"

# Scale the ingress controller daemonset/deployment to 0
# MicroK8s typically uses ingress-nginx-controller as a DaemonSet:
ssh $HOST "sudo microk8s kubectl -n ingress scale deployment nginx-ingress-microk8s-controller --replicas=0 2>/dev/null || \
           sudo microk8s kubectl -n ingress patch daemonset nginx-ingress-microk8s-controller \
             -p '{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"non-existing\":\"true\"}}}}}'"

# Verify port 80 is free (should time out or refuse):
ssh $HOST "sudo ss -tlnp | grep ':80 '"
```

Wait for nginx-ingress pods to terminate:

```bash
ssh $HOST "sudo microk8s kubectl -n ingress get pod --watch"
# Ctrl-C when all pods show Terminating → gone
```

### Step 1b — Rebind kamal-proxy from 8080 to 80

kamal-proxy was running on 8080 during pre-flight. Now that port 80 is free,
rebind it. The cleanest way is to restart the kamal-proxy container with the
correct port binding.

```bash
# Restart kamal-proxy on port 80 (kamal-proxy boot handles the port argument)
ssh $HOST "docker stop kamal-proxy && docker rm kamal-proxy"
ssh $HOST "docker run -d \
  --name kamal-proxy \
  --restart unless-stopped \
  --network kamal \
  -p 80:80 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  basecamp/kamal-proxy:latest \
  run --port=80"

# Wait ~5 seconds for it to come up, then verify
sleep 5
ssh $HOST "docker ps | grep kamal-proxy"
curl -sI http://$HOST/ | head -5
```

At this point Cloudflare tunnel → localhost:80 → kamal-proxy → Rails landing.
The Cloudflare tunnel config does NOT need to change because it already points
at `http://localhost:80`.

### Step 1c — Smoke-test through kamal-proxy on port 80

```bash
# Direct on host (bypasses Cloudflare):
curl -sI http://$HOST/ | grep -E "HTTP|location"
curl -sI http://$HOST/almirah/up | grep -E "HTTP|location"

# Through Cloudflare (requires DNS to propagate — usually immediate):
curl -sI https://sastaspace.com/ | grep "HTTP"
curl -sI https://sastaspace.com/almirah/up | grep "HTTP"
```

Expected results:
- `GET /` → 200 (Rails landing root)  
- `GET /almirah/up` → 200 (Rails health check)  
- Both through Cloudflare respond with `server: cloudflare`

---

## Step 2 — Verify

Run these in order. All must pass before proceeding to Step 3.

```bash
# 2.1 Landing root
STATUS=$(curl -so /dev/null -w "%{http_code}" https://sastaspace.com/)
[ "$STATUS" = "200" ] && echo "PASS landing root" || echo "FAIL landing root: $STATUS"

# 2.2 Landing project list (reads from public.projects via ActiveRecord)
STATUS=$(curl -so /dev/null -w "%{http_code}" https://sastaspace.com/projects)
[ "$STATUS" = "200" ] && echo "PASS projects page" || echo "FAIL projects page: $STATUS"

# 2.3 Almirah root
STATUS=$(curl -so /dev/null -w "%{http_code}" https://sastaspace.com/almirah)
[ "$STATUS" = "200" ] && echo "PASS almirah root" || echo "FAIL almirah root: $STATUS"

# 2.4 Almirah health check
STATUS=$(curl -so /dev/null -w "%{http_code}" https://sastaspace.com/almirah/up)
[ "$STATUS" = "200" ] && echo "PASS almirah health" || echo "FAIL almirah health: $STATUS"

# 2.5 Check response header — must NOT contain x-powered-by: Next.js
curl -sI https://sastaspace.com/ | grep -i "x-powered-by" && echo "WARN: still Next.js?" || echo "PASS no Next.js header"

# 2.6 kamal-proxy container still running
ssh $HOST "docker ps --filter name=kamal-proxy --format '{{.Status}}'"
```

---

## Step 3 — Redirect almirah.sastaspace.com to sastaspace.com/almirah

The old subdomain `almirah.sastaspace.com` should return a permanent 301
redirect so old bookmarks and links continue to work for 30 days before the
DNS record is cleaned up.

**Option A — Cloudflare Page Rule (recommended, no extra container):**

Cloudflare Page Rules can issue 301 redirects without touching the origin.

```bash
# Create a Forwarding URL page rule
curl -X POST \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/pagerules" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "targets": [
      {
        "target": "url",
        "constraint": {
          "operator": "matches",
          "value": "almirah.sastaspace.com/*"
        }
      }
    ],
    "actions": [
      {
        "id": "forwarding_url",
        "value": {
          "url": "https://sastaspace.com/almirah/$1",
          "status_code": 301
        }
      }
    ],
    "status": "active",
    "priority": 1
  }'
```

Verify:

```bash
curl -sI https://almirah.sastaspace.com/ | grep -E "HTTP|location"
# Expected:
# HTTP/2 301
# location: https://sastaspace.com/almirah/
```

**Option B — Tiny nginx redirect container via Kamal accessory** (if the free
Page Rule limit is exhausted):

```yaml
# Add to projects/landing-rails/config/deploy.yml under accessories:
accessories:
  almirah-redirect:
    image: nginx:alpine
    host: 192.168.0.37
    port: "3099:80"
    files:
      - config/nginx-almirah-redirect.conf:/etc/nginx/conf.d/default.conf
```

With `config/nginx-almirah-redirect.conf`:
```nginx
server {
    listen 80;
    server_name almirah.sastaspace.com;
    return 301 https://sastaspace.com/almirah$request_uri;
}
```

Then update the tunnel ingress for `almirah.sastaspace.com` to point at
`http://localhost:3099` instead of port 80.

**Cleanup schedule:** Delete the `almirah.sastaspace.com` DNS record and tunnel
hostname entry 30 days after cutover, once access logs confirm zero organic
traffic to the old subdomain.

---

## Step 4 — Scale down (not delete) old Next.js deployments

Scale to 0 replicas to free CPU/memory. Do NOT delete yet — keep as rollback
option for 48 hours.

```bash
ssh $HOST "sudo microk8s kubectl -n sastaspace scale deployment landing --replicas=0"
ssh $HOST "sudo microk8s kubectl -n sastaspace scale deployment almirah --replicas=0"

# Verify
ssh $HOST "sudo microk8s kubectl -n sastaspace get deployment landing almirah"
# Both should show 0/0 READY
```

After 48 hours of stable Rails operation, run `scripts/k8s-teardown.sh` to
clean up the remaining k8s resources (see that script for details).

---

## Rollback — Re-point Cloudflare to nginx-ingress

If the Rails stack is broken and you need to go back to Next.js immediately:

### Rollback Step 1 — Restart nginx-ingress

```bash
# Re-enable the DaemonSet selector (reverses the patch from Step 1a):
ssh $HOST "sudo microk8s kubectl -n ingress patch daemonset nginx-ingress-microk8s-controller \
  -p '{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{}}}}}'"

# Or if it was a Deployment:
ssh $HOST "sudo microk8s kubectl -n ingress scale deployment nginx-ingress-microk8s-controller --replicas=1"

# Scale Next.js deployments back up:
ssh $HOST "sudo microk8s kubectl -n sastaspace scale deployment landing --replicas=1"
ssh $HOST "sudo microk8s kubectl -n sastaspace scale deployment almirah --replicas=1"
```

### Rollback Step 2 — Stop kamal-proxy (frees port 80)

```bash
ssh $HOST "docker stop kamal-proxy"
```

### Rollback Step 3 — Verify nginx-ingress owns port 80

```bash
ssh $HOST "sudo ss -tlnp | grep ':80 '"
# Should show nginx worker process

curl -sI https://sastaspace.com/ | grep "HTTP"
# Should return 200 from Next.js landing
```

Entire rollback takes approximately 5 minutes. The Cloudflare tunnel ingress
config does NOT need to change for rollback because it always points at
`localhost:80` — the question is just which process owns that port.

---

## Appendix A — Cloudflare tunnel ingress management

The tunnel config lives entirely on Cloudflare's side. To inspect or modify:

```bash
# Read current config
curl -sS \
  "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" | python3 -m json.tool

# The ingress array is ordered. The last entry has no "hostname" field
# (the catch-all http_status:404). Always insert before it.
```

To add a new path-prefixed app's subdomain redirect (for future cleanup of any
remaining subdomain entries), use the Python snippet from CLAUDE.md to safely
insert before the catch-all without overwriting the array.

**Known gotcha:** A Cloudflare account ID typo returns error 7003 "Could not
route" which looks like a permissions error. Always pull the account ID from
`GET /zones/{zone}` → `.result.account.id` rather than decoding the tunnel
token by hand.

---

## Appendix B — Adding a future app at sastaspace.com/<name>

Post-cutover, adding a new path-prefixed Rails app requires exactly two things:

1. Deploy the app via `kamal deploy` from `projects/<name>/`. kamal-proxy
   detects the `kamal-proxy.path_prefix` label and starts routing automatically.
   No Cloudflare changes needed.

2. If the app had an old subdomain (`<name>.sastaspace.com`), add a Cloudflare
   Page Rule 301 redirect matching `<name>.sastaspace.com/*` → 
   `https://sastaspace.com/<name>/$1`.

No DNS changes, no tunnel ingress changes, no nginx-ingress ConfigMaps.

---

## Appendix C — CI/CD with Kamal (Option D4b, future)

If you later want GitHub Actions to deploy instead of local `kamal deploy`:

```yaml
# .github/workflows/deploy.yml (future D4b version)
name: Deploy via Kamal
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3'
          bundler-cache: true
      - name: Install Kamal
        run: gem install kamal
      - name: Set up SSH key
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.DEPLOY_SSH_KEY }}
      - name: Deploy landing
        working-directory: projects/landing-rails
        env:
          RAILS_MASTER_KEY: ${{ secrets.RAILS_MASTER_KEY_LANDING }}
          DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          REGISTRY_USERNAME: unused
          REGISTRY_PASSWORD: unused
        run: kamal deploy
      - name: Deploy almirah
        working-directory: projects/almirah-rails
        env:
          RAILS_MASTER_KEY: ${{ secrets.RAILS_MASTER_KEY_ALMIRAH }}
          DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          REGISTRY_USERNAME: unused
          REGISTRY_PASSWORD: unused
        run: kamal deploy
```

This approach SSHes from a GitHub-hosted runner into 192.168.0.37. The deploy
key must have push access to localhost:32000 on the host. For a personal server
behind a Cloudflare tunnel (no open ports), you will need to open port 22 via
the Cloudflare tunnel or use a jump host. The D4a approach (local `kamal deploy`)
avoids this entirely and is recommended for solo personal use.
