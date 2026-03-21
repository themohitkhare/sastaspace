# Monitoring Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a Grafana observability stack (Prometheus, Loki, Grafana) to microk8s for remote monitoring at `monitor.sastaspace.com`.

**Architecture:** All monitoring components run in a dedicated `monitoring` namespace on the existing microk8s cluster. Prometheus scrapes metrics (auto-discovering pods via annotations), Loki collects logs (via Promtail DaemonSet), Blackbox Exporter probes public domains, and Grafana provides the dashboard UI with built-in auth. Traffic reaches Grafana via the existing Cloudflare tunnel → nginx ingress path.

**Tech Stack:** Kubernetes manifests (YAML), Prometheus, Grafana, Loki, Promtail, Blackbox Exporter, Node Exporter, nginx ingress, Make

**Spec:** `docs/superpowers/specs/2026-03-21-monitoring-stack-design.md`

---

## File Structure

```
k8s/monitoring/
├── namespace.yaml          # CREATE — monitoring namespace
├── prometheus.yaml         # CREATE — Deployment + PVC + ConfigMap + RBAC + Service
├── node-exporter.yaml      # CREATE — DaemonSet + Service
├── blackbox-exporter.yaml  # CREATE — Deployment + ConfigMap + Service
├── loki.yaml               # CREATE — Deployment + PVC + ConfigMap + Service
├── promtail.yaml           # CREATE — DaemonSet + ConfigMap + RBAC
├── grafana.yaml            # CREATE — Deployment + PVC + ConfigMaps + Service
└── ingress.yaml            # CREATE — monitor.sastaspace.com → grafana:3001

k8s/backend.yaml            # MODIFY — add prometheus scrape annotations to pod template
k8s/frontend.yaml           # MODIFY — add prometheus scrape annotations to pod template
Makefile                     # MODIFY — add monitoring deployment targets
```

---

### Task 1: Namespace + Prometheus RBAC + ConfigMap

**Files:**
- Create: `k8s/monitoring/namespace.yaml`
- Create: `k8s/monitoring/prometheus.yaml`

- [ ] **Step 1: Create the monitoring namespace manifest**

Create `k8s/monitoring/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
```

- [ ] **Step 2: Create Prometheus manifest with RBAC, ConfigMap, PVC, Deployment, and Service**

Create `k8s/monitoring/prometheus.yaml`. This is one file with multiple documents (separated by `---`).

RBAC resources (ServiceAccount, ClusterRole, ClusterRoleBinding) allow Prometheus to discover pods/services across all namespaces.

The ConfigMap contains the full `prometheus.yml` with these scrape jobs:
- `kubernetes-pods` — auto-discovers pods with `prometheus.io/scrape: "true"` annotation
- `kubernetes-services` — auto-discovers services with scrape annotations
- `node-exporter` — static target `node-exporter.monitoring.svc:9100`
- `blackbox-http` — probes `https://sastaspace.com`, `https://api.sastaspace.com`, `https://www.sastaspace.com` via blackbox-exporter

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups: [""]
  resources: [nodes, nodes/proxy, services, endpoints, pods]
  verbs: [get, list, watch]
- apiGroups: [extensions, networking.k8s.io]
  resources: [ingresses]
  verbs: [get, list, watch]
- nonResourceURLs: [/metrics]
  verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: "true"
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            target_label: __address__
            regex: (.+)
            replacement: ${1}
            source_labels: [__meta_kubernetes_pod_ip, __meta_kubernetes_pod_annotation_prometheus_io_port]
            separator: ":"
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_pod_label_app]
            target_label: app

      - job_name: node-exporter
        static_configs:
          - targets: ["node-exporter.monitoring.svc:9100"]

      - job_name: blackbox-http
        metrics_path: /probe
        params:
          module: [http_2xx]
        static_configs:
          - targets:
              - https://sastaspace.com
              - https://api.sastaspace.com
              - https://www.sastaspace.com
        relabel_configs:
          - source_labels: [__address__]
            target_label: __param_target
          - source_labels: [__param_target]
            target_label: instance
          - target_label: __address__
            replacement: blackbox-exporter.monitoring.svc:9115
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: prometheus-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: prom/prometheus:v3.3.0
        args:
          - "--config.file=/etc/prometheus/prometheus.yml"
          - "--storage.tsdb.path=/prometheus"
          - "--storage.tsdb.retention.time=15d"
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: data
          mountPath: /prometheus
        resources:
          requests:
            memory: "512Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /-/ready
            port: 9090
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: data
        persistentVolumeClaim:
          claimName: prometheus-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: monitoring
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
```

- [ ] **Step 3: Commit**

```bash
git add k8s/monitoring/namespace.yaml k8s/monitoring/prometheus.yaml
git commit -m "feat(monitoring): add namespace and prometheus with RBAC and auto-discovery"
```

---

### Task 2: Node Exporter

**Files:**
- Create: `k8s/monitoring/node-exporter.yaml`

- [ ] **Step 1: Create Node Exporter DaemonSet manifest**

Create `k8s/monitoring/node-exporter.yaml`. Uses `hostNetwork`, `hostPID`, and mounts `/proc` and `/sys` read-only to expose real host metrics:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.9.0
        args:
          - "--path.procfs=/host/proc"
          - "--path.sysfs=/host/sys"
          - "--path.rootfs=/host/root"
          - "--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)"
        ports:
        - containerPort: 9100
          hostPort: 9100
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
          mountPropagation: HostToContainer
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
---
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    app: node-exporter
  ports:
  - port: 9100
    targetPort: 9100
```

- [ ] **Step 2: Commit**

```bash
git add k8s/monitoring/node-exporter.yaml
git commit -m "feat(monitoring): add node-exporter DaemonSet with host metrics"
```

---

### Task 3: Blackbox Exporter

**Files:**
- Create: `k8s/monitoring/blackbox-exporter.yaml`

- [ ] **Step 1: Create Blackbox Exporter manifest**

Create `k8s/monitoring/blackbox-exporter.yaml`. The ConfigMap defines the `http_2xx` probe module. Prometheus drives the actual probing (targets are in the Prometheus ConfigMap):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: blackbox-config
  namespace: monitoring
data:
  blackbox.yml: |
    modules:
      http_2xx:
        prober: http
        timeout: 10s
        http:
          valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
          valid_status_codes: [200, 301, 302]
          method: GET
          follow_redirects: true
          preferred_ip_protocol: ip4
          tls_config:
            insecure_skip_verify: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blackbox-exporter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blackbox-exporter
  template:
    metadata:
      labels:
        app: blackbox-exporter
    spec:
      containers:
      - name: blackbox-exporter
        image: prom/blackbox-exporter:v0.26.0
        args:
          - "--config.file=/etc/blackbox/blackbox.yml"
        ports:
        - containerPort: 9115
        volumeMounts:
        - name: config
          mountPath: /etc/blackbox
        resources:
          requests:
            memory: "32Mi"
            cpu: "25m"
          limits:
            memory: "64Mi"
            cpu: "50m"
        readinessProbe:
          httpGet:
            path: /health
            port: 9115
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: blackbox-config
---
apiVersion: v1
kind: Service
metadata:
  name: blackbox-exporter
  namespace: monitoring
spec:
  selector:
    app: blackbox-exporter
  ports:
  - port: 9115
    targetPort: 9115
```

- [ ] **Step 2: Commit**

```bash
git add k8s/monitoring/blackbox-exporter.yaml
git commit -m "feat(monitoring): add blackbox-exporter for domain uptime probes"
```

---

### Task 4: Loki

**Files:**
- Create: `k8s/monitoring/loki.yaml`

- [ ] **Step 1: Create Loki manifest**

Create `k8s/monitoring/loki.yaml`. Runs in single-binary mode with filesystem storage. The ConfigMap contains the Loki config with schema, storage, and retention settings:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: monitoring
data:
  loki.yaml: |
    auth_enabled: false

    server:
      http_listen_port: 3100

    common:
      path_prefix: /loki
      storage:
        filesystem:
          chunks_directory: /loki/chunks
          rules_directory: /loki/rules
      replication_factor: 1
      ring:
        kvstore:
          store: inmemory

    schema_config:
      configs:
        - from: "2024-01-01"
          store: tsdb
          object_store: filesystem
          schema: v13
          index:
            prefix: index_
            period: 24h

    limits_config:
      retention_period: 168h
      max_query_series: 500

    compactor:
      working_directory: /loki/compactor
      retention_enabled: true
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: loki-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
    spec:
      containers:
      - name: loki
        image: grafana/loki:3.5.0
        args:
          - "-config.file=/etc/loki/loki.yaml"
        ports:
        - containerPort: 3100
        volumeMounts:
        - name: config
          mountPath: /etc/loki
        - name: data
          mountPath: /loki
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "300m"
        readinessProbe:
          httpGet:
            path: /ready
            port: 3100
          initialDelaySeconds: 15
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: loki-config
      - name: data
        persistentVolumeClaim:
          claimName: loki-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: loki
  namespace: monitoring
spec:
  selector:
    app: loki
  ports:
  - port: 3100
    targetPort: 3100
```

- [ ] **Step 2: Commit**

```bash
git add k8s/monitoring/loki.yaml
git commit -m "feat(monitoring): add Loki for log aggregation"
```

---

### Task 5: Promtail

**Files:**
- Create: `k8s/monitoring/promtail.yaml`

- [ ] **Step 1: Create Promtail manifest**

Create `k8s/monitoring/promtail.yaml`. DaemonSet with RBAC to read pod metadata. Mounts `/var/log/pods` to tail all container logs. Sends to Loki at `http://loki.monitoring.svc:3100`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: promtail
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: promtail
rules:
- apiGroups: [""]
  resources: [nodes, nodes/proxy, services, endpoints, pods]
  verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: promtail
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: promtail
subjects:
- kind: ServiceAccount
  name: promtail
  namespace: monitoring
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
  namespace: monitoring
data:
  promtail.yaml: |
    server:
      http_listen_port: 9080

    positions:
      filename: /tmp/positions.yaml

    clients:
      - url: http://loki.monitoring.svc:3100/loki/api/v1/push

    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
          - role: pod
        pipeline_stages:
          - cri: {}
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_node_name]
            target_label: node
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_pod_container_name]
            target_label: container
          - source_labels: [__meta_kubernetes_pod_label_app]
            target_label: app
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: promtail
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: promtail
  template:
    metadata:
      labels:
        app: promtail
    spec:
      serviceAccountName: promtail
      containers:
      - name: promtail
        image: grafana/promtail:3.5.0
        args:
          - "-config.file=/etc/promtail/promtail.yaml"
        volumeMounts:
        - name: config
          mountPath: /etc/promtail
        - name: pods-logs
          mountPath: /var/log/pods
          readOnly: true
        - name: containers-logs
          mountPath: /var/lib/docker/containers
          readOnly: true
        resources:
          requests:
            memory: "128Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "100m"
      volumes:
      - name: config
        configMap:
          name: promtail-config
      - name: pods-logs
        hostPath:
          path: /var/log/pods
      - name: containers-logs
        hostPath:
          path: /var/lib/docker/containers
```

- [ ] **Step 2: Commit**

```bash
git add k8s/monitoring/promtail.yaml
git commit -m "feat(monitoring): add Promtail DaemonSet for pod log collection"
```

---

### Task 6: Grafana

**Files:**
- Create: `k8s/monitoring/grafana.yaml`

- [ ] **Step 1: Create Grafana manifest**

Create `k8s/monitoring/grafana.yaml`. Includes PVC for persistence, ConfigMaps for auto-provisioned datasources (Prometheus + Loki), and the Deployment. Admin password comes from a k8s Secret created out-of-band on the server:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus.monitoring.svc:9090
        isDefault: true
        editable: false
      - name: Loki
        type: loki
        access: proxy
        url: http://loki.monitoring.svc:3100
        editable: false
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-providers
  namespace: monitoring
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
      - name: default
        orgId: 1
        folder: ""
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards
          foldersFromFilesStructure: false
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:11.6.0
        ports:
        - containerPort: 3001
        env:
        - name: GF_SERVER_HTTP_PORT
          value: "3001"
        - name: GF_SECURITY_ADMIN_USER
          value: "admin"
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-admin
              key: admin-password
        - name: GF_USERS_ALLOW_SIGN_UP
          value: "false"
        volumeMounts:
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
        - name: dashboard-providers
          mountPath: /etc/grafana/provisioning/dashboards
        - name: data
          mountPath: /var/lib/grafana
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "300m"
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3001
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: datasources
        configMap:
          name: grafana-datasources
      - name: dashboard-providers
        configMap:
          name: grafana-dashboard-providers
      - name: data
        persistentVolumeClaim:
          claimName: grafana-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: monitoring
spec:
  selector:
    app: grafana
  ports:
  - port: 3001
    targetPort: 3001
```

- [ ] **Step 2: Commit**

```bash
git add k8s/monitoring/grafana.yaml
git commit -m "feat(monitoring): add Grafana with provisioned datasources"
```

---

### Task 7: Monitoring Ingress

**Files:**
- Create: `k8s/monitoring/ingress.yaml`

- [ ] **Step 1: Create monitoring ingress manifest**

Create `k8s/monitoring/ingress.yaml`. Routes `monitor.sastaspace.com` to Grafana. Follows same pattern as existing `k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: monitoring
  namespace: monitoring
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
spec:
  ingressClassName: nginx
  rules:
  - host: monitor.sastaspace.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3001
```

- [ ] **Step 2: Commit**

```bash
git add k8s/monitoring/ingress.yaml
git commit -m "feat(monitoring): add ingress for monitor.sastaspace.com"
```

---

### Task 8: Update Existing Manifests + Makefile

**Files:**
- Modify: `k8s/backend.yaml:11-13` — add prometheus annotations to pod template
- Modify: `k8s/frontend.yaml:11-13` — add prometheus annotations to pod template
- Modify: `Makefile:10-11,54+` — add monitoring targets

- [ ] **Step 1: Add Prometheus scrape annotations to backend pod template**

In `k8s/backend.yaml`, add annotations under `spec.template.metadata` (the pod template, NOT the Deployment metadata). The existing file has:

```yaml
  template:
    metadata:
      labels:
        app: backend
```

Change to:

```yaml
  template:
    metadata:
      labels:
        app: backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
```

- [ ] **Step 2: Add Prometheus scrape annotations to frontend pod template**

In `k8s/frontend.yaml`, add annotations under `spec.template.metadata`. The existing file has:

```yaml
  template:
    metadata:
      labels:
        app: frontend
```

Change to:

```yaml
  template:
    metadata:
      labels:
        app: frontend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
```

- [ ] **Step 3: Add monitoring targets to Makefile**

In `Makefile`, add to the `.PHONY` line and append monitoring targets after the existing deployment section.

Add `deploy-monitoring monitoring-status monitoring-logs` to the `.PHONY` line.

Append after the `deploy-down` target:

```makefile
# ── Monitoring (Grafana + Prometheus + Loki) ──────────────────────────────────

deploy-monitoring:
	@echo "→ Syncing code to $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)..."
	@rsync -az --delete $(RSYNC_EXCLUDE) . $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)
	@echo "→ Applying monitoring manifests..."
	@$(SSH) "sudo microk8s kubectl apply -f $(REMOTE_DIR)/k8s/monitoring/"
	@echo "✓ Monitoring deployed. Dashboard: https://monitor.sastaspace.com"

monitoring-status:
	@$(SSH) "sudo microk8s kubectl get pods,svc,ingress -n monitoring"

monitoring-logs:
	@$(SSH) "sudo microk8s kubectl logs -f -n monitoring -l 'app in (grafana,prometheus,loki)' --max-log-requests=6"
```

- [ ] **Step 4: Commit**

```bash
git add k8s/backend.yaml k8s/frontend.yaml Makefile
git commit -m "feat(monitoring): add scrape annotations to app pods and Makefile targets"
```

---

### Task 9: Cloudflare Tunnel Route + Documentation

**Files:**
- Modify: `docs/DEPLOYMENT.md` — add monitor.sastaspace.com to tunnel config and ingress rules

- [ ] **Step 1: Update DEPLOYMENT.md**

In `docs/DEPLOYMENT.md`, update the Cloudflare tunnel ingress rules (section 11) to include `monitor.sastaspace.com`. Find the existing ingress JSON block and add the monitoring route.

In the `curl -X PUT` ingress config block, add this line before the catch-all `http_status:404` rule:

```json
{"hostname": "monitor.sastaspace.com", "service": "http://localhost:80"},
```

Also update the DNS records section to include `monitor.sastaspace.com` (already covered by wildcard, but document it explicitly).

In section 14 (Application Deployment), add a note about monitoring:

```markdown
### Monitoring stack

Located in `k8s/monitoring/` directory — deployed separately from the app:

```bash
make deploy-monitoring    # apply all monitoring manifests
make monitoring-status    # check pod/svc/ingress status
make monitoring-logs      # tail monitoring pod logs
```

First-time setup requires creating the Grafana admin secret:

```bash
sudo microk8s kubectl create namespace monitoring
sudo microk8s kubectl create secret generic grafana-admin \
  --namespace monitoring \
  --from-literal=admin-password='<your-password>'
make deploy-monitoring
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/DEPLOYMENT.md
git commit -m "docs: add monitoring stack deployment instructions"
```

---

### Task 10: Verify Manifests Locally

- [ ] **Step 1: Verify all monitoring manifests exist and are valid YAML**

Run:

```bash
ls -la k8s/monitoring/
```

Expected: 8 files (namespace.yaml, prometheus.yaml, node-exporter.yaml, blackbox-exporter.yaml, loki.yaml, promtail.yaml, grafana.yaml, ingress.yaml)

- [ ] **Step 2: Count total lines to verify completeness**

Run:

```bash
wc -l k8s/monitoring/*.yaml
```

Expected: Each file should have substantial content (not empty stubs).

- [ ] **Step 3: Dry-run validation (if kubectl available locally)**

If `kubectl` is available locally, validate manifests:

```bash
kubectl apply --dry-run=client -f k8s/monitoring/ 2>&1 || echo "No local kubectl — skip dry-run, will validate on deploy"
```

- [ ] **Step 4: Verify scrape annotations in app manifests**

Run:

```bash
grep -A2 "prometheus.io" k8s/backend.yaml k8s/frontend.yaml
```

Expected: Both files should show `prometheus.io/scrape: "true"` and `prometheus.io/port` annotations.

- [ ] **Step 5: Verify Makefile targets**

Run:

```bash
grep -E "deploy-monitoring|monitoring-status|monitoring-logs" Makefile
```

Expected: All 3 targets present.

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
# Only if changes were made during verification
git add -A && git commit -m "fix(monitoring): address verification issues"
```

---

## Post-Implementation: Remote Deployment

After all tasks are complete, deploy to the server:

1. **Create the Grafana admin secret on the server** (one-time, manual):
   ```bash
   ssh mkhare@192.168.0.38
   sudo microk8s kubectl create namespace monitoring
   sudo microk8s kubectl create secret generic grafana-admin \
     --namespace monitoring \
     --from-literal=admin-password='<choose-a-password>'
   ```

2. **Add `monitor.sastaspace.com` route to Cloudflare tunnel** (one-time, manual):
   - Cloudflare dashboard → Zero Trust → Networks → Tunnels → sastaspace-prod → Public Hostname
   - Add: `monitor.sastaspace.com` → `http://localhost:80`

3. **Deploy monitoring stack**:
   ```bash
   make deploy-monitoring
   make monitoring-status
   ```

4. **Deploy app with new scrape annotations**:
   ```bash
   make deploy
   ```

5. **Verify**:
   - Visit `https://monitor.sastaspace.com`
   - Login with admin / your-chosen-password
   - Check: Prometheus datasource connected, Loki datasource connected
   - Check: Node metrics visible, pod logs searchable
   - Check: Uptime probes showing for all 3 domains
