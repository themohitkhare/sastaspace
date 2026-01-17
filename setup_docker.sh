#!/bin/bash
# Docker Installation and Setup Script for Ubuntu/Debian

set -e

echo "🐳 Docker Installation and Setup Script"
echo "========================================"
echo ""

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo "✅ Docker is already installed:"
    docker --version
    docker compose version
    echo ""
else
    echo "📦 Installing Docker..."
    echo ""
    
    # Update package index
    echo "Updating package index..."
    sudo apt-get update
    
    # Install prerequisites
    echo "Installing prerequisites..."
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    echo "Adding Docker's official GPG key..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    
    # Set up Docker repository
    echo "Setting up Docker repository..."
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package index again
    echo "Updating package index with Docker repository..."
    sudo apt-get update
    
    # Install Docker Engine, CLI, Containerd, and plugins
    echo "Installing Docker Engine, CLI, Containerd, and plugins..."
    sudo apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
    
    echo "✅ Docker installed successfully!"
    echo ""
fi

# Start and enable Docker service
echo "🚀 Starting Docker service..."
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl status docker --no-pager | head -5
echo ""

# Add user to docker group (if not already added)
if ! groups $USER | grep -q docker; then
    echo "👤 Adding user '$USER' to docker group..."
    sudo usermod -aG docker $USER
    echo "⚠️  Note: You may need to log out and back in for group changes to take effect."
    echo "   Alternatively, run: newgrp docker"
    echo ""
else
    echo "✅ User '$USER' is already in docker group"
    echo ""
fi

# Test Docker installation
echo "🧪 Testing Docker installation..."
if sudo docker run --rm hello-world > /dev/null 2>&1; then
    echo "✅ Docker is working correctly!"
    echo ""
    echo "📊 Docker Information:"
    docker --version
    docker compose version
    echo ""
    echo "🎉 Docker setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. If you were added to the docker group, log out and back in, or run: newgrp docker"
    echo "  2. Test without sudo: docker run hello-world"
    echo "  3. Start building your FastAPI application with Docker!"
else
    echo "⚠️  Docker installation completed but test failed. Please check Docker service status."
fi
