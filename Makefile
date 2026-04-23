.PHONY: help ci lint test verify \
        keys up up-full down reset logs ps migrate psql env-check \
        dev new \
        remote-sync remote-env remote-up remote-up-core remote-down \
        remote-reset remote-logs remote-migrate remote-psql remote-status \
        build deploy-status deploy-logs

COMPOSE := docker compose --env-file .env -f infra/docker-compose.yml
REMOTE  := ./scripts/remote.sh

help:
	@echo "Local dev:"
	@echo "  make keys         Generate JWT_SECRET + ANON_KEY + SERVICE_ROLE_KEY into .env"
	@echo "  make up           Start shared services (postgres, postgrest, gotrue, pg-meta, studio)"
	@echo "  make up-full      Same as 'up' plus the landing app as a container"
	@echo "  make migrate      Apply db/migrations/*.sql in order"
	@echo "  make verify       Run the full end-to-end assertion suite (57 checks)"
	@echo "  make logs         Tail compose logs"
	@echo "  make ps           Show container status"
	@echo "  make psql         Open psql in the postgres container"
	@echo "  make down         Stop containers (keep volumes)"
	@echo "  make reset        Stop and destroy volumes (wipe data)"
	@echo ""
	@echo "Projects:"
	@echo "  make dev p=<name> Run a project's dev server (runs scripts/dev.sh)"
	@echo "  make new p=<name> Scaffold a new project from the template"
	@echo ""
	@echo "Remote (ssh \$$SSH_HOST, default 192.168.0.37):"
	@echo "  make remote-env       Build a remote .env from local .env (rewrite localhost)"
	@echo "  make remote-up        Sync + 'make up-full' on the remote box"
	@echo "  make remote-up-core   Sync + 'make up' on the remote box (no landing container)"
	@echo "  make remote-migrate   Run migrations on remote"
	@echo "  make remote-logs      Tail remote logs"
	@echo "  make remote-psql      psql into remote postgres"
	@echo "  make remote-down      Stop remote stack"
	@echo "  make remote-reset     Destroy remote volumes"
	@echo "  make remote-status    docker compose ps on remote"

# ---------- CI placeholders ----------------------------------------------
ci: lint test

lint:
	@echo "lint placeholder"

test:
	@echo "test placeholder"

# ---------- Local compose -------------------------------------------------
env-check:
	@test -f .env || (echo "No .env found. Run 'make keys' first." && exit 1)

keys:
	./scripts/gen-keys.sh

up: env-check
	$(COMPOSE) up -d

up-full: env-check
	$(COMPOSE) --profile full up -d --build

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

migrate: env-check
	./scripts/migrate.sh

verify: env-check
	./scripts/verify.sh

psql:
	docker exec -it sastaspace-postgres psql -U postgres -d sastaspace

# ---------- Projects ------------------------------------------------------
dev:
	./scripts/dev.sh $(p)

new:
	./scripts/new-project.sh $(p)

# ---------- Remote (ssh) --------------------------------------------------
remote-sync:
	$(REMOTE) sync

remote-env:
	$(REMOTE) env

remote-up:
	$(REMOTE) up

remote-up-core:
	$(REMOTE) up-core

remote-down:
	$(REMOTE) down

remote-reset:
	$(REMOTE) reset

remote-logs:
	$(REMOTE) logs

remote-migrate:
	$(REMOTE) migrate

remote-psql:
	$(REMOTE) psql

remote-status:
	$(REMOTE) status

# ---------- Placeholders kept for back-compat -----------------------------
build:
	@echo "build placeholder"

deploy-status:
	@echo "deploy status placeholder"

deploy-logs:
	@echo "deploy logs placeholder"
