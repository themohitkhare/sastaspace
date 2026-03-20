.PHONY: ci install lint test

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check sastaspace/ tests/
	uv run ruff format --check sastaspace/ tests/

test:
	uv run pytest tests/ -v

ci: lint test
