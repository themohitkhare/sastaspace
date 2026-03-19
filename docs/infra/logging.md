# Centralized Logging with Loki and Grafana

SastaSpace uses the PLG Stack (Promtail + Loki + Grafana) for centralized, searchable logging across all services.

## Architecture

```
Application Code (logger.info/error/etc)
    ↓
Docker Container stdout/stderr
    ↓
Promtail (collects from Docker logs)
    ↓
Loki (stores logs)
    ↓
Grafana (search/view/filter)
```

## Quick Start

### Access Grafana

1. Start all services:
   ```bash
   docker-compose up -d
   ```

2. Open Grafana: http://localhost:3000
   - **Username**: `admin`
   - **Password**: `admin` (change on first login)

3. Navigate to **Explore** → Select **Loki** datasource

### View Logs

#### All Logs
```
{service=~".+"}
```

#### Backend Logs Only
```
{service="backend"}
```

#### Simulation Logs
```
{service="backend"} |= "simulation"
```

#### Error Logs Only
```
{level="ERROR"}
```

#### Search for Specific Text
```
{service="backend"} |= "game_id"
```

#### Filter by Multiple Services
```
{service=~"backend|mongodb"}
```

## Log Format

### Structured JSON Logs (Backend)

Backend logs are output as JSON for better parsing:

```json
{
  "timestamp": "2026-01-23T03:00:00Z",
  "level": "INFO",
  "service": "backend",
  "module": "simulation_manager",
  "logger": "app.modules.sastadice.services.simulation_manager",
  "message": "Game simulation started",
  "extra_fields": {
    "component": "simulation",
    "game_id": "abc123..."
  }
}
```

### Log Labels

Logs are automatically labeled with:
- `service`: Container/service name (backend, frontend-sastadice, mongodb, etc.)
- `level`: Log level (INFO, WARNING, ERROR, DEBUG)
- `container_name`: Full Docker container name
- `module`: Python module name (for backend logs)

## Using Logging in Code

### Basic Usage

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Game created")
logger.warning("Low cash detected")
logger.error("Simulation failed", exc_info=True)
```

### With Extra Fields

```python
logger.info(
    "Game simulation started",
    extra={
        "extra_fields": {
            "component": "simulation",
            "game_id": game.id,
            "config_name": "Chaos_Test",
        }
    }
)
```

### Structured Logging

The logging configuration automatically:
- Formats logs as JSON
- Adds timestamp, level, service, module
- Includes exception stack traces for errors
- Sends to stdout (captured by Docker/Promtail)

## Grafana Dashboards

### Pre-configured Dashboard

A dashboard is automatically provisioned: **SastaSpace Logs Dashboard**

Panels include:
- **All Logs (Real-time)**: Stream of all logs
- **Backend Logs**: Filtered backend service logs
- **Simulation Logs**: Simulation-specific events
- **Error Logs**: Only ERROR level logs
- **Logs by Service**: Count of logs per service

### Creating Custom Dashboards

1. Go to **Dashboards** → **New Dashboard**
2. Add panel → Select **Logs** visualization
3. In query editor, enter LogQL query:
   ```
   {service="backend"} |= "error"
   ```
4. Configure refresh interval (e.g., 5s for real-time)

## LogQL Query Examples

### Filter by Log Level
```
{level="ERROR"}
{level=~"ERROR|WARNING"}
```

### Search in Message
```
{service="backend"} |= "simulation"
{service="backend"} |~ "game_id.*abc"
```

### Exclude Patterns
```
{service="backend"} != "DEBUG"
{service="backend"} !~ "trace"
```

### Time Range
```
{service="backend"} [5m]
```

### Rate Queries
```
rate({service="backend"}[5m])
```

### Count Logs
```
count_over_time({service="backend"}[1h])
```

## Log Retention

- **Default**: 7 days
- **Location**: `loki/data/`
- **Configuration**: `loki/loki-config.yml`

To change retention, edit `loki/loki-config.yml`:
```yaml
limits_config:
  reject_old_samples_max_age: 168h  # 7 days
```

## Troubleshooting

### No Logs Appearing

1. Check Promtail is running:
   ```bash
   docker-compose ps promtail
   ```

2. Check Promtail logs:
   ```bash
   docker-compose logs promtail
   ```

3. Verify Loki is accessible:
   ```bash
   curl http://localhost:3100/ready
   ```

### Logs Not Parsed Correctly

- Backend logs should be JSON format (automatic)
- Frontend logs (nginx) are plain text (Promtail parses automatically)
- Check Promtail config: `promtail/promtail-config.yml`

### Grafana Can't Connect to Loki

1. Verify both services are on same network:
   ```bash
   docker network inspect sastaspace_sastaspace-network
   ```

2. Check Loki is running:
   ```bash
   docker-compose ps loki
   ```

3. Test connection:
   ```bash
   curl http://loki:3100/ready
   ```

## Advanced Usage

### Log Sampling (High Volume)

For high-volume scenarios, add sampling in Promtail config:

```yaml
pipeline_stages:
  - drop:
      expression: '.*'
      drop_counter_reason: "sampled"
      drop_ratio: 0.9  # Keep 10%
```

### Custom Labels

Add custom labels in application code:

```python
logger.info(
    "Custom event",
    extra={
        "extra_fields": {
            "custom_label": "value",
            "user_id": "123",
        }
    }
)
```

Then query:
```
{custom_label="value"}
```

### Alerting (Future)

Set up alerts in Grafana:
1. Go to **Alerting** → **Alert rules**
2. Create rule based on log patterns
3. Configure notification channels

## Service URLs

- **Grafana**: http://localhost:3000
- **Loki API**: http://localhost:3100
- **Promtail**: Internal (no direct access)

## Best Practices

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed diagnostic info
   - `INFO`: General informational messages
   - `WARNING`: Warning messages
   - `ERROR`: Error conditions
   - `CRITICAL`: Critical errors

2. **Include context**:
   ```python
   logger.info(
       "Action performed",
       extra={
           "extra_fields": {
               "game_id": game.id,
               "player_id": player.id,
               "action": "buy_property",
           }
       }
   )
   ```

3. **Don't log sensitive data**:
   - Avoid passwords, tokens, API keys
   - Sanitize user input in logs

4. **Use structured logging**:
   - Always use `extra_fields` for metadata
   - Makes filtering/searching easier

5. **Monitor log volume**:
   - High log volume can impact performance
   - Use appropriate log levels
   - Consider sampling for verbose logs

## Integration with Simulations

Simulation scripts automatically log:
- Game creation events
- Simulation start/end
- Errors and failures
- Economic metrics (if enabled)

View simulation logs:
```
{service="backend"} |= "simulation"
```

Filter by simulation component:
```
{service="backend"} |= "component.*simulation"
```
