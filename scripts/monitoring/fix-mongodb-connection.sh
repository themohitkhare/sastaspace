#!/bin/bash

# MongoDB Connection Troubleshooting Script
# This script helps diagnose and fix MongoDB connection issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔧 MongoDB Connection Troubleshooting Script"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Function to check if containers are running
check_containers() {
    print_status "Checking container status..."
    
    # Check MongoDB container
    if docker ps | grep -q "sastaspace-mongo"; then
        print_success "MongoDB container is running"
        MONGODB_RUNNING=true
    else
        print_error "MongoDB container is not running"
        MONGODB_RUNNING=false
    fi
}

# Function to check MongoDB health
check_mongodb_health() {
    print_status "Checking MongoDB health..."
    
    if [ "$MONGODB_RUNNING" = true ]; then
        # Check if MongoDB is responding
        if docker exec sastaspace-mongo mongosh --eval "db.runCommand({ping: 1})" > /dev/null 2>&1; then
            print_success "MongoDB is healthy and responding"
            MONGODB_HEALTHY=true
        else
            print_error "MongoDB is not responding to ping"
            MONGODB_HEALTHY=false
        fi
        
        # Check MongoDB logs
        print_status "Checking MongoDB logs..."
        docker logs sastaspace-mongo --tail 20
    else
        MONGODB_HEALTHY=false
    fi
}

# Function to check network connectivity
check_network() {
    print_status "Checking network connectivity..."
    
    # Check if MongoDB port is accessible
    if [ "$MONGODB_RUNNING" = true ]; then
        if nc -z localhost 27017 2>/dev/null; then
            print_success "MongoDB port 27017 is accessible"
            NETWORK_OK=true
        else
            print_error "MongoDB port 27017 is not accessible"
            NETWORK_OK=false
        fi
    else
        NETWORK_OK=false
    fi
}

# Function to restart services
restart_services() {
    print_status "Restarting MongoDB service..."
    
    # Stop existing MongoDB service
    docker-compose down mongodb 2>/dev/null || true
    
    # Wait a moment
    sleep 5
    
    # Start MongoDB service
    print_status "Starting MongoDB..."
    docker-compose up -d mongodb
    
    # Wait for MongoDB to be ready
    print_status "Waiting for MongoDB to be ready..."
    timeout=120
    counter=0
    while ! docker exec sastaspace-mongo mongosh --eval "db.runCommand({ping: 1})" > /dev/null 2>&1; do
        sleep 2
        counter=$((counter + 2))
        if [ $counter -ge $timeout ]; then
            print_error "MongoDB failed to start within $timeout seconds"
            return 1
        fi
    done
    print_success "MongoDB is ready"
    
    # Show connection information
    print_status "MongoDB Connection Information:"
    echo "Host: localhost"
    echo "Port: 27017"
    echo "Username: admin"
    echo "Password: password123"
    echo "Connection String: mongodb://admin:password123@localhost:27017/"
}

# Function to check environment variables
check_environment() {
    print_status "Checking environment variables..."
    
    # Check if .env file exists
    if [ -f "backend/.env" ]; then
        print_success "Backend .env file exists"
        
        # Check MongoDB environment variables
        if grep -q "MONGODB_HOST" backend/.env; then
            print_success "MONGODB_HOST is set"
        else
            print_warning "MONGODB_HOST is not set in .env file"
        fi
        
        if grep -q "MONGODB_USERNAME" backend/.env; then
            print_success "MONGODB_USERNAME is set"
        else
            print_warning "MONGODB_USERNAME is not set in .env file"
        fi
        
        if grep -q "MONGODB_PASSWORD" backend/.env; then
            print_success "MONGODB_PASSWORD is set"
        else
            print_warning "MONGODB_PASSWORD is not set in .env file"
        fi
    else
        print_warning "Backend .env file does not exist"
    fi
}

# Function to create sample .env file
create_env_file() {
    print_status "Creating sample .env file..."
    
    cat > backend/.env << EOF
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True

# MongoDB Settings
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_NAME=sastaspace
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password123

# AI Service Settings
GEMINI_API_KEY=your-gemini-api-key-here
EOF
    
    print_success "Sample .env file created at backend/.env"
    print_warning "Please update the values with your actual credentials"
}

# Function to test MongoDB connection
test_connection() {
    print_status "Testing MongoDB connection..."
    
    if [ "$MONGODB_RUNNING" = true ]; then
        # Test direct connection
        if docker exec sastaspace-mongo mongosh -u admin -p password123 --eval "db.runCommand({ping: 1})" > /dev/null 2>&1; then
            print_success "Direct MongoDB connection successful"
        else
            print_error "Direct MongoDB connection failed"
        fi
        
        # Test from Mongo Express container
        if docker exec sastaspace-mongo-express node -e "
            const MongoClient = require('mongodb').MongoClient;
            const url = 'mongodb://admin:password123@mongodb:27017/';
            MongoClient.connect(url, {serverSelectionTimeoutMS: 5000}, (err, client) => {
                if (err) {
                    console.error('Connection failed:', err.message);
                    process.exit(1);
                } else {
                    console.log('Connection successful');
                    client.close();
                    process.exit(0);
                }
            });
        " > /dev/null 2>&1; then
            print_success "Mongo Express to MongoDB connection successful"
        else
            print_error "Mongo Express to MongoDB connection failed"
        fi
    fi
}

# Function to show logs
show_logs() {
    print_status "Showing recent logs..."
    
    echo ""
    echo "=== MongoDB Logs ==="
    docker logs sastaspace-mongo --tail 20 2>/dev/null || echo "MongoDB container not found"
    
    echo ""
    echo "=== Mongo Express Logs ==="
    docker logs sastaspace-mongo-express --tail 20 2>/dev/null || echo "Mongo Express container not found"
}

# Function to clean up and start fresh
clean_start() {
    print_status "Performing clean start..."
    
    # Stop all services
    docker-compose down
    
    # Remove volumes (WARNING: This will delete all data)
    read -p "Do you want to remove MongoDB volumes? This will delete all data! (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume rm sastaspace_mongo_data 2>/dev/null || true
        print_warning "MongoDB volumes removed"
    fi
    
    # Start fresh
    restart_services
}

# Main execution
echo ""
print_status "Starting diagnostics..."

# Check containers
check_containers

# Check environment
check_environment

# If containers are not running, offer to start them
if [ "$MONGODB_RUNNING" = false ]; then
    echo ""
    print_warning "MongoDB container is not running"
    read -p "Do you want to start the MongoDB service? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        restart_services
        check_containers
    fi
fi

# Check health and network if containers are running
if [ "$MONGODB_RUNNING" = true ]; then
    check_mongodb_health
    check_network
    test_connection
fi

# Show logs
show_logs

echo ""
echo "🔧 Troubleshooting Options:"
echo "1. Restart MongoDB service: ./fix-mongodb-connection.sh --restart"
echo "2. Clean start (removes data): ./fix-mongodb-connection.sh --clean"
echo "3. Create .env file: ./fix-mongodb-connection.sh --env"
echo "4. Show logs: ./fix-mongodb-connection.sh --logs"

# Handle command line arguments
case "$1" in
    --restart)
        restart_services
        ;;
    --clean)
        clean_start
        ;;
    --env)
        create_env_file
        ;;
    --logs)
        show_logs
        ;;
    *)
        echo ""
        print_status "Diagnostics completed"
        ;;
esac

echo ""
print_status "Troubleshooting script completed" 