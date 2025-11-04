---
name: vm-setup
description: Create and configure OrbStack Linux VM for Ray cluster (macOS only)
---

# VM Setup Skill

Creates and configures an OrbStack Linux VM with all required dependencies for running Ray cluster with containerized actors.

## When to Use

- During `/cc-setup` on macOS systems
- When Ray cluster needs to run in Linux environment
- After OrbStack installation to set up VM

## Platform

**macOS only** - This skill is not needed on Linux (Docker works natively)

## What It Does

1. Creates Ubuntu 24.04 VM named `ray-cluster` via OrbStack
2. Installs system dependencies in VM:
   - Docker (for container runtime)
   - Python 3.12 (for Ray and Kodosumi)
   - Node.js 18 (for Claude CLI)
   - rsync (for syncing code from macOS)
   - git (for repository operations)
3. Installs Claude Code CLI in VM
4. Configures Docker permissions (adds user to docker group)
5. Creates project directory structure
6. Verifies all installations

## Execution

```bash
bash .claude/skills/vm-setup/scripts/setup-vm.sh
```

## Prerequisites

- OrbStack must be installed and running
- Script must be run from macOS host (not inside VM)

## Output Format

```
=== ORBSTACK VM SETUP ===
[1/7] Creating Ubuntu VM 'ray-cluster'...
✓ VM created successfully

[2/7] Waiting for VM to start...
✓ VM is running

[3/7] Installing Docker...
✓ Docker installed: 24.0.7

[4/7] Installing Python 3.12...
✓ Python installed: 3.12.9

[5/7] Installing Node.js 18...
✓ Node.js installed: 18.20.0

[6/7] Installing Claude CLI...
✓ Claude CLI installed: 1.0.0

[7/7] Creating project directory...
✓ Directory created: ~/dev/cc-hitl-template

=== SETUP COMPLETE ===
VM Status: Running
VM Name: ray-cluster
Project Dir: ~/dev/cc-hitl-template
SSH Access: ray-cluster@orb

Next steps:
1. Sync code to VM: rsync -av ./ ray-cluster@orb:~/dev/cc-hitl-template/
2. Start Ray cluster: just orb-start
```

## Return Values

- **Exit Code 0**: VM setup successful
- **Exit Code 1**: VM creation or configuration failed

## Usage in Setup Agent

```bash
# Check if on macOS
if [ "$(uname -s)" = "Darwin" ]; then
    echo "Setting up OrbStack VM for Ray cluster..."

    if bash .claude/skills/vm-setup/scripts/setup-vm.sh; then
        echo "✅ VM setup complete"
        # Proceed with syncing code
    else
        echo "❌ VM setup failed"
        # Show troubleshooting steps
    fi
else
    echo "Skipping VM setup (not on macOS)"
fi
```

## VM Configuration

**VM Specifications** (defaults):
- Distribution: Ubuntu 24.04 LTS
- Name: ray-cluster
- CPU: Shared (adjustable via `orb config`)
- Memory: Default (adjustable via `orb config`)
- Network: Automatic port forwarding from macOS

**Installed Software**:
- Docker 24.0.7+
- Python 3.12+
- Node.js 18+
- Claude CLI
- rsync
- git

**Project Structure in VM**:
```
/home/user/
├── dev/
│   └── cc-hitl-template/  # Synced from macOS
│       ├── .venv/          # Created after sync
│       ├── .env            # Copied from macOS
│       └── ...
```

## Manual Alternative

If the skill fails, here are manual steps:

```bash
# 1. Create VM
orb create ubuntu:24.04 ray-cluster

# 2. Wait for VM to start
sleep 5
orb list | grep ray-cluster

# 3. Install dependencies
orb -m ray-cluster bash -c "sudo apt update"
orb -m ray-cluster bash -c "sudo apt install -y docker.io python3.12 python3.12-venv python3-pip rsync git"

# 4. Install Node.js
orb -m ray-cluster bash -c "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
orb -m ray-cluster bash -c "sudo apt install -y nodejs"

# 5. Install Claude CLI
orb -m ray-cluster bash -c "sudo npm install -g @anthropic-ai/claude-code"

# 6. Configure Docker permissions
orb -m ray-cluster bash -c "sudo usermod -aG docker \$USER"

# 7. Create project directory
orb -m ray-cluster bash -c "mkdir -p ~/dev/cc-hitl-template"
```

## Troubleshooting

### VM Creation Fails

```
Error: Failed to create VM
Solutions:
1. Check OrbStack is running
2. Check available disk space (need ~10GB)
3. Delete existing VM: orb delete ray-cluster
4. Restart OrbStack app
```

### Package Installation Fails

```
Error: apt install failed
Solutions:
1. Check internet connectivity
2. Retry: orb -m ray-cluster bash -c "sudo apt update"
3. Check VM disk space: orb -m ray-cluster bash -c "df -h"
```

### Node.js Installation Fails

```
Error: Node.js setup script failed
Solutions:
1. Check internet connectivity to deb.nodesource.com
2. Try alternative: orb -m ray-cluster bash -c "sudo snap install node --classic"
3. Or install from Ubuntu repo: sudo apt install nodejs (may be older version)
```

### Claude CLI Installation Fails

```
Error: npm install -g failed
Solutions:
1. Check Node.js is installed: orb -m ray-cluster bash -c "node --version"
2. Check npm is available: orb -m ray-cluster bash -c "npm --version"
3. Try without sudo: orb -m ray-cluster bash -c "npm install -g @anthropic-ai/claude-code"
```

## Notes

- VM setup takes ~5-10 minutes depending on internet speed
- OrbStack handles SSH keys automatically (no manual SSH setup needed)
- VM persists across OrbStack restarts
- Port forwarding is automatic (no manual configuration)
- VM can be accessed via: `orb -m ray-cluster` or `ssh ray-cluster@orb`
- VM disk is thin-provisioned (grows as needed)
