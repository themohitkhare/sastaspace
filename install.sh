#!/usr/bin/env bash
# sastaspace TUI installer.
# Usage: curl -sSf https://sastaspace.com/install.sh | sh
set -euo pipefail

REPO="mohitkhare/sastaspace"
BINARY="sastaspace"
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS-$ARCH" in
    Darwin-arm64)   TARGET="aarch64-apple-darwin"     ;;
    Darwin-x86_64)  TARGET="x86_64-apple-darwin"      ;;
    Linux-x86_64)   TARGET="x86_64-unknown-linux-gnu" ;;
    Linux-aarch64)  TARGET="aarch64-unknown-linux-gnu";;
    *)              echo "Unsupported platform: $OS-$ARCH" >&2; exit 1 ;;
esac

LATEST_URL="https://github.com/${REPO}/releases/latest/download/${BINARY}-${TARGET}.tar.gz"
echo "Fetching $LATEST_URL ..."

INSTALL_DIR="${SASTASPACE_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$INSTALL_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "$LATEST_URL" | tar -C "$TMP" -xzf -
mv "$TMP/${BINARY}" "$INSTALL_DIR/${BINARY}"
chmod +x "$INSTALL_DIR/${BINARY}"

echo "Installed ${BINARY} to ${INSTALL_DIR}/${BINARY}"
echo "Make sure $INSTALL_DIR is in your PATH."
