# OrbStack Setup Guide: Hybrid Development

This guide shows you how to set up a hybrid development environment where:
- **Ray cluster runs in OrbStack Linux VM** (native Linux networking)
- **Development happens on macOS** (your IDE, code, git workflow)
- **Connection via Ray Client** (automatic port forwarding)

## Why This Approach?

Ray's `image_uri` runtime environment feature uses `--network=host` which only works correctly on native Linux. On macOS, Podman runs containers in a QEMU VM where `127.0.0.1` doesn't map to the macOS host, breaking Ray's networking assumptions.

**Hybrid approach benefits:**
- Native Linux Ray cluster (containers work as designed)
- macOS development experience (familiar IDE, tools)
- Lightweight (OrbStack uses <0.1% CPU in background)
- Automatic port forwarding (no manual networking)
- Git workflow stays on macOS (no sync issues)

## Prerequisites

- macOS 12.0+ (Monterey or later)
- Homebrew installed
- Python 3.12+ installed on macOS (for development)
- Docker Desktop NOT running (OrbStack replaces it)

## Quick Setup Option

**Prefer guided setup?** Run `/cc-setup` in Claude Code first. It will:
1. Analyze your macOS system
2. Create a todo list of required steps
3. Guide you through each step below with approvals

The manual instructions below explain what `/cc-setup` does behind the scenes.

---

## Installation

### 1. Install OrbStack

```bash
# Install via Homebrew
brew install orbstack

# Or download from https://orbstack.dev
```

### 2. Create Ubuntu VM for Ray

```bash
# Create Ubuntu 24.04 VM named 'ray-cluster'
orb create ubuntu:24.04 ray-cluster

# Verify VM is running
orb list
```

### 3. Install System Dependencies in VM

```bash
# Enter the VM
orb shell ray-cluster

# Update package list
sudo apt update

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install container runtime (Docker OR Podman - choose one)

# Option 1: Docker (simpler, works out of the box)
sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker

# Option 2: Podman (daemonless, rootless, better security)
# sudo apt install -y podman
# Note: Requires user namespace configuration (see below)

# Install Node.js 18 (required for Claude CLI)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
python3.12 --version
docker --version  # or: podman --version
node --version
```

**Note:** Ubuntu 24.04 implements PEP 668 which prevents system-wide pip installations. We'll create a virtual environment in the next step.

#### 3.1 Podman Configuration (If Using Podman)

**If you chose Podman**, you must configure user namespaces for rootless containers:

```bash
# Still in VM (orb shell ray-cluster)

# Configure subordinate UID/GID ranges
# Format: username:start_uid:count
sudo bash -c 'echo "sebkuepers:100000:65536" >> /etc/subuid'
sudo bash -c 'echo "sebkuepers:100000:65536" >> /etc/subgid'

# Apply configuration
podman system migrate

# Verify configuration
cat /etc/subuid  # Should show: sebkuepers:100000:65536
cat /etc/subgid  # Should show: sebkuepers:100000:65536

# Test podman works
podman run --rm hello-world
```

**Why this is needed:**
- Rootless podman requires subordinate UID/GID mapping
- Container runs as `ray` user (UID 1000) inside
- Host user is `sebkuepers` (UID 501)
- Mapping allows podman to use UIDs 100000-165535 for container processes

**For detailed troubleshooting:** See [Container Runtime Issues](TROUBLESHOOTING.md#container-runtime-issues)

### 4. Clone Repository and Setup

```bash
# Still in OrbStack VM shell

# Clone your repository
git clone <your-repo-url> cc-hitl-template
cd cc-hitl-template

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Install Claude CLI globally
sudo npm install -g @anthropic-ai/claude-code

# Verify Claude CLI
claude --version
```

### 5. Configure Environment

```bash
# Still in VM

# Copy example config
cp .env.example .env

# Edit .env and add your API key
nano .env  # or vim/vi

# Load environment
source .env
export ANTHROPIC_API_KEY
```

### 6. Build Container Image

```bash
# Still in VM

# Build the Docker image
docker build -t claude-hitl-worker:latest .

# Verify image
docker images | grep claude-hitl-worker
```

### 7. Start Ray Cluster

```bash
# Still in VM

# Start Ray head node with dashboard enabled
ray start --head --disable-usage-stats --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265

# Verify cluster
ray status
```

OrbStack automatically forwards ports from the VM to macOS, so Ray's services are accessible at `localhost` on your Mac:
- Ray Dashboard: http://localhost:8265
- Ray GCS: localhost:6379
- Ray Client: localhost:10001

### 8. Access Ray Dashboard

Once Ray is started, you can access the Ray Dashboard from your macOS browser:

**Primary URL**: http://localhost:8265

**Alternative URL**: http://ray-cluster.orb.local:8265

The dashboard provides:
- Cluster overview and resource usage
- Actor instances and their status
- Job monitoring
- Logs and metrics
- Task execution traces

**Note**: OrbStack's automatic port forwarding makes the dashboard accessible without any manual configuration. The `--dashboard-host=0.0.0.0` flag ensures the dashboard listens on all interfaces, allowing the port forward to work.

## Development Workflow

**First time setup?** Complete the installation steps above or run `/cc-setup` for guided setup.

### Quick Daily Workflow (Recommended)

The simplest way to work with OrbStack is using the justfile commands. All commands run from macOS and control the VM automatically.

See [Daily Workflow Guide](DAILY_WORKFLOW.md) for detailed instructions.

**Morning startup:**
```bash
# On macOS - start everything with one command
just orb-up
```

**During development:**
```bash
# Edit code on macOS with your IDE
# Then sync and redeploy:
just orb-deploy
```

**End of day:**
```bash
just orb-down
```

### Available OrbStack Commands

All commands are available via `just` and run from your macOS terminal:

| Command | Purpose |
|---------|---------|
| `just orb-up` | Complete startup: Ray + deploy + services |
| `just orb-down` | Complete shutdown |
| `just orb-deploy` | Sync code and redeploy application |
| `just orb-start` | Start Ray cluster only |
| `just orb-stop` | Stop Ray cluster |
| `just orb-services` | Start Kodosumi services (spooler + admin) |
| `just orb-status` | Check VM and Ray status |
| `just orb-logs` | View Kodosumi logs |
| `just orb-restart` | Restart Ray cluster |
| `just orb-shell` | SSH into VM |

### Traditional Workflow (Manual)

If you prefer manual control:

**On macOS:**
1. Keep code on macOS - Use your favorite IDE, git workflow stays normal
2. Create Python environment for local type checking:
   ```bash
   cd /path/to/cc-hitl-template
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

**Sync code to VM:**
```bash
rsync -av --exclude='.venv' --exclude='__pycache__' \
  /path/to/cc-hitl-template/ \
  ray-cluster.orb.local:~/cc-hitl-template/
```

**Deploy manually in VM:**
```bash
orb shell ray-cluster
cd cc-hitl-template
source .venv/bin/activate
source .env
export ANTHROPIC_API_KEY
koco deploy -r
koco spool &
koco serve --register http://localhost:8001/-/routes
```

## Architecture

```
┌─────────────────────────────────────────┐
│ macOS (Development)                     │
│ - IDE (VSCode, PyCharm, etc.)           │
│ - Git workflow                          │
│ - Code editing                          │
│ - Ray Client: ray.init("ray://...")     │
└────────────┬────────────────────────────┘
             │ Port forwarding (automatic)
             │ localhost:10001 → VM:10001
             │ localhost:6379 → VM:6379
             ▼
┌─────────────────────────────────────────┐
│ OrbStack Linux VM (ray-cluster)         │
│ ┌─────────────────────────────────────┐ │
│ │ Ray Cluster (Head Node)             │ │
│ │ - GCS: 0.0.0.0:6379                 │ │
│ │ - Ray Client Server: 0.0.0.0:10001  │ │
│ └────────────┬────────────────────────┘ │
│              │                           │
│              ▼                           │
│ ┌─────────────────────────────────────┐ │
│ │ ClaudeSessionActor (Ray Actor)      │ │
│ │ - use_container=True                │ │
│ │ - Runtime: claude-hitl-worker:latest│ │
│ └────────────┬────────────────────────┘ │
│              │                           │
│              ▼                           │
│ ┌─────────────────────────────────────┐ │
│ │ Podman Container                    │ │
│ │ - Native Linux networking           │ │
│ │ - 127.0.0.1 works correctly         │ │
│ │ - Claude SDK subprocess             │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Kodosumi Services                   │ │
│ │ - Spooler: localhost:8001           │ │
│ │ - Admin Panel: localhost:3370       │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Container Isolation

The hybrid approach preserves the container isolation benefits:

**Why containers?**
- Isolate `.claude/` configurations between instances
- Reproducible execution environment
- Multiple independent Claude sessions

**How it works:**
1. **template_user/.claude/** - Baked into Docker image (generic template behavior)
2. **project .claude/** - From deployed code directory (project-specific config)
3. **Merged via** - `ClaudeAgentOptions(setting_sources=["user", "project", "local"])`

See `claude_hitl_template/agent.py:268-323` for container configuration details.

## OrbStack Tips

### Port Access from macOS

OrbStack automatically forwards ports. Access services at:
- Ray GCS: `localhost:6379`
- Ray Client: `localhost:10001`
- Kodosumi Spooler: `localhost:8001`
- Admin Panel: `localhost:3370`

Or use the `.orb.local` domain:
- `http://ray-cluster.orb.local:3370`

### File Sharing

**Option 1: rsync** (Manual sync)
```bash
# From macOS
rsync -av --exclude='.venv' \
  /path/to/cc-hitl-template/ \
  ray-cluster.orb.local:~/cc-hitl-template/
```

**Option 2: OrbStack Sync** (Automatic)
Enable in OrbStack preferences → Machines → ray-cluster → Shared Folders

**Option 3: Git workflow** (Recommended)
```bash
# On macOS: commit and push
git add .
git commit -m "Changes"
git push

# In VM: pull
orb shell ray-cluster
cd cc-hitl-template
git pull
```

### Resource Allocation

OrbStack VMs are lightweight by default. For Ray cluster, consider:

```bash
# Adjust VM resources (example: 4 CPUs, 8GB RAM)
orb config ray-cluster --cpus 4 --memory 8G
```

### Starting/Stopping VM

```bash
# Stop VM (preserves state)
orb stop ray-cluster

# Start VM
orb start ray-cluster

# Restart VM
orb restart ray-cluster

# Delete VM (destructive!)
orb delete ray-cluster
```

## Troubleshooting

This guide covered the hybrid macOS + OrbStack VM setup. For detailed troubleshooting:

**Common issues:**
- **Container runtime errors** → See [Container Runtime Issues](TROUBLESHOOTING.md#container-runtime-issues)
- **Podman user namespace** → See [User Namespace Configuration](TROUBLESHOOTING.md#user-namespace-configuration-for-rootless-podman)
- **Permission errors** → See [Permission Issues: /tmp/ray](TROUBLESHOOTING.md#permission-issues-tmpray-file-locking)
- **Ray connection refused** → See [Ray Connection Refused](TROUBLESHOOTING.md#ray-connection-refused)
- **Port conflicts** → See [Port Already in Use](TROUBLESHOOTING.md#port-already-in-use)
- **Container image not found** → See [Container Image Digests](TROUBLESHOOTING.md#container-image-digests-local-vs-registry)
- **Code changes not reflected** → See [Code Changes Not Reflected](TROUBLESHOOTING.md#code-changes-not-reflected)

**Quick fixes:**

```bash
# Clean restart
just stop && just start

# Fix /tmp/ray permissions (for containerized actors)
orb -m ray-cluster bash -c "sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"

# Check status
orb list | grep ray-cluster  # VM status
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray status"  # Ray status
```

For comprehensive troubleshooting: **[docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

## Alternative: Linux Native Environment

If you prefer fully native Linux development (no hybrid setup):

### Option 1: Develop Entirely in OrbStack VM

```bash
# SSH into VM
orb shell ray-cluster

# Install your IDE tools (vim, emacs, or VS Code Server)
# All development happens here
```

Access code via:
- Terminal IDE (vim/emacs)
- VS Code Remote SSH (connect to `ray-cluster.orb.local`)
- OrbStack's built-in VS Code integration

### Option 2: Remote Ray Cluster

If you have access to a remote Linux machine or cloud VM:

```bash
# On remote Linux machine
ray start --head --disable-usage-stats --ray-client-server-port=10001

# On macOS
ray.init("ray://<remote-ip>:10001")
```

## Summary

**Hybrid approach workflow:**
1. Code on macOS with your favorite IDE
2. Sync code to OrbStack VM (rsync or git)
3. Ray cluster runs in Linux VM (native networking)
4. Connect from macOS via `ray.init("ray://localhost:10001")`
5. Containers work correctly with `127.0.0.1`
6. Admin panel accessible from macOS browser

**Best for:**
- macOS developers who want Linux Ray clusters
- Teams with mixed macOS/Linux environments
- Local development with production-like containers
- Avoiding dual-boot or heavy VMs

**Resource usage:**
- OrbStack: <0.1% CPU when idle
- Ray cluster: ~100-200MB base memory
- Containers: 1GB per active conversation (actor)

For questions or issues, see main README.md or CLAUDE.md documentation.
