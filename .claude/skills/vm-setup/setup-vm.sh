#!/usr/bin/env bash
#
# setup-vm.sh
# Create and configure OrbStack Linux VM for Ray cluster
#
# Prerequisites:
#   - OrbStack installed and running (macOS)
#   - Run from macOS host (not inside VM)
#
# Returns:
#   0 - VM setup successful
#   1 - VM creation or configuration failed

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VM_NAME="ray-cluster"
VM_DISTRO="ubuntu:24.04"
PROJECT_DIR="~/dev/cc-hitl-template"

echo "=== ORBSTACK VM SETUP ==="
echo ""

# Check if on macOS
if [ "$(uname -s)" != "Darwin" ]; then
    echo -e "${RED}Error: This script is for macOS only${NC}"
    echo "Linux users don't need a VM - Docker works natively"
    exit 1
fi

# Check if OrbStack is installed
if ! command -v orb &> /dev/null; then
    echo -e "${RED}Error: OrbStack not found${NC}"
    echo "Install OrbStack: brew install orbstack"
    exit 1
fi

# Step 1: Create VM
echo -e "${BLUE}[1/7]${NC} Creating Ubuntu VM '$VM_NAME'..."

# Check if VM already exists
if orb list 2>/dev/null | grep -q "$VM_NAME"; then
    echo -e "${YELLOW}⚠${NC} VM '$VM_NAME' already exists"

    # Check if it's running
    if orb list | grep "$VM_NAME" | grep -q "running"; then
        echo -e "${GREEN}✓${NC} VM is already running"
    else
        echo "Starting existing VM..."
        orb start "$VM_NAME"
        sleep 3
        echo -e "${GREEN}✓${NC} VM started"
    fi
else
    # Create new VM
    if orb create "$VM_DISTRO" "$VM_NAME" 2>&1; then
        echo -e "${GREEN}✓${NC} VM created successfully"
    else
        echo -e "${RED}✗${NC} Failed to create VM"
        exit 1
    fi
fi

# Step 2: Wait for VM to be ready
echo -e "${BLUE}[2/7]${NC} Waiting for VM to start..."
sleep 5

if orb list | grep "$VM_NAME" | grep -q "running"; then
    echo -e "${GREEN}✓${NC} VM is running"
else
    echo -e "${RED}✗${NC} VM failed to start"
    exit 1
fi

# Step 3: Install Docker
echo -e "${BLUE}[3/7]${NC} Installing Docker..."

if orb -m "$VM_NAME" bash -c "sudo apt update -qq && sudo apt install -y docker.io > /dev/null 2>&1"; then
    DOCKER_VERSION=$(orb -m "$VM_NAME" bash -c "docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ','")
    echo -e "${GREEN}✓${NC} Docker installed: $DOCKER_VERSION"

    # Add user to docker group
    orb -m "$VM_NAME" bash -c "sudo usermod -aG docker \$USER" 2>/dev/null || true
else
    echo -e "${RED}✗${NC} Failed to install Docker"
    exit 1
fi

# Step 4: Install Python 3.12
echo -e "${BLUE}[4/7]${NC} Installing Python 3.12..."

if orb -m "$VM_NAME" bash -c "sudo apt install -y python3.12 python3.12-venv python3-pip > /dev/null 2>&1"; then
    PYTHON_VERSION=$(orb -m "$VM_NAME" bash -c "python3.12 --version 2>/dev/null | cut -d' ' -f2")
    echo -e "${GREEN}✓${NC} Python installed: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Failed to install Python"
    exit 1
fi

# Step 5: Install Node.js 18
echo -e "${BLUE}[5/7]${NC} Installing Node.js 18..."

# Download Node.js setup script
if orb -m "$VM_NAME" bash -c "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - > /dev/null 2>&1"; then
    # Install Node.js
    if orb -m "$VM_NAME" bash -c "sudo apt install -y nodejs > /dev/null 2>&1"; then
        NODE_VERSION=$(orb -m "$VM_NAME" bash -c "node --version 2>/dev/null | tr -d 'v'")
        echo -e "${GREEN}✓${NC} Node.js installed: $NODE_VERSION"
    else
        echo -e "${RED}✗${NC} Failed to install Node.js package"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Failed to download Node.js setup script"
    exit 1
fi

# Step 6: Install Claude CLI
echo -e "${BLUE}[6/7]${NC} Installing Claude CLI..."

if orb -m "$VM_NAME" bash -c "sudo npm install -g @anthropic-ai/claude-code > /dev/null 2>&1"; then
    CLAUDE_VERSION=$(orb -m "$VM_NAME" bash -c "claude --version 2>&1 | head -n1" || echo "installed")
    echo -e "${GREEN}✓${NC} Claude CLI installed: $CLAUDE_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Claude CLI installation failed (non-critical)"
    echo "    You can install it manually later: sudo npm install -g @anthropic-ai/claude-code"
fi

# Install additional utilities
echo -e "${BLUE}[6.5/7]${NC} Installing utilities (rsync, git)..."
orb -m "$VM_NAME" bash -c "sudo apt install -y rsync git > /dev/null 2>&1" || true
echo -e "${GREEN}✓${NC} Utilities installed"

# Step 7: Create project directory
echo -e "${BLUE}[7/7]${NC} Creating project directory..."

if orb -m "$VM_NAME" bash -c "mkdir -p $PROJECT_DIR" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Directory created: $PROJECT_DIR"
else
    echo -e "${RED}✗${NC} Failed to create project directory"
    exit 1
fi

# Final verification
echo ""
echo "=== SETUP COMPLETE ==="
echo ""

# Check VM status
VM_STATUS=$(orb list | grep "$VM_NAME" | awk '{print $2}' || echo "unknown")
echo -e "VM Status: ${GREEN}$VM_STATUS${NC}"
echo "VM Name: $VM_NAME"
echo "Project Dir: $PROJECT_DIR"
echo "SSH Access: $VM_NAME@orb"
echo ""

echo "=== INSTALLED SOFTWARE ==="
orb -m "$VM_NAME" bash -c "docker --version" 2>/dev/null || echo "Docker: Not found"
orb -m "$VM_NAME" bash -c "python3.12 --version" 2>/dev/null || echo "Python: Not found"
orb -m "$VM_NAME" bash -c "node --version" 2>/dev/null || echo "Node.js: Not found"
orb -m "$VM_NAME" bash -c "claude --version 2>&1 | head -n1" 2>/dev/null || echo "Claude CLI: Not found"

echo ""
echo "=== NEXT STEPS ==="
echo ""
echo "1. Sync code to VM:"
echo "   rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' \\"
echo "     ./ $VM_NAME@orb:$PROJECT_DIR/"
echo ""
echo "2. Copy .env file to VM:"
echo "   scp .env $VM_NAME@orb:$PROJECT_DIR/.env"
echo ""
echo "3. Set up Python venv in VM:"
echo "   orb -m $VM_NAME bash -c \"cd $PROJECT_DIR && python3.12 -m venv .venv\""
echo "   orb -m $VM_NAME bash -c \"cd $PROJECT_DIR && source .venv/bin/activate && pip install -e .\""
echo ""
echo "4. Start Ray cluster:"
echo "   just orb-start"
echo ""

exit 0
