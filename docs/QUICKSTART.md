# Quick Start Guide

Get the Claude + Kodosumi HITL template running in 5 minutes.

## Which Setup is Right for You?

```
Are you on macOS?
├─ Yes → Use Claude Code Setup (recommended)
│         Autonomous setup with /cc-setup command
│
└─ No (Linux)
    ├─ Have Claude Code? → Use /cc-setup (automated)
    └─ No Claude Code? → Manual setup (see below)
```

---

## Option 1: Claude Code Setup (Recommended)

**Best for**: Everyone - fully automated, guided setup

### Steps

1. **Clone the repository**
   ```bash
   git clone <your-repo-url> cc-hitl-template
   cd cc-hitl-template
   ```

2. **Run setup in Claude Code**
   ```bash
   # In Claude Code CLI
   /cc-setup
   ```

3. **Follow the prompts**
   - Agent will check prerequisites
   - Guide you through installations if needed
   - Prompt for API keys (ANTHROPIC_API_KEY, GITHUB_TOKEN)
   - Set up OrbStack VM (macOS) or Docker (Linux)
   - Start all services automatically

4. **Access the application**
   - Open http://localhost:3370 in your browser
   - Navigate to "Claude HITL Template"
   - Start your first conversation!

**What the agent does for you**:
- ✅ Detects your OS and adjusts workflow
- ✅ Verifies all prerequisites
- ✅ Creates Python virtual environment
- ✅ Installs dependencies
- ✅ Configures .env with your API keys
- ✅ Sets up OrbStack VM (macOS only)
- ✅ Starts Ray cluster and Kodosumi services
- ✅ Validates everything is working

**Time to complete**: 10-15 minutes (most is downloads/installations)

---

## Option 2: Manual Setup

**For those who prefer control or don't have Claude Code**

### Prerequisites

See [SETUP.md](SETUP.md) for detailed prerequisites.

**Quick checklist**:
- Python 3.12+
- Node.js 18+
- Claude Code CLI
- **macOS**: OrbStack + Podman
- **Linux**: Docker

### macOS (Hybrid Setup)

```bash
# 1. Install prerequisites
brew install python@3.12 orbstack podman node@18
sudo npm install -g @anthropic-ai/claude-code

# 2. Create OrbStack VM
orb create ubuntu:24.04 ray-cluster

# 3. Follow detailed guide
```

See [ORBSTACK_SETUP.md](ORBSTACK_SETUP.md) for complete hybrid setup instructions.

### Linux (Native Setup)

```bash
# 1. Install prerequisites
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip docker.io nodejs
sudo npm install -g @anthropic-ai/claude-code

# 2. Create Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Start services
source .env && export ANTHROPIC_API_KEY
just start

# 5. Access application
# Open http://localhost:3370
```

---

## Verification

After setup, verify everything is running:

```bash
# Check Ray cluster
just orb-status  # macOS
ray status       # Linux

# Check Kodosumi services
ps aux | grep koco | grep -v grep

# Check ports
curl http://localhost:8265  # Ray Dashboard (should return HTML)
curl http://localhost:3370  # Admin Panel (should return HTML)
```

**Expected state**:
- ✅ Ray cluster running
- ✅ Ray Dashboard accessible at http://localhost:8265
- ✅ Kodosumi services running (koco spool, koco serve)
- ✅ Admin Panel accessible at http://localhost:3370

---

## Next Steps

### 1. Test Your First Conversation

1. Open http://localhost:3370
2. Navigate to "Claude HITL Template"
3. Enter a prompt: "Help me understand Ray Actors"
4. Click "Start Conversation"
5. Interact with Claude through the HITL interface

### 2. Learn the Daily Workflow

See [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md) for:
- Morning startup commands
- Development cycle (edit → deploy → test)
- Evening shutdown
- Quick reference commands

### 3. Deploy Changes

When you modify code:

**Using Claude Code**:
```bash
/cc-deploy  # Autonomous deployment with change detection
```

**Using justfile** (macOS):
```bash
just orb-deploy  # Sync code and redeploy
```

**Linux**:
```bash
koco deploy -r  # Redeploy to Ray cluster
```

---

## Troubleshooting Quick Fixes

### Services won't start

```bash
# macOS
just orb-down && just orb-up

# Linux
just stop && just start
```

### Port conflicts

```bash
# Check what's using the ports
lsof -i :8265
lsof -i :3370

# Kill conflicting processes
kill <PID>
```

### Ray connection errors

```bash
# Restart Ray cluster
just orb-restart  # macOS
ray stop && ray start --head  # Linux
```

### More help

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive error solutions.

---

## Architecture Overview

Quick understanding of the system:

```
User (Browser)
  ↓
Kodosumi Admin Panel (localhost:3370)
  ↓
Ray Serve Deployment (query.py)
  ↓
Ray Actor in Container (agent.py)
  ↓
Claude SDK Subprocess
  ↓
Anthropic API
```

**Key components**:
- **Kodosumi**: HITL framework + admin panel
- **Ray**: Distributed computing + actor lifecycle
- **Containers**: Isolation for Claude SDK sessions
- **OrbStack** (macOS): Linux VM for native container support

For deeper understanding, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Resources

- **Daily Workflow**: [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)
- **Full Setup Guide**: [SETUP.md](SETUP.md)
- **OrbStack Setup**: [ORBSTACK_SETUP.md](ORBSTACK_SETUP.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Reference**: [REFERENCE.md](REFERENCE.md)

---

**Having issues?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue on GitHub.
