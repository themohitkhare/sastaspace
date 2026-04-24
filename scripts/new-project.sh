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

# Skip heavy directories during substitution — vendor/bundle, tmp/, log/
# are not version-controlled and won't contain __NAME__ placeholders.
while IFS= read -r -d '' file; do
  sed -i.bak "s/__NAME__/$NAME/g" "$file" && rm -f "$file.bak"
done < <(find "projects/$NAME" -type f \
  \! -path "projects/$NAME/vendor/*" \
  \! -path "projects/$NAME/tmp/*" \
  \! -path "projects/$NAME/log/*" \
  -print0)

echo "Project '$NAME' created from the Rails 8 template."
echo "Next steps:"
echo "  cd projects/$NAME"
echo "  bundle install"
echo "  bin/rails db:prepare"
echo "  bin/rails server           # dev at http://localhost:3000"
echo "  # then wire: projects/$NAME/k8s.yaml (see projects/almirah/k8s.yaml)"
echo "  #           infra/k8s/ingress.yaml (add /$NAME path rule)"
