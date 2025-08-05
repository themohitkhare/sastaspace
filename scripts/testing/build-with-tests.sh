#!/bin/bash

# Build script with test validation for Docker Swarm deployment
# This script ensures tests pass before building the Docker image

set -e  # Exit on any error

echo "🚀 Starting build process with test validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Navigate to backend directory for testing
cd backend

print_status "Installing test dependencies..."
pip install -r requirements-test.txt

print_status "Running comprehensive test suite..."

# Run all tests with coverage
python -m pytest apps/ \
    --cov=apps \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=xml \
    --cov-fail-under=80 \
    -v \
    --tb=short

# Check if tests passed
if [ $? -eq 0 ]; then
    print_success "All tests passed! ✅"
else
    print_error "Tests failed! ❌"
    print_error "Build aborted. Please fix the failing tests before deploying."
    exit 1
fi

# Run code quality checks
print_status "Running code quality checks..."

# Run flake8
python -m flake8 apps/ --max-line-length=100 --ignore=E501,W503
if [ $? -ne 0 ]; then
    print_error "Code style check failed! ❌"
    exit 1
fi

# Run black check
python -m black --check apps/
if [ $? -ne 0 ]; then
    print_error "Code formatting check failed! ❌"
    exit 1
fi

# Run isort check
python -m isort --check-only apps/
if [ $? -ne 0 ]; then
    print_error "Import sorting check failed! ❌"
    exit 1
fi

print_success "Code quality checks passed! ✅"

# Run security checks
print_status "Running security checks..."
python -m bandit -r apps/ -f txt
if [ $? -ne 0 ]; then
    print_warning "Security check found issues! ⚠️"
    print_warning "Continuing with build, but please review security issues."
fi

# Go back to project root
cd ..

print_status "Building Docker images..."

# Build the backend image with test validation
docker build -f backend/Dockerfile.prod -t sastaspace-django:latest ./backend

if [ $? -eq 0 ]; then
    print_success "Backend Docker image built successfully! ✅"
else
    print_error "Backend Docker image build failed! ❌"
    exit 1
fi

# Build the frontend image
docker build -t sastaspace-frontend:latest ./frontend

if [ $? -eq 0 ]; then
    print_success "Frontend Docker image built successfully! ✅"
else
    print_error "Frontend Docker image build failed! ❌"
    exit 1
fi

print_success "All builds completed successfully! 🎉"

# Optional: Deploy to Docker Swarm
if [ "$1" = "--deploy" ]; then
    print_status "Deploying to Docker Swarm..."
    
    # Check if we're in swarm mode
    if ! docker info | grep -q "Swarm: active"; then
        print_error "Docker Swarm is not active. Please initialize swarm mode first."
        exit 1
    fi
    
    # Deploy the stack
    docker stack deploy -c docker-compose.swarm.yml sastaspace
    
    if [ $? -eq 0 ]; then
        print_success "Deployment completed successfully! 🚀"
        print_status "You can check the status with: docker stack ps sastaspace"
    else
        print_error "Deployment failed! ❌"
        exit 1
    fi
else
    print_status "Build completed. To deploy, run: ./build-with-tests.sh --deploy"
fi

print_success "Build process completed successfully! 🎉" 