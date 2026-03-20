.PHONY: ci install lint test

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check sastaspace/
	uv run ruff format --check sastaspace/

test:
	uv run pytest tests/ -v; ec=$$?; test $$ec -eq 0 -o $$ec -eq 5

ci: lint test
