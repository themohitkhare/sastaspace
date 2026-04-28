#!/usr/bin/env bash
# Regenerates Rust bindings from the sastaspace module schema.
# Bindings are checked in (per repo convention — see root .gitignore).
#
# The module must be compiled to WASM first. A pre-built binary lives at:
#   modules/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm
#
# If you need to rebuild the WASM, do so from a directory that is NOT under
# the workspace root (the workspace crate named 'core' shadows std::core for
# the wasm32 target). The sastaspace main repo has a pre-built binary you can
# use directly.
#
# Usage: ./crates/stdb-client/build_bindings.sh [--wasm-path <path>]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT="$SCRIPT_DIR/src/bindings"

# Default: use the pre-built wasm from the main sastaspace repo checkout.
WASM_PATH="${1:-$ROOT/../sastaspace/modules/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm}"

if [ ! -f "$WASM_PATH" ]; then
  echo "ERROR: wasm binary not found at $WASM_PATH"
  echo "Build it first from a directory outside this workspace:"
  echo "  cd /tmp && cp -r $ROOT/modules/sastaspace . && cd sastaspace && cargo build --target wasm32-unknown-unknown --release"
  echo "  Then re-run: $0 /tmp/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm"
  exit 1
fi

rm -rf "$OUT"
mkdir -p "$OUT"
spacetime generate --lang rust --out-dir "$OUT" --bin-path "$WASM_PATH" -y
echo "regenerated $(ls "$OUT" | wc -l | tr -d ' ') binding files in $OUT"
