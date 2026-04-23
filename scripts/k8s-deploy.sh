#!/usr/bin/env bash
# k8s-deploy.sh — single-command deploy of the sastaspace stack to the
# microk8s cluster running on taxila (192.168.0.37).
#
# Sub-commands (composable):
#   gen-secrets  Generate infra/k8s/secrets.yaml from .env + prod overrides
#   sync         rsync the repo to the remote under $SSH_REMOTE_DIR
#   build        ssh into remote, docker build the landing image, push to
#                microk8s' local registry (localhost:32000)
#   delete-old   Delete the legacy "sastaspace" namespace on the cluster
#   apply        kubectl apply -f infra/k8s/ on the remote
#   migrate      Pipe db/migrations/*.sql through kubectl exec → psql
#   status       Show pod / svc / ingress status
#   verify       curl the public endpoints
#   all          gen-secrets → sync → build → apply → migrate → verify
#                (deliberately does NOT run delete-old; call it explicitly)
#
# All knobs come from the root .env. SSH_HOST / SSH_REMOTE_DIR default to
# 192.168.0.37 / ~/sastaspace.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
K8S_DIR="${REPO_ROOT}/infra/k8s"
MIGRATIONS_DIR="${REPO_ROOT}/db/migrations"

# shellcheck disable=SC1090
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

SSH_HOST="${SSH_HOST:-192.168.0.37}"
SSH_REMOTE_DIR="${SSH_REMOTE_DIR:-\$HOME/sastaspace}"
NAMESPACE="${K8S_NAMESPACE:-sastaspace}"
IMAGE_REPO="${IMAGE_REPO:-localhost:32000/sastaspace-landing}"
IMAGE_TAG="${IMAGE_TAG:-$(date -u +%Y%m%d-%H%M%S)}"

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
info()  { printf '  %s\n' "$*"; }
die()   { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# Shared ssh wrapper so every command goes through the same user + host.
rssh() { ssh "$SSH_HOST" "$@"; }
rmk() { rssh "microk8s kubectl -n $NAMESPACE $*"; }

# Expand $HOME etc. on the remote the first time we need a concrete path.
remote_dir() {
  rssh "echo $SSH_REMOTE_DIR"
}

require() {
  local v
  for v in "$@"; do
    [[ -n "${!v:-}" ]] || die "missing env var: $v (check .env)"
  done
}

# ---------------------------------------------------------------------------
# gen-secrets
# ---------------------------------------------------------------------------
cmd_gen_secrets() {
  bold "==> Generating $K8S_DIR/secrets.yaml from .env"
  require POSTGRES_PASSWORD JWT_SECRET ANON_KEY SERVICE_ROLE_KEY RESEND_API_KEY OWNER_EMAIL

  local out="$K8S_DIR/secrets.yaml"
  local tpl="$K8S_DIR/secrets.yaml.template"
  [[ -f "$tpl" ]] || die "missing $tpl"

  # NEXT_PUBLIC_SUPABASE_ANON_KEY in .env is the same value as ANON_KEY after
  # the first `make keys` run; fall back to ANON_KEY if the dedicated var is
  # absent. Same for SUPABASE_SERVICE_ROLE_KEY.
  : "${NEXT_PUBLIC_SUPABASE_ANON_KEY:=$ANON_KEY}"
  : "${SUPABASE_SERVICE_ROLE_KEY:=$SERVICE_ROLE_KEY}"
  : "${NEXT_PUBLIC_TURNSTILE_SITE_KEY:=replace_me}"
  : "${TURNSTILE_SECRET_KEY:=replace_me}"

  # Using python for safe, escaping-aware substitution (sed chokes on JWT '=').
  python3 - "$tpl" "$out" <<PY
import os, sys, pathlib
tpl, out = sys.argv[1], sys.argv[2]
t = pathlib.Path(tpl).read_text()
repl = {
    "__POSTGRES_PASSWORD__":        os.environ["POSTGRES_PASSWORD"],
    "__JWT_SECRET__":               os.environ["JWT_SECRET"],
    "__ANON_KEY__":                 os.environ["NEXT_PUBLIC_SUPABASE_ANON_KEY"],
    "__SERVICE_ROLE_KEY__":         os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    "__RESEND_API_KEY__":           os.environ["RESEND_API_KEY"],
    "__OWNER_EMAIL__":              os.environ["OWNER_EMAIL"],
    "__TURNSTILE_SITE_KEY__":       os.environ.get("NEXT_PUBLIC_TURNSTILE_SITE_KEY",""),
    "__TURNSTILE_SECRET_KEY__":     os.environ.get("TURNSTILE_SECRET_KEY",""),
}
for k, v in repl.items():
    t = t.replace(k, v)
pathlib.Path(out).write_text(t)
print(f"wrote {out}")
PY
  info "Reminder: $out contains live credentials — do not commit."
}

# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------
cmd_sync() {
  bold "==> Syncing repo to $SSH_HOST:$SSH_REMOTE_DIR"
  local remote; remote="$(remote_dir)"
  rssh "mkdir -p '$remote'"
  rsync -avz --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '**/dist' \
    --exclude '.env' \
    --exclude 'infra/k8s/secrets.yaml' \
    "$REPO_ROOT/" "$SSH_HOST:$remote/"
  # secrets.yaml is sensitive → scp it separately so it's never in git
  if [[ -f "$K8S_DIR/secrets.yaml" ]]; then
    info "copying secrets.yaml (scp, separate from rsync)"
    scp -q "$K8S_DIR/secrets.yaml" "$SSH_HOST:$remote/infra/k8s/secrets.yaml"
  fi
}

# ---------------------------------------------------------------------------
# build (remote docker build + push to microk8s registry)
# ---------------------------------------------------------------------------
cmd_build() {
  bold "==> Building landing image on remote and pushing to localhost:32000"
  require NEXT_PUBLIC_SUPABASE_ANON_KEY
  local remote; remote="$(remote_dir)"
  local full="$IMAGE_REPO:$IMAGE_TAG"
  local latest="$IMAGE_REPO:latest"

  # Build runs on the remote because localhost:32000 is only reachable from
  # the microk8s node. We pass NEXT_PUBLIC_* as build args so they're baked
  # into the client bundle.
  rssh "cd '$remote/projects/landing/web' && sudo docker build \
    --pull \
    --build-arg NEXT_PUBLIC_SUPABASE_URL='https://api.sastaspace.com' \
    --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY='$NEXT_PUBLIC_SUPABASE_ANON_KEY' \
    --build-arg NEXT_PUBLIC_BASE_URL='https://sastaspace.com' \
    --build-arg NEXT_PUBLIC_TURNSTILE_SITE_KEY='${NEXT_PUBLIC_TURNSTILE_SITE_KEY:-}' \
    -f ../Dockerfile.web \
    -t '$full' -t '$latest' ."
  rssh "sudo docker push '$full' && sudo docker push '$latest'"
  info "pushed $full"
  echo "$IMAGE_TAG" > "$REPO_ROOT/.last-image-tag"
}

# ---------------------------------------------------------------------------
# delete-old (explicit)
# ---------------------------------------------------------------------------
cmd_delete_old() {
  bold "==> Deleting legacy sastaspace namespace (destructive!)"
  rssh "microk8s kubectl delete namespace $NAMESPACE --ignore-not-found --wait=true"
  info "done."
}

# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------
cmd_apply() {
  bold "==> Applying manifests"
  local remote; remote="$(remote_dir)"
  # Order matters only for secrets (everything else has envFrom/Service DNS
  # retries built in). Apply namespace + secrets first, then the rest.
  rssh "microk8s kubectl apply -f '$remote/infra/k8s/namespace.yaml'"
  rssh "microk8s kubectl apply -f '$remote/infra/k8s/secrets.yaml'"
  # Stage 1: postgres alone — nothing else can start until its roles exist.
  rssh "microk8s kubectl apply -f '$remote/infra/k8s/postgres.yaml'"
  bold "==> Waiting for postgres"
  rssh "microk8s kubectl -n $NAMESPACE rollout status statefulset/postgres --timeout=180s" \
    || die "postgres didn't become ready"

  # Run migrations HERE (before gotrue) so supabase_auth_admin exists by the
  # time GoTrue connects. Doing it after `apply` would make GoTrue crash-loop.
  cmd_migrate

  # Stage 2: everything else, and wait for each one.
  rssh "microk8s kubectl apply \
    -f '$remote/infra/k8s/postgrest.yaml' \
    -f '$remote/infra/k8s/gotrue.yaml' \
    -f '$remote/infra/k8s/pg-meta.yaml' \
    -f '$remote/infra/k8s/gateway.yaml' \
    -f '$remote/infra/k8s/landing.yaml' \
    -f '$remote/infra/k8s/ingress.yaml'"

  bold "==> Waiting for gotrue, postgrest, gateway, landing"
  for app in postgrest gotrue pg-meta gateway landing; do
    rssh "microk8s kubectl -n $NAMESPACE rollout status deploy/$app --timeout=240s" \
      || die "$app didn't become ready"
  done

  # Force a roll on landing so a new tag is picked up even if "latest" already
  # existed in containerd's cache.
  if [[ -n "${IMAGE_TAG:-}" && "${IMAGE_TAG}" != "latest" ]]; then
    rssh "microk8s kubectl -n $NAMESPACE set image deploy/landing landing=$IMAGE_REPO:$IMAGE_TAG"
    rssh "microk8s kubectl -n $NAMESPACE rollout status deploy/landing --timeout=180s"
  fi
}

# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------
cmd_migrate() {
  bold "==> Running db/migrations on cluster postgres"
  require POSTGRES_PASSWORD POSTGRES_DB POSTGRES_USER
  local pod
  pod="$(rssh "microk8s kubectl -n $NAMESPACE get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}'")"
  [[ -n "$pod" ]] || die "no postgres pod found"
  info "target pod: $pod"

  # Same substitution as scripts/migrate.sh: bake real password into role
  # CREATE statements and ensure authenticator / supabase_auth_admin
  # passwords are always in sync.
  for f in "$MIGRATIONS_DIR"/*.sql; do
    info "applying $(basename "$f")"
    sed "s/change-me-sync-with-POSTGRES_PASSWORD/$POSTGRES_PASSWORD/g" "$f" \
      | rssh "microk8s kubectl -n $NAMESPACE exec -i $pod -- \
              psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB" \
      >/dev/null
  done

  info "syncing role passwords"
  rssh "microk8s kubectl -n $NAMESPACE exec -i $pod -- psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
    \"ALTER ROLE authenticator WITH PASSWORD '$POSTGRES_PASSWORD'; \
      ALTER ROLE supabase_auth_admin WITH PASSWORD '$POSTGRES_PASSWORD';\"" >/dev/null
}

# ---------------------------------------------------------------------------
# status / verify
# ---------------------------------------------------------------------------
cmd_status() {
  bold "==> Cluster status"
  rssh "microk8s kubectl -n $NAMESPACE get pod,svc,ingress -o wide"
}

cmd_verify() {
  bold "==> Hitting public endpoints"
  local fail=0
  check() {
    local name="$1" url="$2" want="${3:-200}"
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$url" || echo 000)"
    if [[ "$code" == "$want" ]]; then
      printf '  \033[32m✓\033[0m %-32s %s (%s)\n' "$name" "$url" "$code"
    else
      printf '  \033[31m✗\033[0m %-32s %s (got %s, want %s)\n' "$name" "$url" "$code" "$want"
      fail=1
    fi
  }
  check "landing root"        "https://sastaspace.com/"                            200
  check "www redirect"        "https://www.sastaspace.com/"                        200
  check "api gateway health"  "https://api.sastaspace.com/healthz"                 200
  check "gotrue settings"     "https://api.sastaspace.com/auth/v1/settings"        200
  check "postgrest projects"  "https://api.sastaspace.com/rest/v1/projects?select=slug" 200
  [[ "$fail" == 0 ]] || die "at least one check failed"
}

# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------
case "${1:-help}" in
  gen-secrets) cmd_gen_secrets ;;
  sync)        cmd_sync ;;
  build)       cmd_build ;;
  delete-old)  cmd_delete_old ;;
  apply)       cmd_apply ;;
  migrate)     cmd_migrate ;;
  status)      cmd_status ;;
  verify)      cmd_verify ;;
  # apply already runs cmd_migrate internally (between postgres and the rest),
  # so the "all" pipeline does not invoke it a second time.
  all)         cmd_gen_secrets && cmd_sync && cmd_build && cmd_apply && cmd_verify ;;
  help|-h|--help|*)
    cat <<EOF
Usage: scripts/k8s-deploy.sh <command>

Commands:
  gen-secrets   Render infra/k8s/secrets.yaml from .env (local only)
  sync          rsync repo + scp secrets.yaml to $SSH_HOST
  build         docker build landing image on remote, push to localhost:32000
  delete-old    Delete legacy "sastaspace" namespace (destructive, explicit)
  apply         kubectl apply manifests + wait for rollout
  migrate       Run db/migrations/*.sql via kubectl exec psql
  status        Show pods / services / ingress
  verify        curl public endpoints and assert 200
  all           gen-secrets → sync → build → apply → migrate → verify

Env overrides (read from .env):
  SSH_HOST          default 192.168.0.37
  SSH_REMOTE_DIR    default \$HOME/sastaspace on the remote
  IMAGE_REPO        default localhost:32000/sastaspace-landing
  IMAGE_TAG         default UTC timestamp
EOF
    ;;
esac
