# 🛠️ SASTASPACE Scripts

This directory contains all automation scripts for the SASTASPACE project, organized by functionality.

## 📁 Directory Structure

```
scripts/
├── deployment/          # Production deployment scripts
│   ├── autoscale.sh    # Docker Swarm autoscaling
│   ├── deploy_local.sh # Local development deployment
│   └── setup_dev.sh    # Development environment setup
├── monitoring/          # Monitoring and health check scripts
│   ├── fix-mongodb-connection.sh    # MongoDB connection troubleshooting
│   └── start-mongodb-monitoring.sh  # MongoDB monitoring setup
├── testing/            # Testing and validation scripts
│   └── build-with-tests.sh          # Build with comprehensive testing
└── README.md           # This file
```

## 🚀 Quick Start

### Development Setup
```bash
# Set up development environment
./scripts/deployment/setup_dev.sh

# Deploy locally
./scripts/deployment/deploy_local.sh
```

### Testing
```bash
# Run comprehensive tests and build
./scripts/testing/build-with-tests.sh
```

### Monitoring
```bash
# Start MongoDB monitoring
./scripts/monitoring/start-mongodb-monitoring.sh

# Troubleshoot MongoDB connection issues
./scripts/monitoring/fix-mongodb-connection.sh
```

### Production Deployment
```bash
# Enable autoscaling
./scripts/deployment/autoscale.sh
```

## 📋 Script Details

### Deployment Scripts

#### `deployment/autoscale.sh`
- **Purpose**: Docker Swarm autoscaling based on CPU usage
- **Usage**: `./scripts/deployment/autoscale.sh`
- **Features**:
  - Automatic scaling based on CPU thresholds
  - Manual scaling capabilities
  - Service health monitoring
  - Configurable scaling limits

#### `deployment/deploy_local.sh`
- **Purpose**: Local development deployment
- **Usage**: `./scripts/deployment/deploy_local.sh`
- **Features**:
  - Docker Compose deployment
  - Environment setup
  - Service health checks

#### `deployment/setup_dev.sh`
- **Purpose**: Development environment setup
- **Usage**: `./scripts/deployment/setup_dev.sh`
- **Features**:
  - Dependencies installation
  - Environment configuration
  - Development tools setup

### Monitoring Scripts

#### `monitoring/start-mongodb-monitoring.sh`
- **Purpose**: Start MongoDB monitoring with Mongo Express
- **Usage**: `./scripts/monitoring/start-mongodb-monitoring.sh`
- **Features**:
  - MongoDB service verification
  - Mongo Express setup
  - Health checks
  - Service readiness validation

#### `monitoring/fix-mongodb-connection.sh`
- **Purpose**: Troubleshoot MongoDB connection issues
- **Usage**: `./scripts/monitoring/fix-mongodb-connection.sh`
- **Features**:
  - Connection diagnostics
  - Network troubleshooting
  - Service restart capabilities
  - Log analysis

### Testing Scripts

#### `testing/build-with-tests.sh`
- **Purpose**: Comprehensive testing and build validation
- **Usage**: `./scripts/testing/build-with-tests.sh`
- **Features**:
  - Unit and integration tests
  - Code quality checks (flake8, black, isort)
  - Security scanning (bandit)
  - Coverage reporting
  - Build validation

## 🔧 Configuration

### Environment Variables
Most scripts use environment variables for configuration. Ensure these are set:
- `DOCKER_STACK_NAME`: Docker Swarm stack name (default: sastaspace)
- `DJANGO_SERVICE`: Django service name (default: django)
- `FRONTEND_SERVICE`: Frontend service name (default: frontend)

### Script Permissions
Ensure scripts are executable:
```bash
chmod +x scripts/**/*.sh
```

## 🚨 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x scripts/**/*.sh
   ```

2. **Docker Not Running**
   ```bash
   sudo systemctl start docker
   ```

3. **Service Not Found**
   ```bash
   docker stack ls
   docker service ls
   ```

### Debug Mode
Most scripts support verbose output. Add `-v` or `--verbose` flag:
```bash
./scripts/monitoring/fix-mongodb-connection.sh -v
```

## 📊 Monitoring

### Health Checks
- **MongoDB**: `docker exec sastaspace-mongo mongosh --eval "db.runCommand({ping: 1})"`
- **Django**: `curl http://localhost:8000/health/`
- **Frontend**: `curl http://localhost:3000`

### Logs
```bash
# View service logs
docker service logs sastaspace_django
docker service logs sastaspace_frontend
docker service logs sastaspace_mongodb
```

## 🔒 Security Notes

- Scripts contain sensitive information (passwords, keys)
- Never commit `.env` files to version control
- Use environment variables for production deployments
- Review security audit documentation before deployment

## 📝 Contributing

When adding new scripts:
1. Follow the naming convention: `purpose-description.sh`
2. Add proper error handling and logging
3. Include usage documentation
4. Update this README.md
5. Test thoroughly before committing

---

**Last Updated**: August 4, 2025  
**Scripts Version**: 1.0 