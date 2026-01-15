# Developer Environment Blueprint: macOS + OrbStack VM

> Authoritative guide for setting up a local development environment for Claude HITL agents
> Based on tested setup from VM_SETUP_BRIEFING.md (2025-12-17)

---

## Overview

This blueprint describes how to set up a complete development environment for Claude + Kodosumi HITL agents on macOS using OrbStack.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              macOS (Developer Machine)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────┐         ┌──────────────────────┐                 │
│   │  IDE / Editor        │         │  Claude Code CLI     │                 │
│   │  (VS Code, etc.)     │         │  /cc-deploy          │                 │
│   │                      │         │  /cc-setup           │                 │
│   └──────────────────────┘         └──────────────────────┘                 │
│              │                                │                              │
│              │ Edit code                      │ Build & Push                 │
│              ▼                                ▼                              │
│   ┌──────────────────────┐         ┌──────────────────────┐                 │
│   │  ~/git/cc-hitl-*     │         │  ghcr.io/<USER>/     │                 │
│   │  (Project Repo)      │ ──────► │  claude-hitl-worker  │                 │
│   └──────────────────────┘  rsync  └──────────────────────┘                 │
│                                               │                              │
└───────────────────────────────────────────────│──────────────────────────────┘
                                                │ podman pull
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OrbStack VM: ray-cluster                             │
│                         Ubuntu 24.04 (noble) ARM64                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   User: kodosumi (UID 1000) ◄── CRITICAL: Must match container UID          │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        systemd Services                              │   │
│   │                                                                      │   │
│   │   kodosumi-ray.service        → Ray Head Node (:6379, :8265)        │   │
│   │   kodosumi-koco-spool.service → Kodosumi Spooler                    │   │
│   │   kodosumi-koco-serve.service → Kodosumi Admin Panel (:3370)        │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Ray Serve Application                            │   │
│   │                                                                      │   │
│   │   Route: /feeling-check → claude_hitl_template.query:fast_app       │   │
│   │                                                                      │   │
│   │   ┌─────────────────┐   ┌─────────────────┐                         │   │
│   │   │  Podman         │   │  Podman         │                         │   │
│   │   │  Container      │   │  Container      │  ← One per HITL session │   │
│   │   │  (UID 1000)     │   │  (UID 1000)     │                         │   │
│   │   └─────────────────┘   └─────────────────┘                         │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Accessible Endpoints (from macOS)

| Service | URL | Purpose |
|---------|-----|---------|
| Ray Dashboard | http://localhost:8265 | Cluster monitoring |
| Ray Serve | http://localhost:8000 | Application API |
| Kodosumi Admin | http://localhost:3370 | HITL Admin Panel |

---

## Prerequisites (macOS Host)

- **OrbStack** installed ([orbstack.dev](https://orbstack.dev))
- **GitHub Token** with `read:packages` scope (for ghcr.io access)
- **Project repository** cloned: `~/git/cc-hitl-template`
- **Claude Code CLI** installed with plugins:
  - `claude-agent-sdk@cc-marketplace-developers` (provides `/cc-deploy`, `/cc-setup`)

---

## Phase 1: Create VM

```bash
# Create Ubuntu 24.04 ARM64 VM
orb create ubuntu:noble ray-cluster

# Verify
orb list
# Expected: ray-cluster running ubuntu noble arm64
```

---

## Phase 2: Install Base Software

```bash
# System update
orb -m ray-cluster bash -c "sudo apt-get update -qq"

# Python 3.12 tools
orb -m ray-cluster bash -c "sudo apt-get install -y python3.12-venv python3-pip"

# Podman (container runtime - used by Ray)
orb -m ray-cluster bash -c "sudo apt-get install -y podman"

# Node.js 18 (for Claude CLI)
orb -m ray-cluster bash -c "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"

# rsync + git
orb -m ray-cluster bash -c "sudo apt-get install -y rsync git"
```

---

## Phase 3: Create kodosumi Service User (UID 1000)

**CRITICAL**: The user MUST have UID 1000 to match container permissions!

```bash
# Create user with UID 1000
orb -m ray-cluster bash -c "sudo useradd -u 1000 -m -s /bin/bash kodosumi"

# Add to sudo group
orb -m ray-cluster bash -c "sudo usermod -aG sudo kodosumi"

# Verify
orb -m ray-cluster bash -c "id kodosumi"
# Expected: uid=1000(kodosumi) gid=1000(kodosumi) groups=1000(kodosumi),27(sudo)
```

### Why UID 1000?

| Context | User | UID |
|---------|------|-----|
| OrbStack VM (your Mac user) | zimmermannb | 1792997461 (mapped) |
| OrbStack VM (service user) | kodosumi | **1000** |
| Container (ray user) | ray | **1000** |

Without matching UIDs, containers cannot write to shared volumes like `/tmp/ray/`.

---

## Phase 4: Configure Podman for kodosumi

```bash
# Configure subuid/subgid for rootless Podman
orb -m ray-cluster bash -c "sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 kodosumi"

# Enable lingering (for systemd cgroups)
orb -m ray-cluster bash -c "sudo loginctl enable-linger kodosumi"
```

---

## Phase 5: Set Up Project Directory

```bash
# Create directory
orb -m ray-cluster bash -c "sudo mkdir -p /home/kodosumi/dev"

# Sync project from host (EXCLUDE .venv - wrong architecture!)
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.pyc' \
  ~/git/cc-hitl-template/ ray-cluster@orb:/home/kodosumi/dev/cc-hitl-template/

# Set ownership
orb -m ray-cluster bash -c "sudo chown -R kodosumi:kodosumi /home/kodosumi"
```

**IMPORTANT**: Never sync macOS `.venv` to VM - it contains wrong architecture binaries!

---

## Phase 6: Create Python venv + serve Symlink

```bash
# Create venv (as kodosumi)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && python3.12 -m venv .venv'"

# Install dependencies (including Ray 2.51.1)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install -e . sniffio ray==2.51.1 -q'"

# Install Kodosumi feature/candidate branch
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install git+https://github.com/masumi-network/kodosumi.git@feature/candidate -q'"

# Pin Ray version (kodosumi may pull newer version!)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install ray==2.51.1 -q'"

# Verify versions
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'source /home/kodosumi/dev/cc-hitl-template/.venv/bin/activate && ray --version && pip show kodosumi | grep Version'"
# Expected:
# ray, version 2.51.1
# Version: 1.1.0

# Create serve symlink (Kodosumi workaround)
orb -m ray-cluster bash -c "sudo chmod o+x /home/kodosumi && sudo chmod -R o+rX /home/kodosumi/dev"
orb -m ray-cluster bash -c "sudo ln -sf /home/kodosumi/dev/cc-hitl-template/.venv/bin/serve /usr/local/bin/serve"

# Verify symlink
orb -m ray-cluster bash -c "serve --help | head -1"
# Expected: Usage: serve [OPTIONS] COMMAND [ARGS]...
```

---

## Phase 7: Pull Container Image (as kodosumi)

**IMPORTANT**: For local development, use YOUR OWN container image, not `plan-net`!

```bash
# Set your credentials (from .env)
export GITHUB_USERNAME="your-github-username"
export GITHUB_TOKEN="ghp_your_token_here"

# Podman login
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'echo ${GITHUB_TOKEN} | podman login ghcr.io -u ${GITHUB_USERNAME} --password-stdin'"

# Pull YOUR image (not plan-net!)
orb -m ray-cluster bash -c "sudo -u kodosumi podman pull ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker:latest"

# Verify
orb -m ray-cluster bash -c "sudo -u kodosumi podman images"
```

### Container Image Sources

| Scenario | Image Source | When to Use |
|----------|--------------|-------------|
| **Local Development** | `ghcr.io/<YOUR_USERNAME>/claude-hitl-worker` | Your own builds |
| **Team/Shared** | `ghcr.io/plan-net/claude-hitl-worker` | Pre-built team images |

---

## Phase 8: Create systemd Services

### 8.1 Ray Service

```bash
orb -m ray-cluster bash -c 'cat > /tmp/kodosumi-ray.service << EOF
[Unit]
Description=Ray Head Node Service
After=network.target

[Service]
User=kodosumi
WorkingDirectory=/home/kodosumi/dev/cc-hitl-template
Type=simple
Environment=RAY_LOG_TO_DRIVER=0
Environment=RAY_BACKEND_LOG_LEVEL=warning
ExecStart=/home/kodosumi/dev/cc-hitl-template/.venv/bin/ray start --head --port=6379 --dashboard-host=0.0.0.0 --block
ExecStop=/home/kodosumi/dev/cc-hitl-template/.venv/bin/ray stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/kodosumi-ray.service /etc/systemd/system/'
```

### 8.2 Koco Spool Service

```bash
orb -m ray-cluster bash -c 'cat > /tmp/kodosumi-koco-spool.service << EOF
[Unit]
Description=Kodosumi Spooler Service
After=kodosumi-ray.service
Requires=kodosumi-ray.service

[Service]
User=kodosumi
WorkingDirectory=/home/kodosumi/dev/cc-hitl-template
Type=simple
ExecStart=/home/kodosumi/dev/cc-hitl-template/.venv/bin/koco spool --block
ExecStop=/home/kodosumi/dev/cc-hitl-template/.venv/bin/koco spool --stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/kodosumi-koco-spool.service /etc/systemd/system/'
```

### 8.3 Koco Serve Service

```bash
orb -m ray-cluster bash -c 'cat > /tmp/kodosumi-koco-serve.service << EOF
[Unit]
Description=Kodosumi Serve Service
After=kodosumi-ray.service
Requires=kodosumi-ray.service

[Service]
User=kodosumi
WorkingDirectory=/home/kodosumi/dev/cc-hitl-template
Type=simple
ExecStart=/home/kodosumi/dev/cc-hitl-template/.venv/bin/koco serve --register http://localhost:8000/-/routes
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/kodosumi-koco-serve.service /etc/systemd/system/'
```

### 8.4 Enable Services

```bash
orb -m ray-cluster bash -c "sudo systemctl daemon-reload && sudo systemctl enable kodosumi-ray kodosumi-koco-spool kodosumi-koco-serve"
```

---

## Phase 9: Start Services

```bash
# 1. Start Ray
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-ray"

# 2. Wait for Ray to be ready
sleep 5

# 3. Deploy application (MANUAL - not a service)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"

# 4. Start Koco services
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-koco-spool kodosumi-koco-serve"

# 5. Verify status
orb -m ray-cluster bash -c "sudo systemctl status kodosumi-ray kodosumi-koco-spool kodosumi-koco-serve --no-pager | grep -E '(●|○|Active)'"
```

**Expected Output:**
```
● kodosumi-ray.service - Ray Head Node Service
     Active: active (running)
● kodosumi-koco-spool.service - Kodosumi Spooler Service
     Active: active (running)
● kodosumi-koco-serve.service - Kodosumi Serve Service
     Active: active (running)
```

---

## Phase 10: Verification

### 10.1 Ray Dashboard
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8265
# Expected: 200
```

### 10.2 Ray Serve Routes
```bash
orb -m ray-cluster bash -c "curl -s http://localhost:8000/-/routes"
# Expected: {"/feeling-check":"claude_hitl_template"}
```

### 10.3 Kodosumi Admin Panel
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3370
# Expected: 401 (requires login - service is running)
```

### 10.4 Application Status
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'source /home/kodosumi/dev/cc-hitl-template/.venv/bin/activate && serve status'"
# Expected: applications with your deployment listed
```

---

## Phase 11: HITL Test (Container Mode)

```bash
# Start test request (from macOS host)
curl -X POST "http://localhost:8000/feeling-check" \
  -H "Content-Type: application/json" \
  -d '{"name":"Dev-Test","question":"Is everything working?"}'
```

### Check Running Containers
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi podman ps"
```

**Expected Output:**
```
CONTAINER ID  IMAGE                                              STATUS        NAMES
xxxxxxxx      ghcr.io/<USERNAME>/claude-hitl-worker:latest       Up X minutes  some_name
```

---

## Daily Operations

### Start All Services
```bash
just start
# Or manually:
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-ray"
sleep 5
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-koco-spool kodosumi-koco-serve"
```

### Stop All Services
```bash
just stop
# Or manually:
orb -m ray-cluster bash -c "sudo systemctl stop kodosumi-koco-serve kodosumi-koco-spool kodosumi-ray"
```

### Restart All Services (Clean)
```bash
orb -m ray-cluster bash -c "sudo systemctl stop kodosumi-koco-serve kodosumi-koco-spool kodosumi-ray"
orb -m ray-cluster bash -c "sudo rm -rf /tmp/ray"
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-ray"
sleep 5
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-koco-spool kodosumi-koco-serve"
```

### Sync Code Changes
```bash
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.pyc' \
  ~/git/cc-hitl-template/ ray-cluster@orb:/home/kodosumi/dev/cc-hitl-template/
```

### Redeploy Application (After Code Changes)
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"
```

### Update Kodosumi (Without Ray Restart)
```bash
# Update Kodosumi
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install --force-reinstall git+https://github.com/masumi-network/kodosumi.git@feature/candidate -q'"

# Pin Ray version (kodosumi may override!)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install ray==2.51.1 -q'"

# Restart Koco services only
orb -m ray-cluster bash -c "sudo systemctl restart kodosumi-koco-spool kodosumi-koco-serve"
```

---

## Troubleshooting

### Check Service Logs
```bash
orb -m ray-cluster bash -c "sudo journalctl -u kodosumi-ray -n 50 --no-pager"
orb -m ray-cluster bash -c "sudo journalctl -u kodosumi-koco-spool -n 50 --no-pager"
orb -m ray-cluster bash -c "sudo journalctl -u kodosumi-koco-serve -n 50 --no-pager"
```

### Check Ray Logs
```bash
orb -m ray-cluster bash -c "tail -50 /tmp/ray/session_latest/logs/serve/controller*.log"
```

### Check Container Logs
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi podman logs <container_name>"
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `applications: {}` | App not deployed | Run `serve deploy` command |
| Containers exit immediately | UID mismatch | Verify kodosumi is UID 1000 |
| `Permission denied` on /tmp/ray | Wrong ownership | `sudo chown -R 1000:1000 /tmp/ray` |
| `manifest unknown` | Wrong image digest | Use registry digest, not local |
| `serve: command not found` | Missing symlink | Create symlink to venv/bin/serve |

---

## Key Insights

1. **UID 1000 is critical** - Container runs as `ray` (UID 1000), VM services must also use UID 1000
2. **`--block` flag** - Ray and koco spool need `--block` for systemd Type=simple
3. **Podman rootless** - Storage is per-user isolated; kodosumi needs its own image pull
4. **RAY_CONTAINER_RUNTIME ignored** - Ray always uses Podman on this system
5. **Application deployment** - Must be done manually after Ray starts (not a service)
6. **Kodosumi feature/candidate** - Use `git+https://github.com/masumi-network/kodosumi.git@feature/candidate`
7. **Pin Ray version** - Always run `pip install ray==2.51.1` after kodosumi install
8. **serve symlink** - Kodosumi expects `serve` in PATH → symlink to `/usr/local/bin/serve`
9. **Never sync .venv** - macOS venv has wrong architecture for Linux VM

---

## Version Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Ubuntu | 24.04 (noble) | ARM64 for Apple Silicon |
| Python | 3.12 | Required by Kodosumi |
| Ray | 2.51.1 | Must be pinned! |
| Kodosumi | 1.1.0 | feature/candidate branch |
| Node.js | 18.x | For Claude CLI |
| Podman | (system) | Rootless mode |

---

## Related Documentation

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed problem solutions
- [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md) - Day-to-day development tasks
- [PLUGINS.md](PLUGINS.md) - Plugin system documentation
- [DEPENDENCY-MANAGEMENT.md](DEPENDENCY-MANAGEMENT.md) - Container dependencies

---

**Last Updated**: 2025-01-14
**Based On**: VM_SETUP_BRIEFING.md (2025-12-17)
**Status**: Production-ready for macOS development
