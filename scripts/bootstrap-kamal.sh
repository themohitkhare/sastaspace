#!/usr/bin/env bash
# scripts/bootstrap-kamal.sh
#
# One-shot bootstrap for the Kamal deployment stack on the sastaspace prod host.
# Run this ONCE before the first `kamal deploy`. Idempotent — safe to re-run.
#
# What it does:
#   1. Installs the kamal gem on the dev machine (if not already present).
#   2. Adds 192.168.0.37 to ~/.ssh/known_hosts (ssh-keyscan).
#   3. On the remote host (192.168.0.37):
#      a. Pulls the kamal-proxy Docker image.
#      b. Creates the shared "kamal" Docker network all apps attach to.
#      c. Starts kamal-proxy on port 8080 (not 80 — nginx-ingress still owns
#         80 during the pre-flight period; see docs/deploy/cutover.md for the
#         port-swap step at actual cutover).
#      d. Enables the localhost:32000 insecure registry in Docker daemon config
#         so Kamal can push/pull without TLS to the MicroK8s registry.
#   4. Verifies kamal-proxy is running.
#   5. Deploys a "hello-world" test container at sastaspace.com/hello (using
#      a plain nginx image with a canned 200 response) to confirm path routing
#      works end-to-end before any Rails app is ready.
#
# Usage:
#   chmod +x scripts/bootstrap-kamal.sh
#   ./scripts/bootstrap-kamal.sh
#
# Prerequisites on dev machine:
#   - Ruby >= 3.1 installed (rbenv, rvm, or system)
#   - SSH key set up for mkhare@192.168.0.37 (host: taxila, Ubuntu x86_64)
#   - Docker installed locally (for `kamal` CLI)
#
# Prerequisites on prod host (192.168.0.37):
#   - Docker 29.4.1+ (already present per architecture docs)
#   - No requirement for Ruby (kamal builds/pushes from the dev machine via SSH)

set -euo pipefail

HOST="192.168.0.37"
SSH_USER="mkhare"
KAMAL_PROXY_IMAGE="basecamp/kamal-proxy:latest"
DOCKER_NETWORK="kamal"
PREFLIGHT_PORT="8080"   # kamal-proxy pre-cutover port; becomes 80 at cutover

# --------------------------------------------------------------------------
# Step 1 — Install Kamal gem on dev machine
# --------------------------------------------------------------------------
echo "==> Step 1: Installing Kamal gem on dev machine..."

if command -v kamal &>/dev/null; then
  KAMAL_VERSION=$(kamal version 2>/dev/null || echo "unknown")
  echo "    kamal already installed: $KAMAL_VERSION"
else
  echo "    Installing kamal gem..."
  gem install kamal
  echo "    Installed: $(kamal version)"
fi

# --------------------------------------------------------------------------
# Step 2 — Add host to known_hosts
# --------------------------------------------------------------------------
echo "==> Step 2: Adding $HOST to ~/.ssh/known_hosts..."

if ! ssh-keygen -F "$HOST" &>/dev/null; then
  ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts
  echo "    Added $HOST to known_hosts."
else
  echo "    $HOST already in known_hosts."
fi

# --------------------------------------------------------------------------
# Step 3 — Remote host setup
# --------------------------------------------------------------------------
echo "==> Step 3: Setting up remote host $HOST..."

# 3a — Configure Docker daemon to allow insecure registry at localhost:32000
# This lets Kamal push/pull from the MicroK8s registry over plain HTTP.
echo "    3a: Configuring Docker insecure registry (localhost:32000)..."
ssh "${SSH_USER}@${HOST}" bash <<'REMOTE_REGISTRY'
DAEMON_JSON="/etc/docker/daemon.json"
if [ -f "$DAEMON_JSON" ]; then
  # Check if already configured
  if grep -q "localhost:32000" "$DAEMON_JSON"; then
    echo "    insecure-registries already configured"
  else
    # Merge into existing config using Python (avoid jq dependency)
    sudo python3 -c "
import json, sys
with open('$DAEMON_JSON') as f:
    d = json.load(f)
regs = d.get('insecure-registries', [])
if 'localhost:32000' not in regs:
    regs.append('localhost:32000')
d['insecure-registries'] = regs
with open('$DAEMON_JSON', 'w') as f:
    json.dump(d, f, indent=2)
print('    Updated daemon.json')
"
    sudo systemctl reload docker || sudo systemctl restart docker
    echo "    Docker daemon reloaded with insecure registry."
  fi
else
  echo '{"insecure-registries": ["localhost:32000"]}' | sudo tee "$DAEMON_JSON"
  sudo systemctl reload docker || sudo systemctl restart docker
  echo "    Created daemon.json with insecure registry."
fi
REMOTE_REGISTRY

# 3b — Create shared Docker network
echo "    3b: Creating '$DOCKER_NETWORK' Docker network..."
ssh "${SSH_USER}@${HOST}" bash <<REMOTE_NETWORK
if docker network inspect "$DOCKER_NETWORK" &>/dev/null; then
  echo "    Network '$DOCKER_NETWORK' already exists."
else
  docker network create "$DOCKER_NETWORK"
  echo "    Created network '$DOCKER_NETWORK'."
fi
REMOTE_NETWORK

# 3c — Pull kamal-proxy image
echo "    3c: Pulling kamal-proxy image on remote host..."
ssh "${SSH_USER}@${HOST}" "docker pull ${KAMAL_PROXY_IMAGE}"

# 3d — Start kamal-proxy (pre-flight mode on port 8080)
echo "    3d: Starting kamal-proxy on port $PREFLIGHT_PORT (pre-cutover)..."
ssh "${SSH_USER}@${HOST}" bash <<REMOTE_PROXY
if docker ps --filter name=kamal-proxy --format '{{.Names}}' | grep -q kamal-proxy; then
  echo "    kamal-proxy is already running."
  docker ps --filter name=kamal-proxy --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
else
  docker run -d \
    --name kamal-proxy \
    --restart unless-stopped \
    --network $DOCKER_NETWORK \
    -p ${PREFLIGHT_PORT}:80 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    ${KAMAL_PROXY_IMAGE} \
    run --port=80
  echo "    kamal-proxy started on host port ${PREFLIGHT_PORT}."
fi
REMOTE_PROXY

# --------------------------------------------------------------------------
# Step 4 — Verify kamal-proxy is running
# --------------------------------------------------------------------------
echo "==> Step 4: Verifying kamal-proxy on remote host..."

PROXY_STATUS=$(ssh "${SSH_USER}@${HOST}" "docker ps --filter name=kamal-proxy --format '{{.Status}}'")
if [ -n "$PROXY_STATUS" ]; then
  echo "    kamal-proxy is running: $PROXY_STATUS"
else
  echo "    ERROR: kamal-proxy container not found!" >&2
  exit 1
fi

# --------------------------------------------------------------------------
# Step 5 — Deploy hello-world test container
# --------------------------------------------------------------------------
echo "==> Step 5: Deploying hello-world test at /hello path..."

# Create a minimal nginx config that returns 200 for /hello/*
# and includes the path prefix in the response body for easy verification.
ssh "${SSH_USER}@${HOST}" bash <<'REMOTE_HELLO'
# Create a tiny nginx config
mkdir -p /tmp/hello-test
cat > /tmp/hello-test/default.conf <<'NGINX'
server {
    listen 3099;
    location /hello {
        default_type text/plain;
        return 200 "hello from kamal path routing - /hello\n";
    }
    location /hello/ {
        default_type text/plain;
        return 200 "hello from kamal path routing - /hello/\n";
    }
    location /up {
        default_type text/plain;
        return 200 "ok\n";
    }
}
NGINX

# Stop existing hello container if running
docker stop sastaspace-hello 2>/dev/null && docker rm sastaspace-hello 2>/dev/null || true

# Run the hello-world container
docker run -d \
  --name sastaspace-hello \
  --restart unless-stopped \
  --network kamal \
  -p 3099:3099 \
  -v /tmp/hello-test/default.conf:/etc/nginx/conf.d/default.conf:ro \
  --label "kamal-proxy.path_prefix=/hello" \
  nginx:alpine

echo "    hello-world container started on port 3099 with label kamal-proxy.path_prefix=/hello"
REMOTE_HELLO

# Give proxy a moment to detect the new container label
sleep 3

# Test locally on host
echo "    Testing /hello directly on host port 3099..."
HELLO_STATUS=$(ssh "${SSH_USER}@${HOST}" "curl -sI http://localhost:3099/hello | head -1" 2>/dev/null || echo "curl failed")
echo "    Direct container: $HELLO_STATUS"

# Test through kamal-proxy on preflight port 8080
echo "    Testing /hello through kamal-proxy (port $PREFLIGHT_PORT)..."
PROXY_HELLO=$(ssh "${SSH_USER}@${HOST}" "curl -sI http://localhost:${PREFLIGHT_PORT}/hello | head -1" 2>/dev/null || echo "curl failed")
echo "    Through proxy: $PROXY_HELLO"

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Bootstrap complete."
echo "============================================================"
echo ""
echo "kamal version:     $(kamal version 2>/dev/null || echo 'not found')"
echo "kamal-proxy:       running on $HOST:$PREFLIGHT_PORT (pre-cutover)"
echo "Docker network:    $DOCKER_NETWORK"
echo "Hello-world test:  http://$HOST:$PREFLIGHT_PORT/hello"
echo ""
echo "Next steps:"
echo "  1. Build and push Rails app images:"
echo "     cd projects/landing-rails && kamal deploy"
echo "     cd projects/almirah-rails  && kamal deploy"
echo "  2. Smoke-test both apps on port $PREFLIGHT_PORT before cutover."
echo "  3. Follow docs/deploy/cutover.md to swap nginx-ingress → kamal-proxy"
echo "     and move kamal-proxy from port $PREFLIGHT_PORT to port 80."
echo ""
echo "Cloudflare tunnel config: no changes needed at this stage."
echo "The tunnel already points at localhost:80; we will rebind kamal-proxy"
echo "to that port at cutover time."
