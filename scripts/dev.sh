#!/usr/bin/env bash
# dev.sh — boot shared Postgres in Compose + print Rails dev instructions.
# Post-Rails migration: projects are Rails 8 apps, not Next.js + Go.
set -euo pipefail

PROJECT="${1:-${p:-}}"
if [[ -z "$PROJECT" ]]; then
  echo "usage: ./scripts/dev.sh <project-name>"
  echo "or:    make dev p=<project-name>"
  exit 1
fi

if [[ ! -d "projects/$PROJECT" ]]; then
  echo "error: projects/$PROJECT not found"
  exit 1
fi

docker compose -f infra/docker-compose.yml up -d postgres

cat <<EOF

Shared Postgres is up on localhost:5432 (user=postgres, pass=postgres).

To run Rails:

    cd projects/$PROJECT
    bundle install                      # first time
    bin/rails db:prepare                # first time
    bin/rails server                    # dev server on http://localhost:3000

Tests:

    bin/rails test                      # unit
    bin/rails test:system               # Capybara
    bin/rubocop                         # lint
EOF
