REMOTE_HOST   ?= taxila
REMOTE_USER   ?= mkhare
REMOTE_DIR    ?= ~/sastaspace
REGISTRY      := localhost:32000
SSH           := ssh $(REMOTE_USER)@$(REMOTE_HOST)
RSYNC_EXCLUDE := --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
                 --exclude='.venv' --exclude='*.pyc' --exclude='.next' \
                 --exclude='test-results' --exclude='*.egg-info'

.PHONY: ci install lint k8s-lint test dupes semgrep audit dev dev-api dev-web \
        deploy deploy-build deploy-logs deploy-status deploy-down k8s-apply \
        deploy-monitoring monitoring-status monitoring-logs \
        vikunja-deploy vikunja-status vikunja-logs vikunja-restart

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check sastaspace/ tests/
	uv run ruff format --check sastaspace/ tests/

k8s-lint:  ## Validate k8s manifests with kubeconform
	kubeconform -summary -strict k8s/*.yaml k8s/monitoring/*.yaml \
		k8s/vikunja/namespace.yaml k8s/vikunja/vikunja.yaml k8s/vikunja/ingress.yaml

test:
	uv run pytest tests/ -v

dupes:  ## Check for duplicate code
	jscpd sastaspace/ web/src/ --min-lines 10 --min-tokens 50 --reporters consoleFull --threshold 5

semgrep:  ## Static analysis with semgrep
	semgrep scan --config auto --severity ERROR --exclude='node_modules' --exclude='.next' sastaspace/ web/src/

audit:  ## Scan Python dependencies for known vulnerabilities
	uv run pip-audit

ci: lint test

dev:
	@echo "Starting FastAPI (8080) and Next.js (3000)..."
	$(MAKE) dev-api & $(MAKE) dev-web & wait

dev-api:
	uv run uvicorn sastaspace.server:app --host 127.0.0.1 --port 8080 --reload

dev-web:
	cd web && npm run dev

# ── Deployment (microk8s) ─────────────────────────────────────────────────────

deploy:
	@echo "→ Syncing code to $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)..."
	@rsync -az --delete $(RSYNC_EXCLUDE) . $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)
	@echo "→ Building images on remote..."
	@$(SSH) "cd $(REMOTE_DIR) && \
	  docker build -t $(REGISTRY)/sastaspace-backend:latest -f backend/Dockerfile . && \
	  docker build -t $(REGISTRY)/sastaspace-frontend:latest --build-arg NEXT_PUBLIC_BACKEND_URL=https://api.sastaspace.com -f web/Dockerfile web/ && \
	  docker push $(REGISTRY)/sastaspace-backend:latest && \
	  docker push $(REGISTRY)/sastaspace-frontend:latest"
	@echo "→ Applying k8s manifests..."
	@$(MAKE) k8s-apply
	@echo "→ Rolling restart..."
	@$(SSH) "sudo microk8s kubectl rollout restart deployment/backend deployment/frontend deployment/worker -n sastaspace"
	@$(SSH) "sudo microk8s kubectl rollout status deployment/backend deployment/frontend deployment/worker -n sastaspace"
	@echo "✓ Deployed. Site: https://sastaspace.com"

k8s-apply:
	@$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/"

deploy-logs:
	@$(SSH) "sudo microk8s kubectl logs -f -n sastaspace -l 'app in (frontend,backend)' --max-log-requests=4"

deploy-status:
	@$(SSH) "sudo microk8s kubectl get pods,svc,ingress -n sastaspace"

deploy-down:
	@$(SSH) "sudo microk8s kubectl delete namespace sastaspace --ignore-not-found"

# ── Monitoring (Grafana + Prometheus + Loki) ──────────────────────────────────

deploy-monitoring:
	@echo "→ Prerequisite: grafana-admin secret must exist in monitoring namespace"
	@echo "  (see docs/DEPLOYMENT.md for first-time setup)"
	@echo "→ Syncing code to $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)..."
	@rsync -az --delete $(RSYNC_EXCLUDE) . $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)
	@echo "→ Applying monitoring manifests..."
	@$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/monitoring/namespace.yaml"
	@$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/monitoring/"
	@echo "✓ Monitoring deployed. Dashboard: https://monitor.sastaspace.com"

monitoring-status:
	@$(SSH) "sudo microk8s kubectl get pods,svc,ingress -n monitoring"

monitoring-logs:
	@$(SSH) "sudo microk8s kubectl logs -f -n monitoring -l 'app in (grafana,prometheus,loki)' --max-log-requests=6"

# ── Vikunja (Lead Tracking) ─────────────────────────────────────────────────

vikunja-deploy: ## Deploy Vikunja to k8s
	$(SSH) "cd $(REMOTE_DIR) && sudo microk8s kubectl apply -f k8s/vikunja/namespace.yaml -f k8s/vikunja/vikunja.yaml -f k8s/vikunja/ingress.yaml"
	@echo "→ Vikunja deployed. Access at https://tasks.sastaspace.com"

vikunja-status: ## Show Vikunja pod/svc/ingress status
	$(SSH) "sudo microk8s kubectl get pods,svc,ingress -n vikunja"

vikunja-logs: ## Tail Vikunja logs
	$(SSH) "sudo microk8s kubectl logs -n vikunja deploy/vikunja --tail=50 -f"

vikunja-restart: ## Rolling restart Vikunja
	$(SSH) "sudo microk8s kubectl rollout restart deployment/vikunja -n vikunja"
