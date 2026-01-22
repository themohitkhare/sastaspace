.PHONY: deploy-dev deploy-prod test-backend test-frontend-sastadice test-frontend-sastaspace test-full test-e2e-sastadice test-e2e-auction test-e2e-all

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
