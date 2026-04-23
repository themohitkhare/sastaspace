#!/usr/bin/env bash
# Apply every file in db/migrations/*.sql in order via the running postgres
# container. Migrations are expected to be idempotent (IF NOT EXISTS / CREATE
# OR REPLACE). Placeholders in the SQL get substituted from .env so that role
# passwords match POSTGRES_PASSWORD.
set -euo pipefail

cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

CONTAINER="${POSTGRES_CONTAINER:-sastaspace-postgres}"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Error: container '$CONTAINER' not found. Run 'make up' first." >&2
  exit 1
fi

echo "Waiting for postgres to accept connections..."
for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Applying migrations to $POSTGRES_DB..."
shopt -s nullglob
for f in db/migrations/*.sql; do
  echo "  -> $f"
  # Substitute the well-known placeholder so auth roles get the real password.
  sed "s|change-me-sync-with-POSTGRES_PASSWORD|${POSTGRES_PASSWORD}|g" "$f" \
    | docker exec -i "$CONTAINER" \
        psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    >/dev/null
done

# Make absolutely sure role passwords match the current POSTGRES_PASSWORD,
# even on re-runs where the CREATE ROLE above was a no-op.
docker exec -i "$CONTAINER" \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null <<SQL
ALTER ROLE authenticator        WITH PASSWORD '${POSTGRES_PASSWORD}';
ALTER ROLE supabase_auth_admin  WITH PASSWORD '${POSTGRES_PASSWORD}';
SQL

echo "Migrations complete."
