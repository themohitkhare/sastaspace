#!/usr/bin/env bash
# tests/e2e/smoke.sh — HTTP smoke tests against live sastaspace deployment.
#
# Run:  tests/e2e/smoke.sh            # defaults to prod hosts
# Run:  BASE=https://staging.example.com tests/e2e/smoke.sh   # override
#
# No browser, no dependencies beyond curl + bash. Fails on the first assertion
# that doesn't match. Prints a green tick per passing check and a red X with
# enough context to debug on fail.

set -u

# ---------- config ----------
LANDING="${LANDING:-https://sastaspace.com}"
ALMIRAH="${ALMIRAH:-https://almirah.sastaspace.com}"
API="${API:-https://api.sastaspace.com}"
TIMEOUT="${TIMEOUT:-10}"

# ---------- output helpers ----------
GREEN='\033[0;32m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'
PASS=0
FAIL=0

pass() { printf "${GREEN}✓${NC} %s\n" "$1"; PASS=$((PASS+1)); }
fail() { printf "${RED}✗${NC} %s\n    ${DIM}%s${NC}\n" "$1" "$2"; FAIL=$((FAIL+1)); }

check() {
  local name="$1"; local actual="$2"; local expected_pattern="$3"
  if echo "$actual" | grep -qE "$expected_pattern"; then
    pass "$name"
  else
    fail "$name" "want: $expected_pattern  got: $actual"
  fi
}

reject() {
  local name="$1"; local actual="$2"; local forbidden_pattern="$3"
  if echo "$actual" | grep -qE "$forbidden_pattern"; then
    fail "$name" "forbidden: $forbidden_pattern  found in: $actual"
  else
    pass "$name"
  fi
}

status()   { curl -s -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" "$1"; }
location() { curl -s -o /dev/null -D - --max-time "$TIMEOUT" "$1" | awk -F': ' 'tolower($1)=="location"{sub(/\r$/,"",$2); print $2; exit}'; }
body()     { curl -s --max-time "$TIMEOUT" "$1"; }

# ---------- hostname health ----------
echo "== hostname health =="
check "landing 200"              "$(status "$LANDING/")"                "^200$"
check "almirah gates unauth"     "$(status "$ALMIRAH/")"                "^30[27]$"
check "api /auth/v1/settings"    "$(status "$API/auth/v1/settings")"    "^200$"

# ---------- landing listing ----------
echo "== landing content =="
check "landing lists almirah" "$(body "$LANDING/" | grep -oE 'almirah\.sastaspace\.com' | head -1)" "almirah\.sastaspace\.com"
reject "landing has no magic-link form" "$(body "$LANDING/sign-in" | tr A-Z a-z)" "magic[- ]?link"

# ---------- google oauth provider enabled ----------
echo "== supabase providers =="
settings="$(body "$API/auth/v1/settings")"
check "google provider enabled"  "$settings"  '"google":true|"google": *true'
check "email provider enabled"   "$settings"  '"email":true|"email": *true'

# ---------- auth gate + redirect chain ----------
echo "== auth gate + redirect chain =="
loc="$(location "$ALMIRAH/")"
check "almirah root redirects to /signin with next=" "$loc" '^/signin\?next=%2F$'

loc="$(location "$ALMIRAH/signin?next=/today")"
check "almirah /signin → sastaspace.com/sign-in" "$loc" '^https://sastaspace\.com/sign-in\?next=https%3A%2F%2Falmirah\.sastaspace\.com%2Ftoday$'

# ---------- origin-leak guard (the 0.0.0.0 bug from 2026-04-24) ----------
echo "== origin leak guard =="
loc="$(location "$LANDING/auth/callback?code=fakecode&next=https%3A%2F%2Falmirah.sastaspace.com%2F")"
reject "landing /auth/callback redirect does NOT leak 0.0.0.0"   "$loc" '0\.0\.0\.0|127\.0\.0\.1|localhost'
check  "landing /auth/callback redirects to public host"         "$loc" '^https://sastaspace\.com/'

loc="$(location "$ALMIRAH/auth/callback?code=fakecode")"
reject "almirah /auth/callback redirect does NOT leak 0.0.0.0"   "$loc" '0\.0\.0\.0|127\.0\.0\.1|localhost'
check  "almirah /auth/callback redirects to public host"         "$loc" '^https://almirah\.sastaspace\.com/'

# ---------- tag-image protected ----------
echo "== protected api =="
check "POST /api/tag-image without auth → 401" "$(curl -s -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" -X POST "$ALMIRAH/api/tag-image")" "^401$"
check "GET /api/health without auth → 200"     "$(status "$ALMIRAH/api/health")"                                                                 "^200$"

# ---------- summary ----------
echo
if [ "$FAIL" -eq 0 ]; then
  printf "${GREEN}all %d checks passed${NC}\n" "$PASS"
  exit 0
else
  printf "${RED}%d failed, %d passed${NC}\n" "$FAIL" "$PASS"
  exit 1
fi
