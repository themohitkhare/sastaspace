# Deployment Knowledge Base

> Complete setup guide for the sastaspace production server. Covers everything from OS install to live deployment.

## Server Specs

| | |
|---|---|
| **IP** | 192.168.0.38 |
| **OS** | Ubuntu 24.04 LTS |
| **CPU** | AMD Ryzen 9 7900X |
| **GPU** | AMD RX 7900 XTX (gfx1100, 20GB VRAM) |
| **User** | `mkhare` |
| **Hostname** | taxila |

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
| **Tunnel ID** | `REDACTED_TUNNEL_ID` |
| **Account ID** | `REDACTED_CF_ACCOUNT_ID` |
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
CF_TOKEN="<your-api-token>"
ACCOUNT_ID="REDACTED_CF_ACCOUNT_ID"

# Create tunnel
curl -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"sastaspace-prod","config_src":"cloudflare"}'

# Configure ingress (routes to microk8s nginx)
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel/<TUNNEL_ID>/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "ingress": [
        {"hostname": "sastaspace.com",     "service": "http://localhost:80"},
        {"hostname": "www.sastaspace.com", "service": "http://localhost:80"},
        {"hostname": "api.sastaspace.com", "service": "http://localhost:80"},
        {"service": "http_status:404"}
      ]
    }
  }'
```

### DNS records

All CNAMEs point to `<TUNNEL_ID>.cfargotunnel.com` (proxied):
- `sastaspace.com`
- `www.sastaspace.com`
- `*.sastaspace.com`
- `api.sastaspace.com`

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

### k8s manifests

Located in `k8s/` directory:

```
k8s/
├── namespace.yaml     # sastaspace namespace
├── backend.yaml       # FastAPI deployment + service + PVC
├── frontend.yaml      # Next.js deployment + service
└── ingress.yaml       # nginx ingress rules for all hostnames
```

### Local image registry

Images are built on the remote machine and pushed to the microk8s local registry:

```bash
docker build -t localhost:32000/sastaspace-backend:latest -f backend/Dockerfile .
docker build -t localhost:32000/sastaspace-frontend:latest -f web/Dockerfile web/
docker push localhost:32000/sastaspace-backend:latest
docker push localhost:32000/sastaspace-frontend:latest
```

### Deploy via Makefile

```bash
make deploy        # rsync + build images + apply manifests + rolling restart
make deploy-build  # same, forces image rebuild
make deploy-status # show pod/svc/ingress status
make deploy-logs   # tail logs from all pods
make deploy-down   # delete sastaspace namespace
```

Configure remote target if different from default:

```bash
make deploy REMOTE_HOST=192.168.0.38 REMOTE_USER=mkhare
```

---

## 15. Traffic Architecture

```
Browser / API client
        │
        ▼
  Cloudflare Edge
  (DDoS protection, TLS termination, CDN)
        │
        ▼ QUIC / HTTP2
  cloudflared (systemd, /etc/systemd/system/cloudflared.service)
  Tunnel: REDACTED_TUNNEL_ID
        │
        ▼ HTTP
  localhost:80
  microk8s nginx ingress controller
        │
        ├─── sastaspace.com / www ──────▶ frontend service :3000
        │                                 (Next.js pod)
        │
        └─── api.sastaspace.com ────────▶ backend service :8080
                                          (FastAPI pod)
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

## 16. Service Health Checks

```bash
# Cloudflare tunnel
sudo systemctl status cloudflared

# claude-code-api
curl http://localhost:8000/health

# microk8s cluster
sudo microk8s kubectl get pods -A

# k8s app pods
sudo microk8s kubectl get pods,svc,ingress -n sastaspace

# GPU status
rocm-smi

# vLLM (if running)
sudo docker logs vllm-coder --tail 20
```

---

## 17. Useful Commands

```bash
# Tail all app logs
make deploy-logs

# Interactive k8s UI
k9s

# GPU + system monitor
btop

# Restart a service
sudo systemctl restart claude-code-api

# Check firewall
sudo ufw status verbose

# Disk usage
df -h && sudo lvs
```
