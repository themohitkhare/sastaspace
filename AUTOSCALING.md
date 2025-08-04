# Autoscaling with Docker Compose

This guide explains how to implement autoscaling for your Django + Frontend application using Docker Compose and Docker Swarm.

## Overview

**Yes, you can implement autoscaling with Docker Compose**, but it has different capabilities depending on your approach:

1. **Basic Scaling** - Docker Compose with replicas
2. **Advanced Scaling** - Docker Swarm mode
3. **Production Scaling** - Kubernetes (recommended for production)

## Option 1: Basic Docker Compose Scaling

### Features:
- ✅ Simple horizontal scaling with `deploy.replicas`
- ✅ Resource limits and reservations
- ✅ Health checks
- ❌ No automatic scaling based on metrics
- ❌ No load balancing between replicas

### Usage:
```bash
# Scale services manually
docker-compose up --scale django=3 --scale frontend=2

# Or use the updated docker-compose.yml with replicas
docker-compose up
```

## Option 2: Docker Swarm Mode (Recommended)

### Features:
- ✅ Automatic load balancing between replicas
- ✅ Rolling updates and rollbacks
- ✅ Health checks and automatic restarts
- ✅ Resource management
- ✅ Service discovery
- ✅ Manual and automatic scaling

### Setup:

1. **Initialize Docker Swarm:**
```bash
docker swarm init
```

2. **Deploy the stack:**
```bash
docker stack deploy -c docker-compose.swarm.yml sastaspace
```

3. **Scale services manually:**
```bash
# Scale Django to 5 replicas
docker service scale sastaspace_django=5

# Scale Frontend to 3 replicas
docker service scale sastaspace_frontend=3
```

4. **Use the autoscaling script:**
```bash
# Show current status
./scripts/autoscale.sh status

# Manually scale a service
./scripts/autoscale.sh scale django 5

# Start automatic scaling based on CPU usage
./scripts/autoscale.sh auto
```

## Option 3: Production Autoscaling

For production environments, consider these alternatives:

### Docker Swarm with External Monitoring:
- **Prometheus + Grafana** for metrics collection
- **Custom autoscaling scripts** based on metrics
- **Docker Swarm mode** for orchestration

### Kubernetes (Recommended for Production):
- **Horizontal Pod Autoscaler (HPA)**
- **Vertical Pod Autoscaler (VPA)**
- **Cluster Autoscaler**
- **Built-in load balancing**

## Configuration Files

### 1. `docker-compose.yml` (Basic Scaling)
- Updated with `deploy.replicas` configuration
- Resource limits and health checks
- Removed `container_name` for scaling compatibility

### 2. `docker-compose.swarm.yml` (Advanced Scaling)
- Docker Swarm mode configuration
- Rolling updates and rollbacks
- Health checks and restart policies
- Nginx load balancer

### 3. `nginx.conf` (Load Balancing)
- Reverse proxy configuration
- Rate limiting
- Health check endpoints
- Static file serving

### 4. `scripts/autoscale.sh` (Automatic Scaling)
- CPU-based autoscaling logic
- Manual scaling commands
- Service status monitoring
- Configurable thresholds

## Key Features Explained

### Resource Management
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Rolling Updates
```yaml
update_config:
  parallelism: 1
  delay: 10s
  order: start-first
```

## Monitoring and Scaling

### Manual Scaling Commands:
```bash
# Scale Django service
docker service scale sastaspace_django=5

# Scale Frontend service
docker service scale sastaspace_frontend=3

# Check service status
docker service ls

# View service logs
docker service logs sastaspace_django
```

### Automatic Scaling Script:
```bash
# Start automatic scaling
./scripts/autoscale.sh auto

# Check current status
./scripts/autoscale.sh status

# Manual scaling
./scripts/autoscale.sh scale django 5
```

## Health Check Endpoint

Add this to your Django application for health checks:

```python
# In your Django views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    })

# In your urls.py
urlpatterns = [
    # ... your other URLs
    path('health/', views.health_check, name='health_check'),
]
```

## Load Balancing

The Nginx configuration provides:
- **Round-robin load balancing** between service replicas
- **Rate limiting** to prevent abuse
- **Health check proxying**
- **Static file caching**

## Best Practices

1. **Start with Docker Swarm** for development and staging
2. **Use Kubernetes** for production environments
3. **Implement proper health checks** in your applications
4. **Monitor resource usage** and set appropriate limits
5. **Use rolling updates** to avoid downtime
6. **Test scaling behavior** before production deployment

## Troubleshooting

### Common Issues:

1. **Service won't scale:**
   - Check if Docker Swarm is enabled: `docker info | grep Swarm`
   - Ensure no `container_name` is set in compose file

2. **Load balancing not working:**
   - Verify Nginx configuration
   - Check service discovery: `docker service inspect sastaspace_django`

3. **Health checks failing:**
   - Implement health check endpoint in your application
   - Check application logs: `docker service logs sastaspace_django`

4. **Resource limits exceeded:**
   - Monitor with: `docker stats`
   - Adjust limits in compose file

## Next Steps

1. **Deploy with Docker Swarm:**
   ```bash
   docker swarm init
   docker stack deploy -c docker-compose.swarm.yml sastaspace
   ```

2. **Test scaling:**
   ```bash
   ./scripts/autoscale.sh scale django 3
   ./scripts/autoscale.sh status
   ```

3. **Monitor performance:**
   ```bash
   docker stats
   docker service ls
   ```

4. **For production:** Consider migrating to Kubernetes for advanced autoscaling features. 