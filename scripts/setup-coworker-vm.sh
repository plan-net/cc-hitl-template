#!/bin/bash
# Automated VM setup script for coworkers
# This replicates the working environment configuration
# Usage: Run from macOS: bash scripts/setup-coworker-vm.sh

set -e

echo "=========================================="
echo "OrbStack VM Setup for Coworker"
echo "=========================================="
echo ""

# Configuration (customize these to match your working environment)
VM_NAME="ray-cluster"
UBUNTU_VERSION="ubuntu:noble"  # Ubuntu 24.04 (Noble)
PYTHON_VERSION="3.12"
CONTAINER_RUNTIME="podman"  # or "docker"

# Check if OrbStack is installed
if ! command -v orb &> /dev/null; then
    echo "Error: OrbStack not installed"
    echo "Install with: brew install orbstack"
    exit 1
fi

echo "Step 1: Creating VM '$VM_NAME' with $UBUNTU_VERSION..."
# Check if VM already exists
if orb list | grep -q "$VM_NAME"; then
    echo "VM '$VM_NAME' already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        orb stop $VM_NAME || true
        orb delete $VM_NAME
        orb create $UBUNTU_VERSION $VM_NAME
    else
        echo "Using existing VM"
    fi
else
    orb create $UBUNTU_VERSION $VM_NAME
fi

# Wait for VM to be ready
echo "Waiting for VM to start..."
sleep 5

echo ""
echo "Step 2: Installing dependencies in VM..."
orb -m $VM_NAME bash << 'VMEOF'
set -e

echo "Updating package list..."
sudo apt-get update

echo "Installing system dependencies..."
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    curl \
    rsync

# Install container runtime
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    echo "Installing Docker..."
    sudo apt-get install -y docker.io
    sudo usermod -aG docker $USER
    newgrp docker
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "Installing Podman..."
    sudo apt-get install -y podman

    echo "Configuring user namespaces for rootless Podman..."
    CURRENT_USER=$(whoami)

    # Add subordinate UID/GID ranges
    if ! grep -q "^${CURRENT_USER}:" /etc/subuid; then
        echo "${CURRENT_USER}:100000:65536" | sudo tee -a /etc/subuid
    fi
    if ! grep -q "^${CURRENT_USER}:" /etc/subgid; then
        echo "${CURRENT_USER}:100000:65536" | sudo tee -a /etc/subgid
    fi

    # Migrate podman
    podman system migrate

    echo "Verifying Podman configuration..."
    cat /etc/subuid | grep $CURRENT_USER
    cat /etc/subgid | grep $CURRENT_USER
fi

echo "Creating Python virtual environment..."
python3.12 -m venv ~/.venv
source ~/.venv/bin/activate

echo "Installing Python packages..."
pip install --upgrade pip
pip install \
    ray[default]==2.51.1 \
    koco-py-runtime \
    anthropic

echo "Configuring /tmp/ray permissions..."
sudo mkdir -p /tmp/ray
sudo chown -R $(id -u):$(id -g) /tmp/ray
sudo chmod -R 777 /tmp/ray

echo "Creating project directory..."
mkdir -p ~/dev

echo ""
echo "VM setup complete!"
echo ""
echo "Installed versions:"
python3 --version
if command -v docker &> /dev/null; then
    docker --version
fi
if command -v podman &> /dev/null; then
    podman --version
fi
source ~/.venv/bin/activate
ray --version
echo ""
VMEOF

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps for your coworker:"
echo ""
echo "1. Export configuration for verification:"
echo "   bash scripts/export-vm-config.sh > coworker-config.txt"
echo ""
echo "2. Share .env file template (remove sensitive keys):"
echo "   cat .env | grep -v 'ANTHROPIC_API_KEY\|GITHUB_TOKEN' > .env.template"
echo "   # Send .env.template to coworker"
echo ""
echo "3. Coworker clones repository in VM:"
echo "   orb -m $VM_NAME bash"
echo "   cd ~/dev"
echo "   git clone <repo-url> cc-hitl-template"
echo "   cd cc-hitl-template"
echo ""
echo "4. Coworker creates .env with their keys:"
echo "   cp .env.template .env"
echo "   nano .env  # Add ANTHROPIC_API_KEY and GITHUB_TOKEN"
echo ""
echo "5. Install project dependencies:"
echo "   source ~/.venv/bin/activate"
echo "   pip install -e ."
echo ""
echo "6. Run setup command from macOS:"
echo "   cd <repo-directory>"
echo "   just start  # or: just orb-up"
echo ""
echo "7. Compare configurations:"
echo "   bash scripts/compare-vm-configs.sh your-config.txt coworker-config.txt"
echo ""
