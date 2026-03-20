.PHONY: ci install lint test dev dev-api dev-web

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check sastaspace/ tests/
	uv run ruff format --check sastaspace/ tests/

test:
	uv run pytest tests/ -v

ci: lint test

dev:
	@echo "Starting FastAPI (8080) and Next.js (3000)..."
	$(MAKE) dev-api & $(MAKE) dev-web & wait

dev-api:
	uv run uvicorn sastaspace.server:app --host 127.0.0.1 --port 8080 --reload

dev-web:
	cd web && npm run dev
