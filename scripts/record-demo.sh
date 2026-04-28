#!/usr/bin/env bash
# Record a 60-second demo of the sastaspace TUI.
# Output: demo.cast (asciinema v2 format)
# Then upload with: asciinema upload demo.cast
set -euo pipefail

if ! command -v asciinema >/dev/null 2>&1; then
  echo "asciinema not installed. brew install asciinema" >&2
  exit 1
fi
if ! command -v sastaspace >/dev/null 2>&1; then
  echo "sastaspace not installed. brew install themohitkhare/sastaspace/sastaspace" >&2
  exit 1
fi

OUT="${1:-demo.cast}"
echo "Recording to $OUT — when the TUI opens, suggested sequence:"
echo "  Shift-T   (typewars — see legion select)"
echo "  Shift-N   (notes — see two-pane editor)"
echo "  Shift-D   (deck — see plan screen)"
echo "  Shift-A   (admin — see device-flow gate)"
echo "  Shift-P   (back to portfolio)"
echo "  q         (quit)"
echo ""
echo "Press Enter to start. Aim for ~60 seconds total."
read -r

asciinema rec \
  --idle-time-limit=2 \
  --title "sastaspace TUI — portfolio + 4 apps in one binary" \
  --command sastaspace \
  "$OUT"

echo ""
echo "Recorded: $OUT"
echo ""
echo "Next steps:"
echo "  1. Preview locally:    asciinema play $OUT"
echo "  2. Upload to asciinema.org (gives you an embeddable URL):"
echo "       asciinema upload $OUT"
echo "  3. Or convert to GIF (needs `agg` from cargo install --git https://github.com/asciinema/agg):"
echo "       agg --speed 1.5 $OUT demo.gif"
echo ""
