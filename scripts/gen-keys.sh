#!/usr/bin/env bash
# Generate a JWT_SECRET and matching HS256-signed ANON_KEY + SERVICE_ROLE_KEY
# and write them to ./.env. Idempotent: if JWT_SECRET is already a real value,
# keep it and only re-mint the signed keys.
#
# No deps beyond bash + openssl. Works on macOS and Linux.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp .env.example "$ENV_FILE"
  echo "Created .env from .env.example"
fi

# ---- read existing JWT_SECRET (if any and not the placeholder) ----
current_secret=$(grep -E '^JWT_SECRET=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)
placeholder="replace-with-long-random-string-min-32-chars"
if [[ -z "$current_secret" || "$current_secret" == "$placeholder" ]]; then
  JWT_SECRET=$(openssl rand -hex 32)
  echo "Minted new JWT_SECRET"
else
  JWT_SECRET="$current_secret"
  echo "Reusing existing JWT_SECRET"
fi

# ---- HS256 JWT signer (pure openssl) ----
b64url() {
  # stdin -> base64url (no padding)
  openssl base64 -A | tr '+/' '-_' | tr -d '='
}

header_json='{"alg":"HS256","typ":"JWT"}'
now=$(date +%s)
# 5 years; long-lived local keys are fine for dev
exp=$((now + 60 * 60 * 24 * 365 * 5))

sign_jwt() {
  local role="$1"
  local payload
  payload=$(printf '{"role":"%s","iss":"supabase","iat":%d,"exp":%d}' \
    "$role" "$now" "$exp")
  local h p sig
  h=$(printf '%s' "$header_json" | b64url)
  p=$(printf '%s' "$payload"     | b64url)
  sig=$(printf '%s.%s' "$h" "$p" \
        | openssl dgst -binary -sha256 -hmac "$JWT_SECRET" \
        | b64url)
  printf '%s.%s.%s' "$h" "$p" "$sig"
}

ANON_KEY=$(sign_jwt anon)
SERVICE_ROLE_KEY=$(sign_jwt service_role)

# ---- rewrite .env: drop the keys we own, then append fresh values ----
tmp=$(mktemp)
grep -vE '^(JWT_SECRET|ANON_KEY|SERVICE_ROLE_KEY|NEXT_PUBLIC_SUPABASE_ANON_KEY|SUPABASE_SERVICE_ROLE_KEY)=' \
  "$ENV_FILE" > "$tmp" || true
{
  cat "$tmp"
  echo "JWT_SECRET=$JWT_SECRET"
  echo "ANON_KEY=$ANON_KEY"
  echo "SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY"
  echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=$ANON_KEY"
  echo "SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY"
} > "$ENV_FILE"
rm -f "$tmp"

echo "Wrote $ENV_FILE"
printf '  JWT_SECRET        %s...\n' "${JWT_SECRET:0:12}"
printf '  ANON_KEY          %s...\n' "${ANON_KEY:0:24}"
printf '  SERVICE_ROLE_KEY  %s...\n' "${SERVICE_ROLE_KEY:0:24}"
