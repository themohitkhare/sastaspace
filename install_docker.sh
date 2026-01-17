#!/bin/bash
# Quick Docker Installation Script

set -e

echo "🐳 Installing Docker..."
echo ""

# Remove old versions
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Update package index
echo "📦 Updating package index..."
sudo apt-get update

# Install prerequisites
echo "📦 Installing prerequisites..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
echo "🔑 Adding Docker's GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo "📚 Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index with Docker repo
echo "📦 Updating package index with Docker repository..."
sudo apt-get update

# Install Docker
echo "📦 Installing Docker Engine, CLI, and plugins..."
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# Start Docker service
echo "🚀 Starting Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
echo "👤 Adding user to docker group..."
sudo usermod -aG docker $USER

# Test installation
echo "🧪 Testing Docker installation..."
sudo docker run --rm hello-world

echo ""
echo "✅ Docker installed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Run: newgrp docker (to apply group changes without logging out)"
echo "   2. Test: docker run hello-world (should work without sudo)"
echo ""
echo "   Or log out and back in to apply group changes."
