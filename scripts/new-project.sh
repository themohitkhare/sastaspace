#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-}"
if [[ -z "$NAME" ]]; then
  echo "usage: ./scripts/new-project.sh <name>"
  exit 1
fi
if ! [[ "$NAME" =~ ^[a-z][a-z0-9-]{1,30}$ ]]; then
  echo "error: name must match ^[a-z][a-z0-9-]{1,30}$"
  exit 1
fi
case "$NAME" in
  landing|api|www|admin)
    echo "error: reserved project name"
    exit 1
    ;;
esac
if [[ -e "projects/$NAME" ]]; then
  echo "error: projects/$NAME already exists"
  exit 1
fi
if [[ ! -d "projects/_template" ]]; then
  echo "error: projects/_template not found"
  exit 1
fi

cp -R projects/_template "projects/$NAME"

while IFS= read -r -d '' file; do
  sed -i.bak "s/__NAME__/$NAME/g" "$file" && rm -f "$file.bak"
done < <(find "projects/$NAME" -type f -print0)

if [[ -f "projects/$NAME/db/migrations/0001_init.sql.tmpl" ]]; then
  mv "projects/$NAME/db/migrations/0001_init.sql.tmpl" "projects/$NAME/db/migrations/0001_init.sql"
fi

echo "Project '$NAME' created."
echo "Next steps:"
echo "  make migrate p=$NAME"
echo "  make dev p=$NAME"
echo "  git add . && git commit"
