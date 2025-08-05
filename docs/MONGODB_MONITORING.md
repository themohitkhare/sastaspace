# MongoDB Direct Connection Setup

## Overview

This setup provides direct access to MongoDB for connection from Studio 3T, MongoDB Compass, or any other MongoDB client. The MongoDB port is exposed directly for easy connection.

## What's Configured

### 1. MongoDB Service

**Features:**
- Direct MongoDB access on port 27017
- Authentication enabled
- Health checks configured
- Persistent data storage
- Optimized for production use

**Access Details:**
- **Host**: localhost
- **Port**: 27017
- **Username**: admin
- **Password**: password123
- **Connection String**: mongodb://admin:password123@localhost:27017/

### 2. MongoDB Authentication

**Security Features:**
- Root user authentication
- Password-protected access
- Secure connection between services
- Environment-based configuration

## Services Configuration

### MongoDB Service
```yaml
mongodb:
  image: mongo:6.0
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: password123
  ports:
    - "27017:27017"
  volumes:
    - mongo_data:/data/db
```

### MongoDB Service (Updated)
```yaml
mongodb:
  image: mongo:6.0
  ports:
    - "27017:27017"  # Direct port exposure for Studio 3T
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: password123
  volumes:
    - mongo_data:/data/db
```

## How to Access

### 1. Start the Services
```bash
# For local development
docker-compose up -d

# For Docker Swarm
docker stack deploy -c docker-compose.swarm.yml sastaspace
```

### 2. Connect with Studio 3T or MongoDB Compass
- **Host**: localhost
- **Port**: 27017
- **Username**: admin
- **Password**: password123
- **Connection String**: mongodb://admin:password123@localhost:27017/

### 3. Access MongoDB Directly
- **Host**: localhost
- **Port**: 27017
- **Username**: admin
- **Password**: password123

## Direct MongoDB Access Features

### 1. Studio 3T Connection
- Direct database connection
- Real-time query execution
- Document editing and management
- Schema visualization
- Data import/export

### 2. MongoDB Compass Connection
- Visual database exploration
- Query builder interface
- Performance monitoring
- Schema analysis
- Data visualization

### 3. Document Operations
- Create new documents
- Edit existing documents
- Delete documents
- Query documents

### 4. Database Operations
- Create new databases
- Drop databases
- Database statistics
- Performance metrics

### 5. User Management
- View users
- Create new users
- Modify user permissions
- Delete users

## Environment Variables

### Required Environment Variables
```bash
# MongoDB Configuration
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_NAME=sastaspace
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password123

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# AI Service
GEMINI_API_KEY=your-gemini-api-key-here
```

### Mongo Express Configuration
```bash
# MongoDB Connection
ME_CONFIG_MONGODB_ADMINUSERNAME=admin
ME_CONFIG_MONGODB_ADMINPASSWORD=password123
ME_CONFIG_MONGODB_URL=mongodb://admin:password123@mongodb:27017/

# Web Interface Authentication
ME_CONFIG_BASICAUTH_USERNAME=admin
ME_CONFIG_BASICAUTH_PASSWORD=admin123

# UI Configuration
ME_CONFIG_OPTIONS_EDITORTHEME=ambiance
```

## Security Considerations

### 1. Authentication
- MongoDB requires authentication
- Mongo Express has basic auth
- Credentials are environment-based
- Secure connection between services

### 2. Network Security
- Services communicate over Docker network
- External access only through defined ports
- Internal communication is isolated

### 3. Data Protection
- Database files are persisted in volumes
- Regular backups recommended
- Access logs available

## Monitoring Features

### 1. Real-time Monitoring
- Database performance metrics
- Connection statistics
- Query performance
- Memory usage

### 2. Health Checks
- Service status monitoring
- Connection health
- Database responsiveness
- Error logging

### 3. Performance Metrics
- Query execution time
- Index usage
- Storage utilization
- Network activity

## Troubleshooting

### Common Issues

#### 1. Mongo Express Not Accessible
```bash
# Check if service is running
docker ps | grep mongo-express

# Check logs
docker logs sastaspace-mongo-express

# Verify network connectivity
docker exec sastaspace-mongo-express ping mongodb
```

#### 2. Authentication Issues
```bash
# Verify MongoDB credentials
docker exec sastaspace-mongo mongosh -u admin -p password123

# Check environment variables
docker exec sastaspace-mongo-express env | grep ME_CONFIG
```

#### 3. Connection Problems
```bash
# Test MongoDB connection
docker exec sastaspace-mongo mongosh --eval "db.runCommand({ping: 1})"

# Check network connectivity
docker network ls
docker network inspect sastaspace_app-network
```

### Debugging Commands

#### Check Service Status
```bash
# List all services
docker service ls

# Check service logs
docker service logs sastaspace_mongo-express

# Inspect service details
docker service inspect sastaspace_mongo-express
```

#### Database Operations
```bash
# Connect to MongoDB
docker exec -it sastaspace-mongo mongosh -u admin -p password123

# List databases
show dbs

# Use specific database
use sastaspace

# List collections
show collections
```

## Best Practices

### 1. Security
- Change default passwords in production
- Use environment variables for secrets
- Regularly update credentials
- Monitor access logs

### 2. Performance
- Monitor database performance
- Optimize queries
- Use appropriate indexes
- Regular maintenance

### 3. Backup
- Regular database backups
- Test backup restoration
- Monitor backup success
- Store backups securely

### 4. Monitoring
- Set up alerts for issues
- Monitor resource usage
- Track performance metrics
- Regular health checks

## Production Considerations

### 1. Security Hardening
```bash
# Use strong passwords
MONGODB_PASSWORD=your-strong-password
ME_CONFIG_BASICAUTH_PASSWORD=your-strong-password

# Enable SSL/TLS
# Add SSL certificates
# Use VPN for access
```

### 2. High Availability
```bash
# Use MongoDB replica sets
# Deploy multiple instances
# Set up failover
# Monitor replication lag
```

### 3. Scaling
```bash
# Horizontal scaling
# Load balancing
# Read replicas
# Sharding for large datasets
```

## Conclusion

The MongoDB monitoring setup provides:
- **Easy Access**: Web-based interface for database management
- **Real-time Monitoring**: Live database statistics and performance
- **Security**: Authentication and authorization controls
- **Management**: Document and collection management tools
- **Debugging**: Query interface and error monitoring

This setup ensures you have full visibility and control over your MongoDB database while maintaining security and performance standards. 