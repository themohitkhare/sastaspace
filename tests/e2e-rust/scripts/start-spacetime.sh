#!/usr/bin/env bash
# Start a local spacetime instance for e2e tests. Used by SpacetimeFixture.
# Caller controls lifecycle — this script just runs in the foreground.
set -euo pipefail
PORT="${SPACETIME_PORT:-3199}"
DATA="${SPACETIME_DATA:-/tmp/sastaspace-e2e-spacetime}"
rm -rf "$DATA"
mkdir -p "$DATA"
exec spacetime start --listen-addr "127.0.0.1:$PORT" --data-dir "$DATA"
