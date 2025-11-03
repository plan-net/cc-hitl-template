# Setup Guide

Comprehensive guide for installing all prerequisites for the Claude + Kodosumi HITL template.

## Quick Setup

**Prefer guided setup?** Use the `/cc-setup` command in Claude Code - it analyzes your system, creates a comprehensive todo list, and guides you through each step with individual approvals.

This guide is for manual installation or understanding what `/cc-setup` does behind the scenes.

---

## Prerequisites Overview

### All Platforms

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Ray, Kodosumi, application runtime |
| Node.js | 18+ | Required for Claude Code CLI |
| Claude Code CLI | Latest | Claude Agent SDK interface |
| Git | Any recent | Repository operations |

### macOS Specific

| Software | Version | Purpose |
|----------|---------|---------|
| Homebrew | Latest | Package manager for macOS |
| Podman | Latest | Building Docker images on macOS |
| OrbStack | Latest | Linux VM for Ray cluster |

**Why OrbStack on macOS?** Ray's container networking requires native Linux. See [ARCHITECTURE.md](ARCHITECTURE.md#why-macos-needs-orbstack) for details.

### Linux Specific

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20.10+ | Container runtime (native Linux support) |

---

## Installation Instructions

### macOS Setup

#### 1. Install Homebrew (if not installed)

```bash
# Check if Homebrew is installed
brew --version

# Install if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install System Dependencies

```bash
# Install all prerequisites via Homebrew
brew install python@3.12 orbstack podman node@18 git

# Verify installations
python3.12 --version  # Should be 3.12.x
node --version        # Should be v18.x or higher
podman --version      # Should show version
orb version          # Should show OrbStack version
git --version        # Should show git version
```

#### 3. Install Claude Code CLI

```bash
# Install globally via npm
sudo npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

#### 4. Start OrbStack

```bash
# Open OrbStack application
open -a OrbStack

# Verify it's running
orb list
```

**Note**: OrbStack must be running before creating VMs.

---

### Linux Setup (Ubuntu/Debian)

#### 1. Update Package Lists

```bash
sudo apt update
```

#### 2. Install Python 3.12

```bash
# Install Python 3.12 and venv
sudo apt install -y python3.12 python3.12-venv python3-pip

# Verify installation
python3.12 --version  # Should be 3.12.x
```

#### 3. Install Docker

```bash
# Install Docker
sudo apt install -y docker.io

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Apply group changes (logout and login, or use newgrp)
newgrp docker

# Verify installation
docker --version
docker ps  # Should not require sudo
```

**Important**: Logout and login again for docker group membership to take effect.

#### 4. Install Node.js 18

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# Install Node.js
sudo apt install -y nodejs

# Verify installation
node --version  # Should be v18.x or higher
npm --version   # Should show npm version
```

#### 5. Install Claude Code CLI

```bash
# Install globally via npm
sudo npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

#### 6. Install Git (if not installed)

```bash
sudo apt install -y git
git --version
```

---

### Linux Setup (Fedora/RHEL/CentOS)

#### Python 3.12

```bash
sudo dnf install -y python3.12 python3.12-pip
```

#### Docker

```bash
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Node.js 18

```bash
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install -y nodejs
```

#### Claude CLI

```bash
sudo npm install -g @anthropic-ai/claude-code
```

---

## Project Setup

After installing prerequisites, set up the project:

### 1. Clone Repository

```bash
git clone <your-repo-url> cc-hitl-template
cd cc-hitl-template
```

### 2. Create Python Virtual Environment

```bash
# Create venv with Python 3.12
python3.12 -m venv .venv

# Activate venv
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate  # Windows

# Verify activation (should show .venv path)
which python
```

### 3. Install Python Dependencies

```bash
# Install project in editable mode
pip install -e .

# Verify installation
pip list | grep ray
pip list | grep kodosumi
pip list | grep claude-agent-sdk
```

Expected packages:
- ray ~= 2.51.1
- kodosumi ~= 1.0.0
- claude-agent-sdk ~= 0.1.6

---

## Configuration

### 1. Create .env File

```bash
# Copy template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` and add your values:

```bash
# Required: Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-...your-key-here...

# Required for building images: GitHub Container Registry
GITHUB_TOKEN=ghp_...your-token-here...
GITHUB_USERNAME=your-github-username

# Optional: Configuration repositories
MASTER_CONFIG_REPO=git@github.com:your-org/cc-master-agent-config.git
PROJECT_CONFIG_REPO=git@github.com:your-org/cc-example-agent-config.git
```

#### Getting Your API Keys

**Anthropic API Key**:
1. Visit https://console.anthropic.com/settings/keys
2. Create a new API key
3. Copy and paste into .env

**GitHub Token** (for building Docker images):
1. Visit https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Select scopes:
   - `write:packages` (push images to ghcr.io)
   - `read:packages` (pull private images)
4. Generate and copy token
5. Paste into .env

**GitHub Username**:
- Your GitHub username (used in image registry path: `ghcr.io/<username>/claude-hitl-worker`)

### 3. Load Environment

```bash
# Source .env to make variables available
source .env

# Verify (should show first 10 characters)
echo "API Key: ${ANTHROPIC_API_KEY:0:10}..."
echo "GitHub User: $GITHUB_USERNAME"
```

---

## Platform-Specific Setup

### macOS: OrbStack VM Setup

After installing OrbStack, create a Linux VM for Ray cluster:

**Guided (recommended)**:
```bash
# In Claude Code
/cc-setup  # Analyzes system and guides VM creation with approvals
```

**Manual**:
See [ORBSTACK_SETUP.md](ORBSTACK_SETUP.md) for complete instructions.

**Quick manual setup**:
```bash
# Create Ubuntu VM
orb create ubuntu:24.04 ray-cluster

# Wait for VM to start
sleep 5

# Verify VM is running
orb list | grep ray-cluster
```

### Linux: Docker Verification

```bash
# Verify Docker is working without sudo
docker ps

# If it requires sudo, check group membership
groups | grep docker

# If docker group is missing, add and re-login
sudo usermod -aG docker $USER
# Logout and login again
```

---

## Verification

### Check All Prerequisites

Run the prerequisite check skill:

```bash
bash .claude/skills/prerequisite-check/check.sh
```

Expected output:
```
=== PREREQUISITE CHECK ===
[✓] Python 3.12+: 3.12.9 installed
[✓] Git: 2.45.0 installed
[✓] Node.js 18+: 18.20.0 installed
[✓] Claude CLI: 1.0.0 installed
[✓] Homebrew: 4.2.0 installed (macOS)
[✓] Podman: 5.0.0 installed (macOS)
[✓] OrbStack: 1.5.0 installed (macOS)

=== SUMMARY ===
Status: COMPLETE
All prerequisites are installed and ready!
```

### Test Python Environment

```bash
# Activate venv
source .venv/bin/activate

# Check Ray
python -c "import ray; print(f'Ray version: {ray.__version__}')"

# Check Kodosumi
python -c "import kodosumi; print('Kodosumi imported successfully')"

# Check Claude SDK
python -c "from claude_agent_sdk import ClaudeSDKClient; print('Claude SDK imported successfully')"
```

---

## Next Steps

### Option 1: Guided Full Setup

```bash
# In Claude Code - analyzes and guides through everything
/cc-setup
```

**What happens during `/cc-setup`**:

1. **Analysis Phase** (Sub-agent):
   - Detects your OS (macOS/Linux)
   - Checks which prerequisites are met vs missing
   - Reads previous setup state if exists
   - Creates comprehensive TodoWrite list

2. **Execution Phase** (Main agent):
   - Reviews todo list with you
   - Executes each pending item with your approval
   - Updates todo status in real-time
   - Validates each step before moving on

This gives you full visibility and control over what gets installed.

### Option 2: Manual Setup

**macOS**:
1. Follow [ORBSTACK_SETUP.md](ORBSTACK_SETUP.md) for VM setup
2. Follow [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md) for starting services

**Linux**:
1. Start services: `just start`
2. Access admin panel: http://localhost:3370

---

## Troubleshooting

### Python 3.12 Not Found

**macOS**:
```bash
brew install python@3.12
# May need to link
brew link python@3.12
```

**Linux**:
```bash
# Add deadsnakes PPA for Ubuntu
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

### Node.js Version Too Old

```bash
# Check current version
node --version

# Upgrade to Node.js 18+
# macOS
brew upgrade node@18

# Linux
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### Claude CLI Not Found After Installation

```bash
# Check npm global bin directory is in PATH
echo $PATH | grep npm

# Find where npm installs global packages
npm config get prefix

# Add to PATH if needed (macOS/Linux)
export PATH="$(npm config get prefix)/bin:$PATH"

# Add to your shell profile for persistence
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.zshrc  # or ~/.bashrc
```

### Docker Permission Denied (Linux)

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Check group membership
groups | grep docker

# If group shows but still fails, logout and login
# OR refresh group membership
newgrp docker

# Test
docker ps
```

### OrbStack Not Starting (macOS)

1. Quit OrbStack completely: `pkill -9 OrbStack`
2. Restart: `open -a OrbStack`
3. Wait 30 seconds for full startup
4. Test: `orb list`

---

## System Requirements

### Minimum Requirements

- **CPU**: 4 cores (2 cores minimum)
- **RAM**: 8GB (4GB absolute minimum)
- **Disk**: 10GB free space
- **Network**: Internet connection for:
  - Downloading dependencies
  - API calls to anthropic.com
  - Pulling container images

### Recommended Requirements

- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Disk**: 20GB+ free space (for Ray, containers, logs)
- **Network**: Broadband connection

### Resource Usage

- **Python venv**: ~500MB
- **Docker images**: ~2-3GB
- **Ray cluster**: ~200MB base + 1GB per concurrent conversation
- **OrbStack VM** (macOS): ~2GB disk, <0.1% CPU when idle

---

## Additional Resources

- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **OrbStack Setup**: [ORBSTACK_SETUP.md](ORBSTACK_SETUP.md)
- **Daily Workflow**: [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Need help?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue on GitHub.
