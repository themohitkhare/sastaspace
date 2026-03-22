# Deployment Knowledge Base

> Complete setup guide for the sastaspace production server. Covers everything from OS install to live deployment.

## Server Specs

| | |
|---|---|
| **IP** | `192.168.0.38` |
| **OS** | Ubuntu 24.04 LTS |
| **CPU** | AMD Ryzen 9 7900X |
| **GPU** | AMD RX 7900 XTX (gfx1100, 20GB VRAM) |
| **User** | `mkhare` |
| **Hostname** | taxila |

---

## Secrets

All secrets are stored in the **macOS Keychain** on the dev machine under account `sastaspace`.
Never stored in git, `.env` files, or on the server.

| Secret | Keychain service name | Usage |
|--------|----------------------|-------|
| Cloudflare API token | `cloudflare-api-token` | DNS records, tunnel management |
| claude-code-api key | `claude-code-api-key` | Backend → claude-code-api auth |

Retrieve in scripts:
```bash
security find-generic-password -a sastaspace -s <service-name> -w
```

Add a new secret:
```bash
security add-generic-password -a sastaspace -s <service-name> -w "<value>" -U
```

---

## 1. SSH Setup

After OS reinstall the host key changes. Clear the old one:

```bash
ssh-keygen -R 192.168.0.38
ssh mkhare@192.168.0.38   # accept new key
```

### Passwordless SSH

```bash
ssh-copy-id mkhare@192.168.0.38
```

### Enable Root SSH (optional)

```bash
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin yes
sudo systemctl restart sshd
ssh-copy-id root@192.168.0.38
```

---

## 2. Shell: zsh + Oh My Zsh

```bash
sudo apt install -y zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" '' --unattended
sudo chsh -s $(which zsh) mkhare
```

---

## 3. AMD GPU Drivers + ROCm 6.3

```bash
# Download and install AMD GPU installer
wget https://repo.radeon.com/amdgpu-install/6.3.3/ubuntu/noble/amdgpu-install_6.3.60303-1_all.deb
sudo apt install -y ./amdgpu-install_6.3.60303-1_all.deb
sudo amdgpu-install --usecase=rocm --no-32

# Add user to GPU groups
sudo usermod -aG video,render mkhare

sudo reboot
```

### Verify

```bash
rocm-smi
rocminfo | grep gfx  # should show gfx1100
```

---

## 4. btop with GPU Support

The apt version (1.3.0) segfaults. Build from source with g++-14 for AMD GPU support:

```bash
sudo apt install -y g++-14 make git
git clone --depth=1 --branch v1.4.6 https://github.com/aristocratos/btop /tmp/btop-src
cd /tmp/btop-src
make GPU_SUPPORT=true RSMI_STATIC=false \
  ADDFLAGS='-I/opt/rocm/include -L/opt/rocm/lib' \
  CXX=g++-14 -j$(nproc)
sudo cp bin/btop /usr/local/bin/btop
```

Press `g` in btop to toggle GPU panel.

---

## 5. LVM Disk Expansion

The default Ubuntu LVM install only uses 100GB. The VG has ~1.7TB free:

```bash
sudo lvextend -L +200G /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
df -h /  # verify new size
```

---

## 6. Screen Rotation (Persistent)

Console is rotated 180°. Apply on every boot via systemd:

```bash
sudo tee /etc/systemd/system/fbcon-rotate.service << EOF
[Unit]
Description=Rotate framebuffer console
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo 3 > /sys/class/graphics/fbcon/rotate_all"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now fbcon-rotate.service
```

---

## 7. Node.js + Claude Code CLI

```bash
sudo bash -c "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -"
sudo apt install -y nodejs
sudo npm install -g @anthropic-ai/claude-code
claude --version
```

---

## 8. vLLM (AMD ROCm via Docker)

### Install Docker

```bash
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sudo sh /tmp/get-docker.sh
sudo usermod -aG docker mkhare
```

### Pull ROCm vLLM Image

```bash
sudo docker pull rocm/vllm:latest   # ~35GB, ensure enough disk space
```

### Run Coding Model (Qwen2.5-Coder-14B-AWQ)

```bash
sudo docker run -d \
  --name vllm-coder \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --group-add render \
  --ipc=host \
  -p 127.0.0.1:8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  rocm/vllm:latest \
  vllm serve Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
    --gpu-memory-utilization 0.85 \
    --max-model-len 32768 \
    --host 0.0.0.0 --port 8000
```

> Note: bind to `127.0.0.1:8001` to keep it off the public internet.

---

## 9. microk8s

```bash
# Already installed via snap. Fix permissions:
sudo usermod -a -G microk8s mkhare
sudo chown -R mkhare ~/.kube
newgrp microk8s

# Enable required addons
sudo microk8s enable ingress hostpath-storage cert-manager registry
```

### Addons summary

| Addon | Purpose |
|---|---|
| `ingress` | nginx ingress controller (listens on :80) |
| `hostpath-storage` | PVC storage from host disk |
| `cert-manager` | TLS certificate management |
| `registry` | Local image registry at `localhost:32000` |

---

## 10. k9s

```bash
curl -sL https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz \
  -o /tmp/k9s.tar.gz
sudo tar xz -C /usr/local/bin k9s -f /tmp/k9s.tar.gz

# Configure kubeconfig for microk8s
mkdir -p ~/.kube
sudo microk8s config > ~/.kube/config
chmod 600 ~/.kube/config

k9s  # launch
```

---

## 11. Cloudflare Tunnel (systemd service)

Tunnel routes public traffic to the microk8s nginx ingress without exposing any ports.

### Tunnel details

| | |
|---|---|
| **Name** | sastaspace-prod |
| **Tunnel ID** | `b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8` |
| **Account ID** | stored in Cloudflare dashboard |
| **Zone** | sastaspace.com |

### Install cloudflared

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-main.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
  https://pkg.cloudflare.com/cloudflared any main" \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared
```

### Install as root systemd service

```bash
sudo cloudflared service install <TUNNEL_TOKEN>
sudo systemctl status cloudflared
```

Get the tunnel token from the Cloudflare dashboard or re-create via API:

```bash
# Retrieve from macOS Keychain (stored under account: sastaspace)
CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
ACCOUNT_ID="<CF_ACCOUNT_ID>"

# Create tunnel
curl -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"sastaspace-prod","config_src":"cloudflare"}'

# Configure ingress (routes to microk8s nginx)
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel/b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "ingress": [
        {"hostname": "sastaspace.com",     "service": "http://localhost:80"},
        {"hostname": "www.sastaspace.com", "service": "http://localhost:80"},
        {"hostname": "api.sastaspace.com", "service": "http://localhost:80"},
        {"hostname": "crm.sastaspace.com", "service": "http://localhost:80"},
        {"hostname": "monitor.sastaspace.com", "service": "http://localhost:80"},
        {"service": "http_status:404"}
      ]
    }
  }'
```

### DNS records

All CNAMEs point to `b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8.cfargotunnel.com` (proxied):
- `sastaspace.com`
- `www.sastaspace.com`
- `*.sastaspace.com`
- `api.sastaspace.com`
- `crm.sastaspace.com`
- `monitor.sastaspace.com`

---

## 12. claude-code-api (systemd service)

OpenAI-compatible API gateway for Claude Code CLI.

```bash
git clone https://github.com/codingworkflow/claude-code-api ~/claude-code-api
cd ~/claude-code-api
python3 -m venv .venv
.venv/bin/pip install -e .
```

```bash
sudo tee /etc/systemd/system/claude-code-api.service << EOF
[Unit]
Description=Claude Code API Gateway
After=network.target

[Service]
Type=simple
User=mkhare
WorkingDirectory=/home/mkhare/claude-code-api
ExecStart=/home/mkhare/claude-code-api/.venv/bin/uvicorn claude_code_api.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=HOME=/home/mkhare

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now claude-code-api
```

Endpoints (localhost only):
- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/v1/chat/completions`

---

## 13. Firewall (UFW)

Only SSH, HTTP, and HTTPS are open. Everything else (vLLM :8001, k8s API :16443, etc.) is blocked:

```bash
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment SSH
sudo ufw allow 80/tcp comment HTTP
sudo ufw allow 443/tcp comment HTTPS
sudo ufw status verbose
```

---

## 14. Application Deployment (microk8s)

### Pod architecture

The application runs as **5 pods** in the `sastaspace` namespace:

| Pod | Image | Role |
|-----|-------|------|
| `backend` | `sastaspace-backend` | FastAPI API server (port 8080). Handles HTTP requests, SSE streams, static site serving. Uses `MODE=server` entrypoint. |
| `worker` | `sastaspace-backend` (same image) | Async job consumer. Reads from Redis Stream, runs crawl→redesign→deploy pipeline. Uses `MODE=worker` entrypoint. Strategy: `Recreate` (not rolling). |
| `browserless` | `ghcr.io/browserless/chromium` | Headless Chromium service for web crawling via CDP WebSocket (port 3000). Chromium was removed from the backend image to reduce size. |
| `mongodb` | `mongo:7` | Job persistence, site registry, dedup index. PVC: 5Gi. |
| `redis` | `redis:7-alpine` | Job queue (Redis Streams), pub/sub for SSE status updates, webhook dedup. PVC: 2Gi, appendonly. |

The backend and worker share the same Docker image (`backend/Dockerfile`). The `entrypoint.sh` script checks `$MODE` to decide whether to run `uvicorn` (server) or `python -m sastaspace.worker` (worker).

### Backend Dockerfile

`python:3.11-slim` — lightweight image, no Chromium. System deps: `curl` (healthcheck), `libmagic1` (asset validation). Runs as `appuser` (UID 1000, non-root).

### k8s manifests

```
k8s/
├── namespace.yaml           # sastaspace namespace
├── configmap.yaml           # shared env vars (non-secret)
├── backend.yaml             # FastAPI deployment + service + sites PVC (10Gi)
├── worker.yaml              # async job worker deployment
├── browserless.yaml         # headless Chromium service
├── frontend.yaml            # Next.js deployment + service
├── mongodb.yaml             # MongoDB deployment + service + PVC (5Gi)
├── redis.yaml               # Redis deployment + service + PVC (2Gi, appendonly)
├── ingress.yaml             # nginx ingress (sastaspace.com, api.*, www.*)
├── twenty/
│   ├── namespace.yaml       # twenty namespace
│   ├── secrets.yaml         # Twenty env secrets (template — fill before first deploy)
│   ├── server.yaml          # Twenty CRM server + service
│   ├── worker.yaml          # Twenty CRM worker
│   ├── postgres.yaml        # PostgreSQL for Twenty
│   ├── redis.yaml           # Redis for Twenty
│   └── ingress.yaml         # nginx ingress for crm.sastaspace.com
└── monitoring/
    ├── namespace.yaml       # monitoring namespace
    ├── grafana.yaml         # Grafana deployment + service
    ├── prometheus.yaml      # Prometheus deployment + service + config
    ├── loki.yaml            # Loki deployment + service
    ├── promtail.yaml        # Promtail DaemonSet (log shipper)
    ├── node-exporter.yaml   # node-exporter DaemonSet (host metrics)
    ├── kube-state-metrics.yaml  # kube-state-metrics deployment
    ├── blackbox-exporter.yaml   # blackbox-exporter deployment
    ├── redis-exporter.yaml  # Redis metrics exporter
    ├── dcgm-exporter.yaml   # GPU metrics exporter
    ├── dashboards/          # Grafana dashboard JSON files
    │   ├── gpu-monitoring.json
    │   ├── pod-logs.json
    │   └── sastaspace-business.json
    └── ingress.yaml         # nginx ingress for monitor.sastaspace.com → Grafana
```

### ConfigMap (`k8s/configmap.yaml`)

Non-secret environment variables shared by backend and worker pods:

| Key | Value | Purpose |
|-----|-------|---------|
| `CLAUDE_CODE_API_URL` | `http://192.168.0.38:8000/v1` | claude-code-api gateway (host network) |
| `SASTASPACE_SITES_DIR` | `/data/sites` | PVC mount path for generated HTML |
| `REDIS_URL` | `redis://redis:6379` | Redis service (k8s DNS) |
| `MONGODB_URL` | `mongodb://mongodb:27017` | MongoDB service (k8s DNS) |
| `MONGODB_DB` | `sastaspace` | Database name |
| `OLLAMA_URL` | `http://192.168.0.38:11434/v1` | Ollama for free-tier redesigns (host network) |
| `BROWSERLESS_URL` | `ws://browserless:3000` | Browserless CDP WebSocket (k8s DNS) |

Secrets (Twenty API keys, webhook secrets, admin key) are in `sastaspace-env` Secret, injected via `secretRef`.

### Browserless

Dedicated headless Chromium pod using `ghcr.io/browserless/chromium:latest`. The backend image no longer contains Playwright/Chromium — all browser operations go through Browserless via CDP WebSocket.

- Connects from worker/backend via `ws://browserless:3000` (Playwright `connect_over_cdp`)
- Concurrency: 5 simultaneous sessions, 10 queued, 60s timeout per session
- Resources: 256Mi–2Gi RAM, 100m–1000m CPU
- Readiness probe: `GET /json/version` on port 3000

### Local image registry

Images are built on the remote machine and pushed to the microk8s local registry:

```bash
docker build -t localhost:32000/sastaspace-backend:latest -f backend/Dockerfile .
docker build -t localhost:32000/sastaspace-frontend:latest --build-arg NEXT_PUBLIC_BACKEND_URL=https://api.sastaspace.com -f web/Dockerfile web/
docker push localhost:32000/sastaspace-backend:latest
docker push localhost:32000/sastaspace-frontend:latest
```

### Deploy via Makefile

```bash
make deploy            # rsync + build images + apply manifests + rolling restart
make deploy-status     # show pod/svc/ingress status
make deploy-logs       # tail logs from backend + frontend pods
make deploy-down       # delete sastaspace namespace
make deploy-monitoring # apply monitoring manifests
make monitoring-status # check monitoring pod/svc/ingress status
make monitoring-logs   # tail monitoring pod logs
make deploy-twenty     # deploy Twenty CRM stack
make twenty-status     # check Twenty pod/svc/ingress status
make twenty-logs       # tail Twenty server logs
make twenty-setup      # first-time Twenty setup instructions
```

Configure remote target if different from default:

```bash
make deploy REMOTE_HOST=192.168.0.38 REMOTE_USER=mkhare
```

### Monitoring stack

Located in `k8s/monitoring/` directory — deployed separately from the app.

Components: Prometheus (metrics), Loki (logs), Promtail (log shipper), Grafana (dashboards), node-exporter (host metrics), kube-state-metrics, blackbox-exporter, redis-exporter, dcgm-exporter (GPU metrics).

Dashboards are provisioned from `k8s/monitoring/dashboards/`:
- `gpu-monitoring.json` — GPU utilization and memory
- `pod-logs.json` — live pod log viewer
- `sastaspace-business.json` — redesign job metrics, success rates, latency

First-time setup requires creating the Grafana admin secret:

```bash
sudo microk8s kubectl create namespace monitoring
sudo microk8s kubectl create secret generic grafana-admin \
  --namespace monitoring \
  --from-literal=admin-password='<your-password>'
make deploy-monitoring
```

### Twenty CRM stack

Self-hosted Twenty CRM for lead management. Runs in separate `twenty` namespace.

Components: Twenty server + worker, PostgreSQL (PVC), Redis.

First-time setup:
```bash
# 1. Edit secrets template with real values
vi k8s/twenty/secrets.yaml
# 2. Deploy
make deploy-twenty
# 3. Verify
make twenty-status
# 4. Access at https://crm.sastaspace.com
```

The app auto-syncs data to Twenty CRM:
- Job completion/failure pushes company + redesign job records
- Contact form submissions create Person records
- Webhook endpoint (`/webhooks/twenty`) handles admin actions (delete, reprocess)
- Admin endpoints (`/admin/sync`, `/admin/sites`) for reconciliation

---

## 15. CI/CD Pipeline (GitHub Actions)

The pipeline runs on a **self-hosted runner** on the server itself (192.168.0.38).

### Jobs

| Job | Trigger | What it does |
|-----|---------|-------------|
| `test` | push/PR to main | lint (ruff), format check, duplicate code detection (jscpd), static analysis (semgrep), pytest (parallel), k8s manifest validation (kubeconform) |
| `security` | push/PR to main (after test) | pip-audit (OSV), npm audit, Trivy filesystem scan (secrets + misconfigs) |
| `deploy` | push to main only (after test + security) | build backend + frontend images, Trivy image scan per image, push to registry, apply all k8s manifests (app + monitoring + Twenty if secrets exist), rolling restart all deployments, rollout status wait |

### Pipeline flow

```
test ──► security ──► deploy
                       │
                       ├─ build backend image → Trivy scan → push
                       ├─ build frontend image → Trivy scan → push
                       ├─ kubectl apply k8s/ (app)
                       ├─ kubectl apply k8s/monitoring/ (monitoring)
                       ├─ kubectl apply k8s/twenty/ (if secrets exist)
                       ├─ rolling restart all deployments in sastaspace ns
                       ├─ rolling restart prometheus + grafana + promtail in monitoring ns
                       ├─ rolling restart Twenty deployments (if present)
                       └─ rollout status wait (300s timeout per deployment)
```

### Security scanning

```bash
# Python CVEs (OSV database)
uv export --no-dev --no-editable --no-emit-project --format requirements-txt > /tmp/requirements-audit.txt
uv tool run pip-audit --requirement /tmp/requirements-audit.txt --vulnerability-service osv

# npm CVEs (high+ only)
npm audit --audit-level=high --omit=dev

# Trivy: repo secrets + k8s misconfigs
trivy fs . --scanners secret,misconfig --exit-code 1 --severity HIGH,CRITICAL \
  --ignorefile .trivyignore --skip-dirs node_modules,.git

# Trivy: container image CVEs (per image after build)
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignorefile .trivyignore \
  localhost:32000/sastaspace-backend:latest
```

Suppressions are documented in `.trivyignore` with justifications.

### Self-hosted runner

The GitHub Actions runner is registered on the server. To check or restart it:
```bash
# Status
sudo systemctl status actions.runner.*

# Re-register if needed (get token from GitHub repo → Settings → Actions → Runners)
cd ~/actions-runner
./config.sh --url https://github.com/<org>/<repo> --token <TOKEN>
sudo ./svc.sh install && sudo ./svc.sh start
```

---

## 16. Traffic Architecture

```
Browser / API client
        │
        ▼
  Cloudflare Edge
  (DDoS protection, TLS termination, CDN)
        │
        ▼ QUIC / HTTP2
  cloudflared (systemd, /etc/systemd/system/cloudflared.service)
  Tunnel: b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8
        │
        ▼ HTTP
  localhost:80
  microk8s nginx ingress controller
        │
        ├─── sastaspace.com / www ──────▶ frontend service :3000
        │                                 (Next.js pod)
        │
        ├─── api.sastaspace.com ────────▶ backend service :8080
        │                                 (FastAPI pod)
        │
        ├─── crm.sastaspace.com ────────▶ twenty-server service :3000
        │                                 (Twenty CRM pod, twenty ns)
        │
        └─── monitor.sastaspace.com ────▶ grafana service :3001
                                          (Grafana pod, monitoring ns)
```

### Internal service communication (k8s DNS)

```
backend pod ──► redis:6379         (job queue, pub/sub, dedup)
           ──► mongodb:27017       (job persistence, site registry)

worker pod  ──► redis:6379         (consume jobs from stream)
            ──► mongodb:27017      (update job status)
            ──► browserless:3000   (CDP WebSocket for Chromium)
            ──► 192.168.0.38:8000  (claude-code-api on host, via configmap)
            ──► 192.168.0.38:11434 (Ollama on host, free tier)
```

### System services (non-k8s)

```
systemd services on host:
  cloudflared        — Cloudflare tunnel (auto-starts, survives reboot)
  claude-code-api    — OpenAI-compatible Claude API (localhost:8000)
  fbcon-rotate       — Console screen rotation on boot
  docker             — Container runtime (used for vLLM)
```

---

## 17. Job Processing Pipeline

The redesign pipeline is an async 3-step process managed by the worker pod via Redis Streams:

```
POST /redesign (backend)
  │
  ▼
Redis Stream (sastaspace:jobs)
  │
  ▼
Worker pod (consumer group: redesign-workers)
  │
  ├─ Step 1: Enhanced Crawl
  │    ├─ Homepage crawl via Browserless CDP (ws://browserless:3000)
  │    ├─ Extract + filter internal links (up to 50)
  │    ├─ LLM selects best 3 internal pages to crawl
  │    ├─ Parallel crawl of internal pages (30s timeout each)
  │    ├─ Download + validate assets (magic bytes, Pillow, defusedxml, YARA — no ClamAV)
  │    └─ LLM builds business profile from crawled text
  │
  ├─ Step 2: AI Redesign
  │    ├─ Premium tier: Agno multi-agent pipeline (analyst → strategist → generator → reviewer)
  │    └─ Free tier: Ollama single-shot (glm-4.7-flash)
  │
  └─ Step 3: Deploy
       ├─ Write HTML + assets to /data/sites/{subdomain}/
       ├─ Register in MongoDB (with URL hash for dedup)
       └─ Sync to Twenty CRM (fire-and-forget)
```

Status updates are published via Redis Pub/Sub → SSE to the frontend.

Checkpoints are saved to MongoDB after each step so crashed jobs can be recovered on restart (XAUTOCLAIM for messages idle >60s).

---

## 18. docker-compose (local development)

For local development, `docker-compose.yml` provides:

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `redis` | `redis:7-alpine` | 6379 | Job queue |
| `mongodb` | `mongo:7` | 27017 | Job persistence |
| `browserless` | `ghcr.io/browserless/chromium` | 3100→3000 | Headless Chromium |
| `backend` | Built from `backend/Dockerfile` | 8080 | API server (inline mode, no separate worker) |
| `frontend` | Built from `web/Dockerfile` | 3000 | Next.js app |
| `tests` | Built from `web/Dockerfile.test` | — | E2E tests (profile: `test`) |

```bash
docker compose up              # start all services
docker compose --profile test run tests  # run E2E tests
```

Backend connects to claude-code-api on host via `host.docker.internal:8000`.

---

## 19. Service Health Checks

```bash
# Cloudflare tunnel
sudo systemctl status cloudflared

# claude-code-api
curl http://localhost:8000/health

# microk8s cluster
sudo microk8s kubectl get pods -A

# k8s app pods
sudo microk8s kubectl get pods,svc,ingress -n sastaspace

# Worker logs (check for job processing)
sudo microk8s kubectl logs -n sastaspace deployment/worker --tail=50

# Browserless health
sudo microk8s kubectl logs -n sastaspace deployment/browserless --tail=20

# Twenty CRM
make twenty-status

# Monitoring
make monitoring-status

# GPU status
rocm-smi

# vLLM (if running)
sudo docker logs vllm-coder --tail 20
```

---

## 20. Useful Commands

```bash
# Tail all app logs
make deploy-logs

# Worker logs specifically
ssh mkhare@192.168.0.38 "sudo microk8s kubectl logs -n sastaspace deployment/worker --tail=100 -f"

# Interactive k8s UI
k9s

# GPU + system monitor
btop

# Restart a service
sudo systemctl restart claude-code-api

# Restart worker pod (picks up new image on rolling restart)
sudo microk8s kubectl rollout restart deployment/worker -n sastaspace

# Check Redis job queue
sudo microk8s kubectl exec -n sastaspace deployment/redis -- redis-cli XLEN sastaspace:jobs

# Check MongoDB job count
sudo microk8s kubectl exec -n sastaspace deployment/mongodb -- mongosh sastaspace --eval "db.jobs.countDocuments()"

# Check firewall
sudo ufw status verbose

# Disk usage
df -h && sudo lvs

# Full CI locally
make ci
```

---

## 21. Troubleshooting

### Crawl jobs failing

1. Check worker logs: `sudo microk8s kubectl logs -n sastaspace deployment/worker --tail=100`
2. Verify Browserless is healthy: `sudo microk8s kubectl get pods -n sastaspace -l app=browserless`
3. Verify claude-code-api is running: `curl http://localhost:8000/health` (from server)
4. Check Redis connectivity: `sudo microk8s kubectl exec -n sastaspace deployment/redis -- redis-cli ping`

### Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `'str' object has no attribute 'text_content'` | Wrong argument types passed to `build_business_profile` | Fixed in commit `a8b726bf` — redeploy |
| `Redis connection lost, reconnecting` | Redis pod restarting during rolling deploy | Transient — worker auto-reconnects after 2s |
| `Could not reach that website` | Browserless failed to load the target URL | Check if site is down, or Browserless is OOM |
| `Bot protection detected` | Target site returned <500 chars of text | Site is blocking automated crawlers |
| `Timeout after 30s` | Internal page took too long to load | Normal for slow sites — other pages still crawled |

### Worker not processing jobs

1. Check if worker pod is running: `sudo microk8s kubectl get pods -n sastaspace -l app=worker`
2. Check Redis stream length: `redis-cli XLEN sastaspace:jobs`
3. Check pending messages: `redis-cli XPENDING sastaspace:jobs redesign-workers`
4. Worker uses `Recreate` strategy (not `RollingUpdate`) — brief downtime during deploys is expected
