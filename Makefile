.PHONY: deploy-dev deploy-prod test-backend test-frontend-sastadice test-frontend-sastaspace test-full test-e2e-sastadice test-e2e-auction test-e2e-all complexity lint typecheck test-cov audit

deploy-dev: ## Deploy all services in development mode
	docker-compose up -d --build

deploy-prod: ## Deploy all services in production mode
	docker-compose up -d --build --force-recreate

test-backend: ## Run backend tests
	cd backend && uv run pytest tests/ -v

test-frontend-sastadice: ## Run sastadice frontend tests
	@export NVM_DIR="$$HOME/.nvm" && [ -s "$$NVM_DIR/nvm.sh" ] && \. "$$NVM_DIR/nvm.sh" && \
	cd frontends/sastadice && \
	([ -f .nvmrc ] && nvm use || nvm use --lts) && \
	npm test -- --run

test-frontend-sastaspace: ## Run sastaspace frontend tests (placeholder - no tests yet)
	@echo "No tests configured for sastaspace frontend"

test-e2e-sastadice: ## Run sastadice E2E tests with Playwright
	@export NVM_DIR="$$HOME/.nvm" && [ -s "$$NVM_DIR/nvm.sh" ] && \. "$$NVM_DIR/nvm.sh" && \
	cd frontends/sastadice && \
	([ -f .nvmrc ] && nvm use || nvm use --lts) && \
	npx playwright test tests/e2e/ --workers=2

test-e2e-auction: ## Run only auction E2E tests
	@export NVM_DIR="$$HOME/.nvm" && [ -s "$$NVM_DIR/nvm.sh" ] && \. "$$NVM_DIR/nvm.sh" && \
	cd frontends/sastadice && \
	([ -f .nvmrc ] && nvm use || nvm use --lts) && \
	npx playwright test tests/e2e/auction_complete.spec.js --headed

test-e2e-all: test-e2e-sastadice ## Run all E2E tests

test-full: test-backend test-frontend-sastadice ## Run all tests

complexity: ## Check cyclomatic complexity (max CC=10)
	@echo "Checking cyclomatic complexity (max CC=10)..."
	cd backend && uv run radon cc app/ -a -nc --total-average || true
	@cd backend && uv run radon cc app/ --min C > /dev/null 2>&1 && echo "FAIL: Functions with CC > 10 found" && exit 1 || echo "OK"

lint: ## Run ruff linting and formatting checks
	cd backend && uv run ruff check app/ tests/
	cd backend && uv run ruff format --check app/ tests/

typecheck: ## Run mypy type checking
	cd backend && uv run mypy app/

test-cov: ## Run tests with 100% coverage requirement
	cd backend && uv run pytest tests/ --cov=app --cov-fail-under=100 --cov-branch -v

audit: lint typecheck complexity test-cov ## Run all quality gates
	@echo "All quality gates passed!"

dashboard: ## Generate and open RepoHealth dashboard
	@echo "Collecting backend coverage..."
	cd backend && uv run pytest tests/ --cov=app --cov-report=xml --cov-report=html -q || true
	@echo "Collecting frontend coverage..."
	@for dir in frontends/*/; do \
		if [ -f "$$dir/package.json" ] && grep -q "test:coverage" "$$dir/package.json"; then \
			echo "Running coverage for $$dir..."; \
			cd "$$dir" && npm run test:coverage -- --run || true; \
			cd -; \
		fi; \
	done
	@echo "Generating dashboard..."
	cd backend && uv run python3 ../scripts/generate_dashboard.py
	@echo "Dashboard generated: dashboard.html"
	@python3 -c "import webbrowser; webbrowser.open('dashboard.html')" || open dashboard.html || xdg-open dashboard.html
