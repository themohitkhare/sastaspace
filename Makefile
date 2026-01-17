.PHONY: deploy-dev deploy-prod test-backend test-frontend-sastadice test-frontend-sastaspace test-full

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

test-full: test-backend test-frontend-sastadice ## Run all tests
