REMOTE_HOST   ?= 192.168.0.38
REMOTE_USER   ?= mkhare
REMOTE_DIR    ?= ~/sastaspace
REGISTRY      := localhost:32000
SSH           := ssh $(REMOTE_USER)@$(REMOTE_HOST)
RSYNC_EXCLUDE := --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
                 --exclude='.venv' --exclude='*.pyc' --exclude='.next' \
                 --exclude='test-results' --exclude='*.egg-info'

.PHONY: ci install lint test dev dev-api dev-web \
        deploy deploy-build deploy-logs deploy-status deploy-down k8s-apply \
        deploy-monitoring monitoring-status monitoring-logs

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

# ── Deployment (microk8s) ─────────────────────────────────────────────────────

deploy:
	@echo "→ Syncing code to $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)..."
	@rsync -az --delete $(RSYNC_EXCLUDE) . $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)
	@echo "→ Building images on remote..."
	@$(SSH) "cd $(REMOTE_DIR) && \
	  docker build -t $(REGISTRY)/sastaspace-backend:latest -f backend/Dockerfile . && \
	  docker build -t $(REGISTRY)/sastaspace-frontend:latest -f web/Dockerfile web/ && \
	  docker push $(REGISTRY)/sastaspace-backend:latest && \
	  docker push $(REGISTRY)/sastaspace-frontend:latest"
	@echo "→ Applying k8s manifests..."
	@$(MAKE) k8s-apply
	@echo "→ Rolling restart..."
	@$(SSH) "sudo microk8s kubectl rollout restart deployment/backend deployment/frontend -n sastaspace"
	@$(SSH) "sudo microk8s kubectl rollout status deployment/backend deployment/frontend -n sastaspace"
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
	@echo "→ Creating dashboards ConfigMap from JSON files..."
	@$(SSH) "sudo microk8s kubectl create configmap grafana-dashboards \
	  --namespace monitoring \
	  --from-file=/home/$(REMOTE_USER)/sastaspace/k8s/monitoring/dashboards/ \
	  --dry-run=client -o yaml | sudo microk8s kubectl apply -f -"
	@echo "→ Applying monitoring manifests..."
	@$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/monitoring/namespace.yaml"
	@$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/monitoring/"
	@echo "✓ Monitoring deployed. Dashboard: https://monitor.sastaspace.com"

monitoring-status:
	@$(SSH) "sudo microk8s kubectl get pods,svc,ingress -n monitoring"

monitoring-logs:
	@$(SSH) "sudo microk8s kubectl logs -f -n monitoring -l 'app in (grafana,prometheus,loki)' --max-log-requests=6"
