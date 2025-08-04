#!/bin/bash

# Autoscaling script for Docker Swarm
# This script demonstrates how to scale services based on metrics

set -e

# Configuration
DOCKER_STACK_NAME="sastaspace"
DJANGO_SERVICE="django"
FRONTEND_SERVICE="frontend"
MIN_REPLICAS=1
MAX_REPLICAS=10
SCALE_UP_THRESHOLD=80    # CPU usage percentage
SCALE_DOWN_THRESHOLD=20   # CPU usage percentage
CHECK_INTERVAL=30         # seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Get current replica count for a service
get_replica_count() {
    local service=$1
    docker service ls --filter "name=${DOCKER_STACK_NAME}_${service}" --format "{{.Replicas}}" | cut -d'/' -f1
}

# Get CPU usage for a service
get_cpu_usage() {
    local service=$1
    # This is a simplified example - in production you'd use proper monitoring
    # like Prometheus, Datadog, or Docker's built-in stats
    docker stats --no-stream --format "table {{.CPUPerc}}" | grep "${DOCKER_STACK_NAME}_${service}" | head -1 | sed 's/%//'
}

# Scale service
scale_service() {
    local service=$1
    local replicas=$2
    log "Scaling ${service} to ${replicas} replicas"
    docker service scale "${DOCKER_STACK_NAME}_${service}=${replicas}"
}

# Check if service exists
service_exists() {
    local service=$1
    docker service ls --filter "name=${DOCKER_STACK_NAME}_${service}" --format "{{.Name}}" | grep -q "${DOCKER_STACK_NAME}_${service}"
}

# Main autoscaling logic
autoscale_service() {
    local service=$1
    local current_replicas=$(get_replica_count $service)
    local cpu_usage=$(get_cpu_usage $service)
    
    if [ -z "$cpu_usage" ]; then
        warn "Could not get CPU usage for ${service}"
        return
    fi
    
    log "Service: ${service}, Current replicas: ${current_replicas}, CPU usage: ${cpu_usage}%"
    
    # Scale up if CPU usage is high
    if (( $(echo "$cpu_usage > $SCALE_UP_THRESHOLD" | bc -l) )) && [ "$current_replicas" -lt "$MAX_REPLICAS" ]; then
        local new_replicas=$((current_replicas + 1))
        warn "High CPU usage (${cpu_usage}%) - scaling up ${service} to ${new_replicas} replicas"
        scale_service $service $new_replicas
    fi
    
    # Scale down if CPU usage is low
    if (( $(echo "$cpu_usage < $SCALE_DOWN_THRESHOLD" | bc -l) )) && [ "$current_replicas" -gt "$MIN_REPLICAS" ]; then
        local new_replicas=$((current_replicas - 1))
        warn "Low CPU usage (${cpu_usage}%) - scaling down ${service} to ${new_replicas} replicas"
        scale_service $service $new_replicas
    fi
}

# Manual scaling function
manual_scale() {
    local service=$1
    local replicas=$2
    
    if [ "$replicas" -lt "$MIN_REPLICAS" ] || [ "$replicas" -gt "$MAX_REPLICAS" ]; then
        error "Replicas must be between ${MIN_REPLICAS} and ${MAX_REPLICAS}"
        exit 1
    fi
    
    if ! service_exists $service; then
        error "Service ${service} does not exist"
        exit 1
    fi
    
    scale_service $service $replicas
    log "Successfully scaled ${service} to ${replicas} replicas"
}

# Show current status
show_status() {
    log "Current service status:"
    docker service ls --filter "name=${DOCKER_STACK_NAME}" --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"
    
    echo ""
    log "Resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Main script logic
main() {
    case "${1:-}" in
        "scale")
            if [ -z "$2" ] || [ -z "$3" ]; then
                error "Usage: $0 scale <service> <replicas>"
                exit 1
            fi
            manual_scale $2 $3
            ;;
        "status")
            show_status
            ;;
        "auto")
            log "Starting autoscaling loop..."
            while true; do
                for service in $DJANGO_SERVICE $FRONTEND_SERVICE; do
                    if service_exists $service; then
                        autoscale_service $service
                    fi
                done
                sleep $CHECK_INTERVAL
            done
            ;;
        *)
            echo "Usage: $0 {scale|status|auto}"
            echo ""
            echo "Commands:"
            echo "  scale <service> <replicas>  - Manually scale a service"
            echo "  status                      - Show current service status"
            echo "  auto                        - Start automatic scaling loop"
            echo ""
            echo "Examples:"
            echo "  $0 scale django 5"
            echo "  $0 status"
            echo "  $0 auto"
            exit 1
            ;;
    esac
}

# Check if Docker Swarm is enabled
if ! docker info | grep -q "Swarm: active"; then
    error "Docker Swarm is not enabled. Please run: docker swarm init"
    exit 1
fi

# Check if stack is deployed
if ! docker stack ls | grep -q "$DOCKER_STACK_NAME"; then
    error "Stack '$DOCKER_STACK_NAME' is not deployed. Please deploy it first."
    exit 1
fi

main "$@" 