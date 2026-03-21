# Monitoring Stack Design

> Full observability for sastaspace: uptime monitoring, infrastructure metrics, and pod logs — accessible remotely at `monitor.sastaspace.com` behind Grafana's built-in authentication.

## Problem

No way to monitor the production server remotely without SSH access. Need visibility into:
- Domain uptime (sastaspace.com, api.sastaspace.com, www.sastaspace.com)
- Infrastructure health (CPU, memory, disk, network)
- Pod status and resource usage
- Application logs from all pods
- Must be extensible — new services auto-discovered without config changes

## Solution

Grafana observability stack deployed to microk8s in a dedicated `monitoring` namespace.

## Architecture

```
Browser → monitor.sastaspace.com
    │
    ▼
Cloudflare Tunnel → localhost:80
    │
    ▼
nginx ingress (monitor.sastaspace.com)
    │
    ▼
Grafana (:3001) ← built-in login
    │
    ├── Prometheus (:9090)
    │     ├── scrapes k8s pod metrics (auto-discovery via annotations)
    │     ├── scrapes node-exporter (CPU/mem/disk of host)
    │     └── scrapes blackbox-exporter (uptime probes for domains)
    │
    └── Loki (:3100)
          └── Promtail (DaemonSet, tails all pod logs automatically)
```

## Components

### Prometheus

- Deployment with 5Gi PVC for metric storage (15-day retention)
- ConfigMap with scrape configs:
  - Kubernetes pod auto-discovery (annotations-based)
  - Kubernetes service auto-discovery
  - Node exporter target
  - Blackbox exporter probe targets
- RBAC: ServiceAccount + ClusterRole + ClusterRoleBinding to discover pods across all namespaces
- Service on port 9090

### Node Exporter

- DaemonSet — runs on every node
- Requires host access: `hostNetwork: true`, `hostPID: true`
- Mounts `/proc` and `/sys` as read-only from host (needed for real host metrics, not container metrics)
- Exposes host-level metrics: CPU, memory, disk, network
- Service on port 9100
- Prometheus auto-scrapes via service discovery

### Blackbox Exporter

- Deployment with ConfigMap defining HTTP probe module
- Probe targets configured in Prometheus scrape config:
  - `https://sastaspace.com`
  - `https://api.sastaspace.com`
  - `https://www.sastaspace.com`
- Measures: response time, HTTP status, SSL certificate expiry
- Adding new domains: add a target line in the Prometheus ConfigMap
- Service on port 9115

### Loki

- Deployment in single-binary mode (appropriate for single-node cluster)
- 10Gi PVC for log storage
- ConfigMap for Loki config (schema, storage, retention)
- Service on port 3100

### Promtail

- DaemonSet — runs on every node, auto-tails all pod logs
- ConfigMap for Promtail config (Loki push endpoint, label extraction)
- RBAC: ServiceAccount + ClusterRole to read pod metadata for labeling
- Mounts `/var/log/pods` from host to read container logs
- Labels: namespace, pod, container — all searchable in Grafana
- Zero per-service configuration needed — new pods auto-collected

### Grafana

- Deployment with 1Gi PVC for dashboard/settings persistence
- Port 3001 (avoids conflict with frontend's 3000)
- Admin password via k8s Secret (set during initial deployment)
- ConfigMap for provisioned datasources:
  - Prometheus (metrics) — pre-configured, no manual setup
  - Loki (logs) — pre-configured, no manual setup
- ConfigMap for provisioned dashboards:
  - Node Exporter Full (host metrics)
  - Kubernetes Pods (pod CPU/memory/restarts)
  - Blackbox Exporter (uptime, response times, SSL expiry)
  - Loki Log Explorer (search/filter logs)
- Service on port 3001

### Ingress

- Ingress resource in `monitoring` namespace
- Host: `monitor.sastaspace.com` → grafana service port 3001
- IngressClass: nginx (same as existing app ingress)

## File Structure

```
k8s/monitoring/
├── namespace.yaml          # monitoring namespace
├── prometheus.yaml         # Deployment + PVC + ConfigMap + RBAC + Service
├── node-exporter.yaml      # DaemonSet + Service
├── blackbox-exporter.yaml  # Deployment + ConfigMap + Service
├── loki.yaml               # Deployment + PVC + ConfigMap + Service
├── promtail.yaml           # DaemonSet + ConfigMap + RBAC
├── grafana.yaml            # Deployment + PVC + ConfigMaps + Secret + Service
└── ingress.yaml            # monitor.sastaspace.com → grafana:3001
```

## Changes to Existing Files

### `k8s/backend.yaml`

Add Prometheus scrape annotations to the **pod template** (not Deployment-level metadata):

```yaml
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
```

### `k8s/frontend.yaml`

Add Prometheus scrape annotations to the **pod template** (not Deployment-level metadata):

```yaml
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
```

**Note:** Prometheus pod-based service discovery reads annotations from pod metadata, not Deployment metadata. Placing them on the Deployment would silently fail.

### `Makefile`

Add monitoring deployment targets. **Note:** `kubectl apply -f <dir>` is non-recursive, so `k8s-apply` will NOT deploy monitoring resources. Monitoring is deployed separately via `deploy-monitoring`:

```makefile
deploy-monitoring:
    @$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/monitoring/"

monitoring-status:
    @$(SSH) "sudo microk8s kubectl get pods,svc,ingress -n monitoring"

monitoring-logs:
    @$(SSH) "sudo microk8s kubectl logs -f -n monitoring -l 'app in (grafana,prometheus,loki)' --max-log-requests=6"
```

### Cloudflare Tunnel

Add `monitor.sastaspace.com` route to the tunnel ingress config. This is managed via the Cloudflare dashboard (Zero Trust > Networks > Tunnels > sastaspace-prod > Public Hostname) or via API:

```bash
# Add to existing tunnel ingress rules via Cloudflare API
# (see docs/DEPLOYMENT.md section 11 for full API example)
{"hostname": "monitor.sastaspace.com", "service": "http://localhost:80"}
```

No DNS changes needed — existing wildcard CNAME `*.sastaspace.com` covers it.

## Adding Future Services

When adding a new service to the cluster:

1. **Metrics**: Add annotations to the Deployment pod template:
   ```yaml
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "<metrics-port>"
   ```
2. **Logs**: Nothing — Promtail auto-collects all pod logs
3. **Uptime**: Add URL to Prometheus blackbox targets in `prometheus.yaml` ConfigMap

## Authentication

- Grafana built-in login (admin user + password from k8s Secret)
- No ingress-level basic auth (KISS — single login layer)
- Grafana supports adding additional users via its admin panel if needed later
- Admin secret created out-of-band on the server before first deploy:
  ```bash
  sudo microk8s kubectl create secret generic grafana-admin \
    --namespace monitoring \
    --from-literal=admin-password='<your-password>'
  ```

## Resource Budget

Values shown as request / limit. Limits set higher than requests to absorb spikes without OOM kills:

| Component         | Memory (req/limit) | CPU (req/limit) |
|-------------------|---------------------|-----------------|
| Prometheus        | 512Mi / 1Gi         | 200m / 500m     |
| Grafana           | 256Mi / 512Mi       | 100m / 300m     |
| Loki              | 256Mi / 512Mi       | 100m / 300m     |
| Promtail          | 128Mi / 256Mi       | 50m / 100m      |
| Node Exporter     | 64Mi / 128Mi        | 50m / 100m      |
| Blackbox Exporter | 32Mi / 64Mi         | 25m / 50m       |
| **Total requests**| **~1.25Gi**         | **525m**        |
| **Total limits**  | **~2.5Gi**          | **1350m**       |

## First Login Flow

1. Deploy with `make deploy-monitoring`
2. Visit `monitor.sastaspace.com`
3. Login with admin / (password from k8s secret)
4. Dashboards pre-loaded — immediately see node health, pod status, uptime, and logs

## Out of Scope

- Alerting via email/Slack (can be added later in Grafana)
- Distributed tracing (not needed at current scale)
- Multi-node cluster metrics (single node setup)
