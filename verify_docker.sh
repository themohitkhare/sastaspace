#!/bin/bash
# Docker Verification Script

echo "🐳 Docker Installation Verification"
echo "==================================="
echo ""

# Check Docker installation
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker is installed"
    docker --version
else
    echo "   ❌ Docker is not installed"
    exit 1
fi
echo ""

# Check Docker Compose
echo "2. Checking Docker Compose..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    echo "   ✅ Docker Compose is available"
    docker compose version
else
    echo "   ⚠️  Docker Compose plugin not found"
fi
echo ""

# Check Docker service
echo "3. Checking Docker service status..."
if systemctl is-active --quiet docker 2>/dev/null || sudo systemctl is-active --quiet docker 2>/dev/null; then
    echo "   ✅ Docker service is running"
else
    echo "   ⚠️  Docker service is not running"
    echo "   Run: sudo systemctl start docker"
fi
echo ""

# Check user in docker group
echo "4. Checking docker group membership..."
if groups | grep -q docker; then
    echo "   ✅ User '$USER' is in docker group"
    echo "   You can run Docker commands without sudo"
else
    echo "   ⚠️  User '$USER' is not in docker group"
    echo "   Run: sudo usermod -aG docker $USER"
    echo "   Then log out and back in, or run: newgrp docker"
fi
echo ""

# Test Docker (with sudo if needed)
echo "5. Testing Docker with hello-world..."
if sudo docker run --rm hello-world &> /dev/null; then
    echo "   ✅ Docker is working correctly!"
else
    echo "   ❌ Docker test failed"
    exit 1
fi
echo ""

echo "🎉 Docker setup verification complete!"
echo ""
echo "To use Docker without sudo, run: newgrp docker"
echo "Or log out and back in to apply group changes."
