#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-${p:-}}"
if [[ -z "$PROJECT" ]]; then
  echo "usage: ./scripts/dev.sh <project-name>"
  echo "or: make dev p=<project-name>"
  exit 1
fi

if [[ ! -d "projects/$PROJECT" ]]; then
  echo "error: projects/$PROJECT not found"
  exit 1
fi

docker compose -f infra/docker-compose.yml up -d postgres postgrest

echo "Start project services in separate terminals:"
echo "  cd projects/$PROJECT/web && npm run dev"
echo "  cd projects/$PROJECT/api && go run ."
