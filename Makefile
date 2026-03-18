.PHONY: deploy-dev deploy-prod test-backend test-frontend-sastadice test-frontend-sastaspace test-frontend-sastahero test-full test-e2e-sastadice test-e2e-auction test-e2e-all complexity lint typecheck test-cov audit ci ci-fast install-hooks simulate-games simulate-games-quick simulate-games-fuzz

deploy-dev: ## Deploy all services in development mode
	docker-compose up -d --build

deploy-prod: ## Deploy all services in production mode
	docker-compose up -d --build --force-recreate

test-backend: ## Run backend tests
	cd backend && uv run pytest tests/ -v

test-frontend-sastadice: ## Run sastadice frontend tests
	cd frontends/sastadice && bun run test -- --run

test-frontend-sastaspace: ## Run sastaspace frontend tests
	@echo "No tests configured for sastaspace frontend"

test-frontend-sastahero: ## Run sastahero frontend tests
	cd frontends/sastahero && npm run test -- --run

test-e2e-sastadice: ## Run sastadice E2E tests with Playwright
	cd frontends/sastadice && bun run test:e2e -- tests/e2e/ --workers=2

test-e2e-auction: ## Run only auction E2E tests
	cd frontends/sastadice && bun run test:e2e -- tests/e2e/auction_complete.spec.js --headed

test-e2e-all: test-e2e-sastadice ## Run all E2E tests

test-full: test-backend test-frontend-sastadice test-frontend-sastahero ## Run all tests

complexity: ## Check cyclomatic complexity (max CC=30 outside excluded modules)
	@echo "Checking cyclomatic complexity (max CC=30; exclude event_manager, simulation_manager)..."
	@cd backend && uv run radon cc app/ -a -nc --total-average || true
	@output=$$(cd backend && uv run radon cc app/ --min E --exclude "app/modules/sastadice/events/event_manager.py,app/modules/sastadice/services/simulation_manager.py" 2>&1); \
	if [ -n "$$output" ]; then echo "$$output"; echo "FAIL: Functions with CC > 30 found"; exit 1; fi; \
	echo "OK"

lint: ## Run ruff linting and formatting checks
	cd backend && uv run ruff check app/ tests/
	cd backend && uv run ruff format --check app/ tests/

typecheck: ## Run mypy type checking
	cd backend && uv run mypy app/

test-cov: ## Run tests with coverage (fail_under from backend/pyproject.toml)
	cd backend && uv run pytest tests/ --cov=app --cov-branch -q

audit: lint typecheck complexity test-cov ## Run all quality gates (sequential)
	@echo "All quality gates passed!"

# ── Fast parallel CI ────────────────────────────────────────────────
# Runs ALL checks in parallel using background jobs.
# Usage: make ci-fast   (or: make -j8 ci for Make-native parallelism)
ci-fast: ## Parallel CI: all quality gates + all tests in one shot
	@echo "=== CI-FAST: launching all checks in parallel ==="
	@fail=0; \
	(cd backend && uv run ruff check app/ tests/ && uv run ruff format --check app/ tests/) & pid_lint=$$!; \
	(cd backend && uv run mypy app/) & pid_type=$$!; \
	( \
		output=$$(cd backend && uv run radon cc app/ --min E --exclude "app/modules/sastadice/events/event_manager.py,app/modules/sastadice/services/simulation_manager.py" 2>&1); \
		if [ -n "$$output" ]; then echo "$$output"; echo "FAIL: CC > 30"; exit 1; fi; \
		echo "Complexity OK" \
	) & pid_cc=$$!; \
	(cd backend && uv run pytest tests/ --cov=app --cov-branch -q) & pid_cov=$$!; \
	(cd frontends/sastadice && bun run test -- --run) & pid_dice=$$!; \
	(cd frontends/sastahero && npm run test -- --run) & pid_hero=$$!; \
	for pid in $$pid_lint $$pid_type $$pid_cc $$pid_cov $$pid_dice $$pid_hero; do \
		wait $$pid || fail=1; \
	done; \
	if [ $$fail -eq 1 ]; then echo "=== CI-FAST FAILED ==="; exit 1; fi; \
	echo "=== CI-FAST PASSED ==="

ci: ci-fast ## Alias for ci-fast (parallel)

install-hooks: ## Install pre-commit hook that runs 'make ci-fast' (run once per clone)
	@mkdir -p .git/hooks
	@cp .githooks/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed. Commits will run 'make ci'."

dashboard: ## Generate and open RepoHealth dashboard
	@echo "Collecting backend coverage..."
	cd backend && uv run pytest tests/ --cov=app --cov-report=xml --cov-report=html -q || true
	@echo "Collecting frontend coverage..."
	@for dir in frontends/*/; do \
		if [ -f "$$dir/package.json" ] && grep -q "test:coverage" "$$dir/package.json"; then \
			echo "Running coverage for $$dir..."; \
			cd "$$dir" && bun run test:coverage -- --run || true; \
			cd -; \
		fi; \
	done
	@echo "Generating dashboard..."
	cd backend && uv run python3 ../scripts/generate_dashboard.py
	@echo "Dashboard generated: dashboard.html"
	@python3 -c "import webbrowser; webbrowser.open('dashboard.html')" || open dashboard.html || xdg-open dashboard.html

simulate-games: ## Run backend game simulation script (use ARGS='...' for script options)
	cd backend && uv run python scripts/simulate_games.py $(ARGS)

simulate-games-quick: ## Quick smoke test: 3 games, quiet, fixed seed (reproducible)
	cd backend && uv run python scripts/simulate_games.py --num-games 3 --quiet --seed 42

simulate-games-fuzz: ## Fuzz test: 8 combinatorial configs, quiet, fixed seed
	cd backend && uv run python scripts/simulate_games.py --fuzz --num-games 8 --quiet --seed 123
