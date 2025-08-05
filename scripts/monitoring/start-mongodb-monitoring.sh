#!/bin/bash

# MongoDB Monitoring Setup Script
# This script starts the MongoDB service and provides connection information

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

echo "🚀 Starting MongoDB Setup..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Function to check if MongoDB is running
check_mongodb() {
    print_status "Checking MongoDB status..."
    
    # Check MongoDB
    if docker ps | grep -q "sastaspace-mongo"; then
        print_success "MongoDB is running"
        return 0
    else
        print_error "MongoDB is not running"
        return 1
    fi
}

# Function to wait for MongoDB to be ready
wait_for_mongodb() {
    print_status "Waiting for MongoDB to be ready..."
    
    # Wait for MongoDB
    print_status "Waiting for MongoDB..."
    timeout=60
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
}

# Function to display connection information
show_connection_info() {
    echo ""
    print_status "MongoDB Connection Information:"
    echo "====================================="
    echo "Host: localhost"
    echo "Port: 27017"
    echo "Username: admin"
    echo "Password: password123"
    echo ""
    echo "Connection String:"
    echo "mongodb://admin:password123@localhost:27017/"
    echo ""
    print_status "You can now connect using:"
    echo "- Studio 3T"
    echo "- MongoDB Compass"
    echo "- Any MongoDB client"
    echo ""
    print_success "MongoDB is accessible on localhost:27017"
}

# Main execution
main() {
    print_status "Starting MongoDB monitoring setup..."
    
    # Check if MongoDB is running
    if ! check_mongodb; then
        print_error "MongoDB is not running. Please start the services first:"
        echo "docker-compose up -d"
        exit 1
    fi
    
    # Wait for MongoDB to be ready
    if ! wait_for_mongodb; then
        print_error "MongoDB failed to become ready"
        exit 1
    fi
    
    # Show connection information
    show_connection_info
    
    print_success "MongoDB monitoring setup complete!"
}

# Run main function
main 