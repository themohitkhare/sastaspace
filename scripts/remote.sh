#!/usr/bin/env bash
# Helpers to run the compose stack on a remote Linux box over ssh.
# Reads SSH_HOST (e.g. mohit@192.168.0.37) and SSH_REMOTE_DIR from .env.
set -euo pipefail

cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

: "${SSH_HOST:?SSH_HOST must be set in .env (e.g. mohit@192.168.0.37)}"
REMOTE_DIR="${SSH_REMOTE_DIR:-~/sastaspace}"

cmd="${1:-help}"
shift || true

rsync_code() {
  # Sync source tree (NOT .env) to remote. Dotfiles are included by rsync by
  # default unless excluded; we exclude .env specifically so the remote keeps
  # its own (which should have 192.168.0.37 URLs).
  rsync -avz --delete \
    --exclude '.git' \
    --exclude '.env' \
    --exclude '.env.local' \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude 'dist' \
    --exclude 'build' \
    --exclude '**/target' \
    --exclude '*.log' \
    ./ "$SSH_HOST:$REMOTE_DIR/"
}

ssh_run() {
  ssh "$SSH_HOST" "cd $REMOTE_DIR && $*"
}

ssh_run_tty() {
  ssh -t "$SSH_HOST" "cd $REMOTE_DIR && $*"
}

bootstrap_env() {
  # One-time helper: take local .env, rewrite all localhost references to
  # the remote host's LAN IP, and scp it to the remote as .env. Requires
  # REMOTE_HOST to be set (the IP/hostname the box is reachable as from
  # your browser — e.g. 192.168.0.37).
  local remote_host="${REMOTE_HOST:-}"
  if [[ -z "$remote_host" ]]; then
    # Best-effort guess: strip "user@" from SSH_HOST
    remote_host="${SSH_HOST##*@}"
  fi
  if [[ -z "$remote_host" ]]; then
    echo "Set REMOTE_HOST (e.g. 192.168.0.37) and retry" >&2
    exit 1
  fi
  local tmp
  tmp=$(mktemp)
  sed -e "s|http://localhost:|http://${remote_host}:|g" \
      -e "s|https://sastaspace.com|http://${remote_host}:3000|g" \
      .env > "$tmp"
  echo "Uploading rewritten .env to $SSH_HOST:$REMOTE_DIR/.env ..."
  ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR"
  scp "$tmp" "$SSH_HOST:$REMOTE_DIR/.env"
  rm -f "$tmp"
  echo "Done. Review it with: ssh $SSH_HOST 'cat $REMOTE_DIR/.env'"
}

case "$cmd" in
  sync)      rsync_code ;;
  env)       bootstrap_env ;;
  up)        rsync_code; ssh_run "make up-full" ;;
  up-core)   rsync_code; ssh_run "make up" ;;
  down)      ssh_run "make down" ;;
  reset)     ssh_run "make reset" ;;
  logs)      ssh_run_tty "make logs" ;;
  migrate)   ssh_run "make migrate" ;;
  psql)      ssh_run_tty "make psql" ;;
  exec)      ssh_run_tty "$*" ;;
  status)    ssh_run "docker compose -f infra/docker-compose.yml ps" ;;
  help|*)
    cat <<'EOF'
Usage: scripts/remote.sh <cmd>

  sync        rsync the repo (no .env) to SSH_HOST:SSH_REMOTE_DIR
  env         bootstrap a remote .env from local .env with localhost rewritten
              (uses REMOTE_HOST or the host part of SSH_HOST)
  up          sync + `make up-full` on remote (services + landing container)
  up-core     sync + `make up` on remote (services only; run apps on host)
  down        `make down` on remote
  reset       `make reset` on remote (destroys volumes)
  logs        tail remote logs
  migrate     run `make migrate` on remote
  psql        open psql against the remote postgres
  status      docker compose ps on remote
  exec <cmd>  run an arbitrary command in REMOTE_DIR
EOF
    ;;
esac
