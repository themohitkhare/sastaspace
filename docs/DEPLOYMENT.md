# Deployment Knowledge Base

## Server

| Key | Value |
|-----|-------|
| IP | DHCP-assigned (currently `192.168.0.37`) |
| OS | Ubuntu 24.04 LTS |
| CPU | AMD Ryzen 9 7900X |
| GPU | AMD RX 7900 XTX (gfx1100, 20GB VRAM) |
| User | `mkhare` |
| Hostname | taxila |
| SSH | `ssh mkhare@taxila` or `ssh mkhare@<current-ip>` (key-based) |

## Secrets

macOS Keychain, account `sastaspace`. Never in git or `.env`.

```bash
security find-generic-password -a sastaspace -s <service-name> -w        # read
security add-generic-password -a sastaspace -s <service-name> -w "X" -U  # write
```

| Service name | Usage |
|---|---|
| `cloudflare-api-token` | DNS, tunnel |
| `claude-code-api-key` | Backend → claude-code-api |

---

## k8s Pod Architecture (`sastaspace` namespace)

| Pod | Image | Purpose |
|-----|-------|---------|
| `backend` | `sastaspace-backend` (`MODE=server`) | FastAPI API server :8080 |
| `worker` | `sastaspace-backend` (`MODE=worker`) | Redis Stream consumer — crawl→redesign→deploy. Strategy: `Recreate` |
| `browserless` | `ghcr.io/browserless/chromium` | Headless Chromium via CDP WebSocket :3000. Concurrency: 5, timeout: 60s |
| `mongodb` | `mongo:7` | Job persistence, site registry. PVC: 5Gi |
| `redis` | `redis:7-alpine` | Job queue (Streams), pub/sub (SSE), webhook dedup. PVC: 2Gi |

Backend + worker share same image (`backend/Dockerfile`). `entrypoint.sh` switches on `$MODE`.

## ConfigMap (`k8s/configmap.yaml`)

```yaml
CLAUDE_CODE_API_URL: "http://host.k8s.internal:8000/v1"  # via microk8s host-access addon
SASTASPACE_SITES_DIR: "/data/sites"
REDIS_URL: "redis://redis:6379"
MONGODB_URL: "mongodb://mongodb:27017"
MONGODB_DB: "sastaspace"
OLLAMA_URL: "http://host.k8s.internal:11434/v1"          # via microk8s host-access addon
BROWSERLESS_URL: "ws://browserless:3000"
```

Secrets in `sastaspace-env` Secret (Twenty keys, webhook secret, admin key).

## k8s Manifest Tree

```
k8s/
├── namespace.yaml, configmap.yaml, ingress.yaml
├── backend.yaml        (+ service + sites-pvc 10Gi)
├── worker.yaml
├── browserless.yaml    (+ service)
├── frontend.yaml       (+ service)
├── mongodb.yaml        (+ service + pvc 5Gi)
├── redis.yaml          (+ service + pvc 2Gi)
├── espocrm/            (namespace, app, mariadb, secret, ingress)
├── twenty/             (namespace, server, worker, postgres, redis, secrets, ingress)
└── monitoring/         (namespace, grafana, prometheus, loki, promtail, node-exporter,
                         kube-state-metrics, blackbox-exporter, redis-exporter,
                         dcgm-exporter, dashboards/, ingress)
```

---

## Internal Service Routing

```
worker ──► browserless:3000   (CDP WebSocket — Chromium crawling)
       ──► redis:6379         (consume jobs, publish status)
       ──► mongodb:27017      (job state, checkpoints)
       ──► host.k8s.internal:8000  (claude-code-api, via microk8s host-access)
       ──► host.k8s.internal:11434 (Ollama, via microk8s host-access)

backend ──► redis:6379        (enqueue jobs, pub/sub for SSE)
        ──► mongodb:27017     (job lookup, site registry, dedup)
```

## Traffic Architecture

```
Internet → Cloudflare Edge → cloudflared (systemd) → localhost:80 (nginx ingress)
  sastaspace.com / www    → frontend :3000
  api.sastaspace.com      → backend :8080
  crm.sastaspace.com      → espocrm :80 (espocrm ns) [migrating from twenty-server :3000]
  monitor.sastaspace.com  → grafana :3001 (monitoring ns)
```

Tunnel ID: `b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8`. DNS: all CNAMEs → `b3d36ee8-...cfargotunnel.com` (proxied).

---

## Job Processing Pipeline

```
POST /redesign → Redis Stream (sastaspace:jobs) → Worker consumer
  1. Enhanced Crawl (via Browserless CDP)
     - Homepage crawl → extract links → LLM picks 3 best → parallel crawl
     - Download + validate assets (magic bytes, Pillow, defusedxml, YARA)
     - LLM builds business profile
  2. AI Redesign
     - Premium: Agno multi-agent (analyst→strategist→generator→reviewer)
     - Free: Ollama single-shot (glm-4.7-flash)
  3. Deploy
     - Write HTML + assets to /data/sites/{subdomain}/
     - Register in MongoDB (URL hash dedup)
     - Sync to Twenty CRM (fire-and-forget)
```

Status via Redis Pub/Sub → SSE. Checkpoints in MongoDB. Dead job recovery via XAUTOCLAIM (>60s idle).

---

## Host systemd Services

| Service | Port | Purpose |
|---------|------|---------|
| `cloudflared` | — | Cloudflare tunnel |
| `claude-code-api` | 8000 | OpenAI-compatible Claude gateway. Endpoints: `/health`, `/docs`, `/v1/chat/completions` |
| `docker` | — | Container runtime (vLLM) |
| `fbcon-rotate` | — | Console screen rotation (`echo 3 > /sys/class/graphics/fbcon/rotate_all`) |

claude-code-api setup:
```bash
git clone https://github.com/codingworkflow/claude-code-api ~/claude-code-api
cd ~/claude-code-api && python3 -m venv .venv && .venv/bin/pip install -e .
# systemd: User=mkhare, Restart=always, RestartSec=5, Environment=HOME=/home/mkhare
# ExecStart: ~/claude-code-api/.venv/bin/uvicorn claude_code_api.main:app --host 10.0.1.1 --port 8000
```

---

## CI/CD (`.github/workflows/deploy.yml`)

Self-hosted runner on `taxila` (DHCP, see server table for current IP).

```
test → security → deploy (main branch only)
```

| Job | Steps |
|-----|-------|
| `test` | ruff lint+format, jscpd (dupes), semgrep (SAST), pytest -n auto, kubeconform |
| `security` | pip-audit (OSV), npm audit, Trivy fs scan (secrets + misconfigs) |
| `deploy` | build images → Trivy image scan per image → push registry → kubectl apply (app + monitoring + twenty if secrets exist) → rolling restart all → rollout wait 300s |

Deploy builds with `--build-arg NEXT_PUBLIC_BACKEND_URL=https://api.sastaspace.com`. Tags: `latest` + `${{ github.sha }}`. Suppressions in `.trivyignore`.

```bash
# Security scan commands (run by CI, useful for local debugging)
uv export --no-dev --no-editable --no-emit-project --format requirements-txt > /tmp/req.txt
uv tool run pip-audit --requirement /tmp/req.txt --vulnerability-service osv
npm audit --audit-level=high --omit=dev                              # in web/
trivy fs . --scanners secret,misconfig --exit-code 1 --severity HIGH,CRITICAL --ignorefile .trivyignore --skip-dirs node_modules,.git
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignorefile .trivyignore localhost:32000/sastaspace-backend:latest
```

Runner re-registration:
```bash
sudo systemctl status actions.runner.*
cd ~/actions-runner && ./config.sh --url https://github.com/<org>/<repo> --token <TOKEN>
sudo ./svc.sh install && sudo ./svc.sh start
```

---

## Makefile Commands

```bash
make install            # uv sync + playwright install chromium
make ci                 # lint + test
make dev                # FastAPI :8080 + Next.js :3000
make deploy             # rsync → build → push → k8s apply → restart
make deploy-status      # pods/svc/ingress
make deploy-logs        # tail backend + frontend
make deploy-down        # delete namespace
make deploy-monitoring  # apply monitoring manifests
make monitoring-status
make monitoring-logs    # tail grafana/prometheus/loki
make deploy-twenty      # deploy Twenty CRM stack
make twenty-status
make twenty-logs        # tail Twenty server logs
make twenty-setup       # first-time instructions
make espocrm-deploy    # deploy EspoCRM stack
make espocrm-status
make espocrm-logs      # tail EspoCRM app logs
make espocrm-restart   # rolling restart EspoCRM
make twenty-remove     # delete Twenty namespace (after EspoCRM verified)
```

Custom remote: `make deploy REMOTE_HOST=taxila REMOTE_USER=mkhare`

Image build (manual):
```bash
docker build -t localhost:32000/sastaspace-backend:latest -f backend/Dockerfile .
docker build -t localhost:32000/sastaspace-frontend:latest --build-arg NEXT_PUBLIC_BACKEND_URL=https://api.sastaspace.com -f web/Dockerfile web/
docker push localhost:32000/sastaspace-backend:latest && docker push localhost:32000/sastaspace-frontend:latest
```

## docker-compose (local dev)

```bash
docker compose up                         # redis, mongodb, browserless, backend, frontend
docker compose --profile test run tests   # E2E
```

Backend uses `host.docker.internal:8000` for claude-code-api. Browserless at `3100→3000`.

## First-Time Setup

### Monitoring (Grafana)
```bash
sudo microk8s kubectl create namespace monitoring
sudo microk8s kubectl create secret generic grafana-admin --namespace monitoring --from-literal=admin-password='<pw>'
make deploy-monitoring
```

### Twenty CRM
```bash
vi k8s/twenty/secrets.yaml   # fill template with real values
make deploy-twenty
make twenty-status            # verify pods
# Access: https://crm.sastaspace.com
```

### EspoCRM (Lead Management)

Replaces Twenty CRM. 2 pods (app + MariaDB) vs Twenty's 6 pods.

#### First-time setup
1. Generate secure passwords and update `k8s/espocrm/secret.yaml`
2. `make espocrm-deploy`
3. Access https://crm.sastaspace.com, login with admin credentials
4. Go to Administration → API Users → Create API User → copy API key
5. Set `ESPOCRM_URL` and `ESPOCRM_API_KEY` in sastaspace-env secret
6. Verify: `make espocrm-status`

#### After verifying EspoCRM works
- `make twenty-remove` to delete the Twenty namespace and free ~3GB RAM

---

## Health Checks

```bash
sudo systemctl status cloudflared
curl http://10.0.1.1:8000/health                                               # claude-code-api (bound to host-access bridge IP)
sudo microk8s kubectl get pods -A                                              # all namespaces
sudo microk8s kubectl get pods,svc,ingress -n sastaspace
sudo microk8s kubectl logs -n sastaspace deployment/worker --tail=50           # worker
sudo microk8s kubectl logs -n sastaspace deployment/browserless --tail=20      # browserless
sudo microk8s kubectl exec -n sastaspace deployment/redis -- redis-cli XLEN sastaspace:jobs
make twenty-status
make monitoring-status
rocm-smi                                                                       # GPU
sudo docker logs vllm-coder --tail 20                                          # vLLM
```

## Useful Commands

```bash
make deploy-logs                                                               # tail app logs
ssh mkhare@taxila "sudo microk8s kubectl logs -n sastaspace deploy/worker --tail=100 -f"
k9s                                                                            # interactive k8s UI
btop                                                                           # GPU + system monitor
sudo systemctl restart claude-code-api
sudo microk8s kubectl rollout restart deployment/worker -n sastaspace
sudo microk8s kubectl exec -n sastaspace deploy/redis -- redis-cli XLEN sastaspace:jobs
sudo microk8s kubectl exec -n sastaspace deploy/mongodb -- mongosh sastaspace --eval "db.jobs.countDocuments()"
sudo ufw status verbose
df -h && sudo lvs
make ci
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `'str' object has no attribute 'text_content'` | Wrong args to `build_business_profile` | Fixed `a8b726bf` — redeploy |
| `Redis connection lost, reconnecting` | Redis pod restarting during deploy | Transient, auto-reconnects 2s |
| `Could not reach that website` | Browserless can't load URL | Check site/browserless OOM |
| `Bot protection detected` | Target site <500 chars text | Site blocking crawlers |
| `Timeout after 30s` | Slow internal page | Normal, other pages still crawled |

### Worker not processing

```bash
kubectl get pods -n sastaspace -l app=worker           # running?
kubectl exec -n sastaspace deploy/redis -- redis-cli XLEN sastaspace:jobs     # queued?
kubectl exec -n sastaspace deploy/redis -- redis-cli XPENDING sastaspace:jobs redesign-workers  # stuck?
kubectl rollout restart deployment/worker -n sastaspace  # restart
```

---

## Server Setup (one-time, fresh Ubuntu 24.04)

### 1. SSH
```bash
ssh-keygen -R taxila && ssh mkhare@taxila   # accept new key (use hostname or current IP)
ssh-copy-id mkhare@taxila                    # passwordless
```

### 2. Shell
```bash
sudo apt install -y zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" '' --unattended
sudo chsh -s $(which zsh) mkhare
```

### 3. AMD GPU + ROCm 6.3
```bash
wget https://repo.radeon.com/amdgpu-install/6.3.3/ubuntu/noble/amdgpu-install_6.3.60303-1_all.deb
sudo apt install -y ./amdgpu-install_6.3.60303-1_all.deb
sudo amdgpu-install --usecase=rocm --no-32
sudo usermod -aG video,render mkhare && sudo reboot
# Verify: rocm-smi && rocminfo | grep gfx  (expect gfx1100)
```

### 4. btop (apt 1.3.0 segfaults — build from source)
```bash
sudo apt install -y g++-14 make git
git clone --depth=1 --branch v1.4.6 https://github.com/aristocratos/btop /tmp/btop-src
cd /tmp/btop-src && make GPU_SUPPORT=true RSMI_STATIC=false ADDFLAGS='-I/opt/rocm/include -L/opt/rocm/lib' CXX=g++-14 -j$(nproc)
sudo cp bin/btop /usr/local/bin/btop   # press 'g' for GPU panel
```

### 5. LVM disk expansion (default install uses 100GB, VG has ~1.7TB free)
```bash
sudo lvextend -L +200G /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```

### 6. Screen rotation (console rotated 180°)
```bash
# systemd oneshot: ExecStart=/bin/sh -c "echo 3 > /sys/class/graphics/fbcon/rotate_all"
sudo systemctl enable --now fbcon-rotate.service
```

### 7. Node.js 22 + Claude Code CLI
```bash
sudo bash -c "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -"
sudo apt install -y nodejs
sudo npm install -g @anthropic-ai/claude-code
```

### 8. Docker + vLLM
```bash
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sudo sh /tmp/get-docker.sh
sudo usermod -aG docker mkhare
sudo docker run -d --name vllm-coder --device=/dev/kfd --device=/dev/dri \
  --group-add video --group-add render --ipc=host -p 127.0.0.1:8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface rocm/vllm:latest \
  vllm serve Qwen/Qwen2.5-Coder-14B-Instruct-AWQ --gpu-memory-utilization 0.85 --max-model-len 32768 --host 0.0.0.0 --port 8000
# Bound to 127.0.0.1:8001 — not exposed publicly
```

### 9. microk8s
```bash
sudo usermod -a -G microk8s mkhare && sudo chown -R mkhare ~/.kube && newgrp microk8s
sudo microk8s enable ingress hostpath-storage cert-manager registry host-access
```

### 10. k9s
```bash
curl -sL https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz -o /tmp/k9s.tar.gz
sudo tar xz -C /usr/local/bin k9s -f /tmp/k9s.tar.gz
mkdir -p ~/.kube && sudo microk8s config > ~/.kube/config && chmod 600 ~/.kube/config
```

### 11. Cloudflare tunnel
```bash
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-main.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared
sudo cloudflared service install <TUNNEL_TOKEN>
# Ingress: sastaspace.com, www, api, crm, monitor → http://localhost:80; catch-all → 404
```

### 12. claude-code-api — see "Host systemd Services" section above

### 13. UFW firewall
```bash
sudo ufw --force enable && sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment SSH && sudo ufw allow 80/tcp comment HTTP && sudo ufw allow 443/tcp comment HTTPS
```
