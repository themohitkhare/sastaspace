#!/usr/bin/env bash
# Regenerates Rust bindings from the sastaspace module schema.
# Bindings are checked in (per repo convention — see root .gitignore).
#
# Usage: ./crates/stdb-client/build_bindings.sh [<path-to-wasm>]
#
# If no wasm path is given the script tries (in order):
#   1. Build the module in-tree using cargo with the rustup-managed rustc.
#      The dev machine has /opt/homebrew/bin/rustc on PATH which lacks the
#      wasm32 target; RUSTC_FOR_WASM (or the rustup stable toolchain rustc)
#      is used to override it.
#   2. Pre-built wasm from the sibling sastaspace checkout (local fallback).
#   3. Fail with a clear error message.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT="$SCRIPT_DIR/src/bindings"
# Cargo places the output in the workspace-level target dir when building
# from a workspace member. Both paths are checked.
IN_TREE_WASM_WORKSPACE="$ROOT/target/wasm32-unknown-unknown/release/sastaspace_module.wasm"
IN_TREE_WASM_LOCAL="$ROOT/modules/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm"
SIBLING_WASM="$ROOT/../sastaspace/modules/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm"

find_in_tree_wasm() {
  for p in "$IN_TREE_WASM_WORKSPACE" "$IN_TREE_WASM_LOCAL"; do
    if [ -f "$p" ]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

resolve_wasm() {
  # Explicit argument wins.
  if [ -n "${1:-}" ]; then
    echo "$1"
    return
  fi

  # Check if already built.
  if find_in_tree_wasm 2>/dev/null; then
    return
  fi

  # Try to build in-tree.
  # Pick a rustc that has the wasm32 target:
  #   - RUSTC_FOR_WASM env var (CI can set this)
  #   - rustup stable toolchain rustc (present on the dev machine)
  #   - fall through if neither has the wasm32 target
  local RUSTC_BIN=""
  if [ -n "${RUSTC_FOR_WASM:-}" ]; then
    RUSTC_BIN="$RUSTC_FOR_WASM"
  else
    local CANDIDATE="$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc"
    if [ -f "$CANDIDATE" ]; then
      RUSTC_BIN="$CANDIDATE"
    fi
  fi

  if [ -n "$RUSTC_BIN" ]; then
    echo "Building wasm in-tree using $RUSTC_BIN ..." >&2
    (
      cd "$ROOT/modules/sastaspace"
      RUSTC="$RUSTC_BIN" cargo build --target wasm32-unknown-unknown --release 2>&1 || true
    )
  else
    echo "Warning: no wasm-capable rustc found; trying existing binaries." >&2
    (
      cd "$ROOT/modules/sastaspace"
      cargo build --target wasm32-unknown-unknown --release 2>&1 || true
    )
  fi

  if find_in_tree_wasm 2>/dev/null; then
    return
  fi

  # Fallback: pre-built wasm from the sibling checkout.
  if [ -f "$SIBLING_WASM" ]; then
    echo "Warning: in-tree wasm build failed; falling back to sibling checkout wasm." >&2
    echo "         Fix the local toolchain (see Debt 3 notes in docs/superpowers/plans/)." >&2
    echo "$SIBLING_WASM"
    return
  fi

  echo ""  # empty → caller will fail
}

WASM_PATH="$(resolve_wasm "${1:-}")"

if [ -z "$WASM_PATH" ] || [ ! -f "$WASM_PATH" ]; then
  echo "ERROR: could not locate or build wasm binary."
  echo ""
  echo "Tried:"
  echo "  in-tree (workspace): $IN_TREE_WASM_WORKSPACE"
  echo "  in-tree (local):     $IN_TREE_WASM_LOCAL"
  echo "  sibling:             $SIBLING_WASM"
  echo ""
  echo "Fix options:"
  echo "  1. Set RUSTC_FOR_WASM=/path/to/rustup-rustc and re-run."
  echo "  2. Pass an explicit wasm path: $0 /path/to/sastaspace_module.wasm"
  echo "  3. Reinstall wasm target: rustup target add wasm32-unknown-unknown"
  exit 1
fi

rm -rf "$OUT"
mkdir -p "$OUT"
spacetime generate --lang rust --out-dir "$OUT" --bin-path "$WASM_PATH" -y
echo "regenerated $(ls "$OUT" | wc -l | tr -d ' ') binding files in $OUT"
