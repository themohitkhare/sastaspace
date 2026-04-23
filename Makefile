.PHONY: help ci dev new migrate lint test build deploy-status deploy-logs

help:
	@echo "Targets: dev new migrate lint test build ci"

ci: lint test

lint:
	@echo "lint placeholder"

test:
	@echo "test placeholder"

dev:
	./scripts/dev.sh $(p)

new:
	./scripts/new-project.sh $(p)

migrate:
	@echo "migrate placeholder for project $(p)"

build:
	@echo "build placeholder"

deploy-status:
	@echo "deploy status placeholder"

deploy-logs:
	@echo "deploy logs placeholder"
