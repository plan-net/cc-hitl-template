# Claude + Kodosumi HITL Template

A production-ready template demonstrating how to integrate **Claude Agent SDK** with **Kodosumi's Human-in-the-Loop (HITL)** functionality using **mandatory containerized execution** for security and configuration isolation.

## Status

**Fully Functional** ✅

This template is production-ready with containerized Ray Actor-based Claude SDK integration.

**Features:**
- ✅ Mandatory container isolation for security and configuration management
- ✅ Claude Agent SDK integration via Ray Actors in containers
- ✅ Persistent conversation sessions across HITL interactions
- ✅ Kodosumi service deployment with Ray Serve
- ✅ GitHub Container Registry workflow for image distribution
- ✅ Back-and-forth conversation with timeout detection
- ✅ Proper subprocess lifecycle management

**Known Limitations:**
- ⚠️ SDK Bug: `connect(prompt_string)` broken in v0.1.6 - we use `connect(None) + query()` pattern
- ⚠️ macOS requires OrbStack for proper container networking (see below)
- See [CLAUDE.md](CLAUDE.md#known-issues--workarounds) for details and workarounds

## Architecture Overview

This template implements a **containerized, multi-layered architecture** designed for security, isolation, and scalability:

```
┌─────────────────────────────────────────────────────────────────┐
│                    macOS Development Machine                     │
│  - IDE, git, source code                                        │
│  - Podman (builds images)                                       │
│  - Connects to Ray cluster via ray://localhost:10001            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ├─► Build & Push Images
                     │   └─► GitHub Container Registry (ghcr.io)
                     │
                     ▼ Connect to Ray Cluster
┌─────────────────────────────────────────────────────────────────┐
│          OrbStack Linux VM (or Native Linux Server)             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                    Ray Cluster                          │    │
│  │  - Ray Head Node (port 10001)                          │    │
│  │  - Ray GCS (Global Control Store)                      │    │
│  │  - Kodosumi Service (Ray Serve deployment)             │    │
│  └─────────────────┬──────────────────────────────────────┘    │
│                    │                                             │
│                    │ Spawns Ray Actors                          │
│                    ▼                                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │        ClaudeSessionActor (in Container)               │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Docker Container (MANDATORY)                    │  │    │
│  │  │  Image: ghcr.io/<user>/claude-hitl-worker       │  │    │
│  │  │                                                  │  │    │
│  │  │  ┌────────────────────────────────────────┐     │  │    │
│  │  │  │  Baked-in Configurations:              │     │  │    │
│  │  │  │  - /app/template_user/.claude/         │     │  │    │
│  │  │  │    (cc-master-agent-config)            │     │  │    │
│  │  │  │  - /app/project/.claude/               │     │  │    │
│  │  │  │    (cc-example-agent-config)           │     │  │    │
│  │  │  └────────────────────────────────────────┘     │  │    │
│  │  │                                                  │  │    │
│  │  │  ┌────────────────────────────────────────┐     │  │    │
│  │  │  │  Claude SDK Subprocess (Node.js)       │     │  │    │
│  │  │  │  - Claude Code CLI                     │     │  │    │
│  │  │  │  - Connects to api.anthropic.com       │     │  │    │
│  │  │  │  - Isolated execution environment      │     │  │    │
│  │  │  └────────────────────────────────────────┘     │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Kodosumi + Ray Serve**: Service deployment and HITL orchestration (query.py:276)
2. **Ray Actors in Containers**: Persistent session managers running in isolated containers (agent.py:282)
3. **Docker/Podman**: Container runtime providing mandatory isolation
4. **GitHub Container Registry**: Centralized image distribution with baked configurations
5. **Claude SDK**: AI conversation API running in sandboxed subprocess

### Data Flow

```
User Input
  ↓
Kodosumi Form (browser)
  ↓
Ray Serve Deployment (query.py)
  ↓
Ray Actor in Container (agent.py)
  ↓
Claude SDK Subprocess (Node.js CLI)
  ↓
Anthropic API (api.anthropic.com)
  ↓
Response ← ← ← ← ← (reverse flow)
```

### Reference Documentation

- **[Claude SDK Hosting Guide](https://docs.claude.com/en/api/agent-sdk/hosting)** - Official recommendations for containerized Claude SDK deployments
- **[Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html)** - Distributed serving framework
- **[Kodosumi Documentation](https://kodosumi.dev)** - HITL service framework

## Why Containers Are Mandatory

**This template requires containerized execution. This is not optional.**

### Security and Isolation Requirements

#### 1. Sandboxed Execution
- **Risk**: Claude SDK spawns subprocesses that can execute code and interact with the filesystem
- **Mitigation**: Containers provide process isolation, limiting blast radius
- **Benefit**: Even if Claude SDK is compromised, container boundaries prevent host access

#### 2. Configuration Isolation
- **Problem**: Multiple agents with different `.claude` configurations cannot coexist on bare metal
  - Template/user-level settings (cc-master-agent-config)
  - Project-specific settings (cc-example-agent-config)
  - Personal `~/.claude/` on host would interfere
  - Multiple projects would conflict
- **Solution**: Each container has its own isolated `.claude` folders baked into the image
  - `HOME=/app/template_user` → loads master config
  - Settings merge via `setting_sources=["user", "project", "local"]`
  - Complete isolation from host filesystem

#### 3. Credential Separation
- **Risk**: Claude SDK requires `ANTHROPIC_API_KEY` - leaking credentials is a critical security issue
- **Mitigation**: Containers enforce environment variable isolation
- **Benefit**: Each container gets its own credential scope, preventing cross-contamination

#### 4. Resource Limits
- **Problem**: Claude SDK conversations can be resource-intensive (CPU, memory)
- **Solution**: Containers enforce resource limits (1 CPU, 1GB RAM per actor)
- **Benefit**: Prevents resource exhaustion and ensures fair resource allocation

#### 5. Reproducibility
- **Problem**: "Works on my machine" syndrome
- **Solution**: Same Docker image everywhere = same behavior
- **Benefit**: Development, staging, and production use identical environments

#### 6. Auditability
- **Requirement**: Know exactly what code and configurations are running
- **Solution**: Image contents are version-controlled in git repos, image layers are immutable
- **Benefit**: Full audit trail of what runs in production

### How Container Isolation Works

```dockerfile
# Dockerfile excerpt showing isolation mechanism

# Build args for separate config repositories
ARG MASTER_CONFIG_PATH=template_user/.claude  # cc-master-agent-config
ARG PROJECT_CONFIG_PATH=project/.claude       # cc-example-agent-config

# Copy both config folders into image (baked-in, immutable)
COPY ${MASTER_CONFIG_PATH} /app/template_user/.claude
COPY ${PROJECT_CONFIG_PATH} /app/project/.claude

# Set HOME to template_user so "user" settings load from master config
ENV HOME=/app/template_user
```

```python
# agent.py excerpt showing Ray integration

runtime_env = RuntimeEnv(
    image_uri="ghcr.io/plan-net/claude-hitl-worker:latest",  # Pull from registry
    env_vars={
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        # HOME is set in Dockerfile to /app/template_user
    }
)

# Actor runs inside container with isolated configs
actor = ClaudeSessionActor.options(
    runtime_env=runtime_env,
    lifetime="detached",
    num_cpus=1,
    memory=1024 * 1024 * 1024  # 1GB limit enforced by container
).remote(cwd=actor_cwd)
```

## Why macOS Setup is Complex (and How We Solve It)

### The macOS Container Networking Challenge

**Problem**: Ray's `image_uri` feature requires native Linux container networking, which doesn't work correctly on macOS.

#### Technical Details

1. **Ray's Assumption**: Ray 2.51.1 assumes containers share the host's network namespace
   - Ray Head Node runs at `127.0.0.1:6379` (GCS address)
   - Ray passes this address to actors: `RAY_ADDRESS=127.0.0.1:6379`
   - Ray expects containers to reach GCS via localhost

2. **macOS Reality**: Podman on macOS uses a QEMU-based Linux VM
   - Containers run inside the VM with NAT networking
   - VM's `127.0.0.1` ≠ macOS host's `127.0.0.1`
   - Containers cannot reach Ray GCS at `127.0.0.1:6379`

3. **Result**: Container actors fail with networking errors
   ```
   ConnectionError: Failed to connect to GCS at 127.0.0.1:6379
   ```

4. **Containers Are Still Mandatory**: We can't just skip containers - security and isolation require them

### The Solution: OrbStack + Linux Ray Cluster

**OrbStack provides a lightweight Linux VM where Ray's container networking works as designed.**

#### Why OrbStack?

1. **Native Linux Environment**:
   - Full Ubuntu VM with native Linux kernel
   - Docker runs with proper Linux container networking
   - Ray's `127.0.0.1` assumptions hold true

2. **Lightweight**:
   - <0.1% CPU when idle
   - Fast startup (~2 seconds)
   - Minimal memory overhead

3. **Seamless Integration**:
   - Automatic port forwarding (localhost:10001 → VM Ray cluster)
   - Shared filesystem via virtfs
   - No manual network configuration needed

4. **Containers Work Correctly**:
   - **Mandatory** container isolation functions properly
   - `image_uri` actors can reach GCS
   - Production-like environment on macOS

#### The Hybrid Development Workflow

```
┌───────────────────────────────────────────────────────┐
│         macOS (Development Environment)               │
│  - IDE (VSCode, PyCharm, etc.)                       │
│  - Git repositories                                   │
│  - Podman (builds images)                            │
│  - Source code editing                               │
│  - ray.init("ray://localhost:10001")                 │
└─────────────────┬─────────────────────────────────────┘
                  │
                  │ Port forward: localhost:10001
                  ▼
┌───────────────────────────────────────────────────────┐
│      OrbStack Linux VM (Execution Environment)        │
│  - Ray cluster (head node on port 10001)             │
│  - Docker (pulls images from ghcr.io)                │
│  - Containerized Ray Actors                          │
│  - Claude SDK subprocesses                           │
└───────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Keep macOS development experience (IDE, git, all tools)
- ✅ **Mandatory containers work correctly** in Linux VM
- ✅ Production-like environment (Linux + Docker)
- ✅ Fast iteration cycle (edit on macOS → deploy to VM)
- ✅ No manual networking configuration

**Setup Guide**: See **[docs/ORBSTACK_SETUP.md](docs/ORBSTACK_SETUP.md)** for complete step-by-step setup.

### Linux Users: Direct Setup

If you're already on Linux, the **mandatory** container setup works directly without OrbStack:

1. Install Docker: `apt-get install docker.io` (Ubuntu/Debian)
2. Install Ray: `pip install ray[serve]`
3. Build images: `./build-and-push.sh --no-push` (local build)
4. Start Ray: `ray start --head`
5. Deploy: `koco deploy -r`

**Containers work out of the box on Linux** because Ray's networking assumptions are correct.

## GitHub Container Registry Workflow

This template uses **GitHub Container Registry (ghcr.io)** to distribute pre-built images with baked-in `.claude` configurations.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Separate Git Repositories (Private)                         │
│  ┌───────────────────────────┐  ┌──────────────────────────┐ │
│  │ cc-master-agent-config    │  │ cc-example-agent-config  │ │
│  │ (Template/user settings)  │  │ (Project-specific config)│ │
│  │                           │  │                          │ │
│  │ .claude/                  │  │ .claude/                 │ │
│  │   ├── settings.json       │  │   ├── settings.json      │ │
│  │   └── commands/           │  │   └── commands/          │ │
│  └───────────────────────────┘  └──────────────────────────┘ │
└──────────────┬───────────────────────┬───────────────────────┘
               │                       │
               └───────────┬───────────┘
                           │ Cloned during build
                           ▼
               ┌─────────────────────────┐
               │  build-and-push.sh      │
               │  (Build Script)         │
               │  - Clone both repos     │
               │  - Build Docker image   │
               │  - Push to ghcr.io      │
               └────────────┬────────────┘
                            │
                            ▼
               ┌─────────────────────────┐
               │  GitHub Container       │
               │  Registry (ghcr.io)     │
               │  ghcr.io/<user>/        │
               │  claude-hitl-worker     │
               └────────────┬────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌──────────────────┐       ┌──────────────────┐
    │  OrbStack VM     │       │  Production      │
    │  (Development)   │       │  (Ray Cluster)   │
    │  docker pull ... │       │  docker pull ... │
    └──────────────────┘       └──────────────────┘
```

### Fast Iteration Workflow

1. **Edit Configurations**: Update configs in separate git repos
   ```bash
   cd ~/repos/cc-master-agent-config
   vim .claude/settings.json
   git commit -am "Update template settings"
   git push
   ```

2. **Build and Push Image**: Run build script on macOS
   ```bash
   cd ~/dev/cc-hitl-template
   ./build-and-push.sh
   ```
   - Script clones both config repos locally
   - Builds image with Podman
   - Pushes to `ghcr.io/plan-net/claude-hitl-worker:latest`

3. **Deploy to Ray Cluster**: Redeploy with new image
   ```bash
   koco deploy -r  # Ray pulls new image from ghcr.io
   ```

4. **Test**: Verify new configurations are active

**Total iteration time: ~2-3 minutes** (clone + build + push + deploy)

### Build Script Features

```bash
./build-and-push.sh [OPTIONS]

Options:
  -u, --username <name>     GitHub username (default: from git config)
  -t, --tag <tag>          Image tag (default: latest)
  -m, --master <repo>      Master config repo (default: cc-master-agent-config)
  -p, --project <repo>     Project config repo (default: cc-example-agent-config)
  --no-push                Build only, don't push to registry
  -h, --help               Show this help message
```

### Authentication Setup

**Required**: GitHub Personal Access Token (PAT) with `packages:write` scope

1. Create PAT: https://github.com/settings/tokens
2. Scopes needed:
   - `write:packages` - Push images to ghcr.io
   - `read:packages` - Pull private images
3. Add to `.env`:
   ```bash
   GITHUB_TOKEN=ghp_...your-token-here...
   GITHUB_USERNAME=your-github-username
   ```

**Why separate from git SSH?**
- Git operations use SSH keys ✅
- Container registry uses token authentication ❌
- Different auth mechanisms for different services

## Prerequisites

### Required Software

#### Container Runtime
- **macOS**:
  - **Podman** (for building images): `brew install podman`
  - **OrbStack** (for Ray cluster): `brew install orbstack`
- **Linux**:
  - **Docker**: `apt-get install docker.io` (Ubuntu/Debian)
  - Or **Podman**: `apt-get install podman` (alternative)

#### Python Environment
- **Python 3.12+** (managed via pyenv recommended)
  ```bash
  pyenv install 3.12.9
  pyenv local 3.12.9
  ```

#### Claude Agent SDK Components
**Note**: These are installed **inside containers**, not on host:
- **Node.js 18+** - Included in Docker image
- **Claude Code CLI** - Installed in Docker image via npm
- **Claude Agent SDK 0.1.6** - Installed in Docker image via pip

#### Service Framework
- **Ray 2.51.1+** - Distributed computing framework
- **Kodosumi v1.0.0+** - Service framework with HITL support

### System Requirements

- **Operating System**:
  - macOS (with OrbStack for container support)
  - Linux (native container support)
  - WSL2 on Windows (with Docker)
- **Resources**:
  - 8GB+ RAM (1GB per concurrent conversation)
  - 10GB+ disk space (for Ray, containers, images)
  - Active internet connection for Claude API
- **Network**:
  - Outbound HTTPS to `api.anthropic.com`
  - Outbound HTTPS to `ghcr.io` (for pulling images)

### Verify Prerequisites

```bash
# Check Python
python3.12 --version

# macOS: Check Podman and OrbStack
podman --version
orb version

# Linux: Check Docker
docker --version

# Check Ray (install first if needed)
ray --version
```

## Quick Start

### Decision Tree: Which Setup is Right for You?

```
Are you on Linux?
├─ Yes → Use "Native Linux Setup" (containers work directly)
└─ No (macOS or Windows)
    └─ Use "Hybrid Setup with OrbStack" (containers work in VM)
```

### Option A: Hybrid macOS + OrbStack Setup (Recommended for macOS)

**Setup Guide**: See **[docs/ORBSTACK_SETUP.md](docs/ORBSTACK_SETUP.md)** for one-time setup instructions.

**Daily Workflow**: See **[docs/DAILY_WORKFLOW.md](docs/DAILY_WORKFLOW.md)** for daily usage commands.

**Quick Summary:**

1. **Install Prerequisites**:
   ```bash
   brew install orbstack podman
   ```

2. **Create Linux VM**:
   ```bash
   orb create ubuntu:24.04 ray-cluster
   ```

3. **Setup Ray Cluster in VM** (see full guide for details):
   - Install Docker, Ray, dependencies
   - Build or pull Docker image
   - Start Ray cluster

4. **Daily Usage** (after setup):
   ```bash
   # Morning startup - one command starts everything
   just orb-up

   # During development - edit code, then deploy
   just orb-deploy

   # End of day - shutdown
   just orb-down
   ```

**Benefits**: Native macOS development + Linux container support + simple daily workflow

---

### Option B: Native Linux Setup

**For Linux users, containers work directly without virtualization.**

#### 1. Clone and Setup

```bash
# Navigate to project directory
cd claude-kodosumi-hitl-template

# Create virtual environment with Python 3.12+
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

#### 2. Build Container Image

**Option 1: Build Locally** (for development)
```bash
# Create example config repos (or clone your actual repos)
mkdir -p /tmp/cc-master-agent-config/.claude
mkdir -p /tmp/cc-example-agent-config/.claude

# Build image locally
docker build \
  --build-arg MASTER_CONFIG_PATH=/tmp/cc-master-agent-config/.claude \
  --build-arg PROJECT_CONFIG_PATH=/tmp/cc-example-agent-config/.claude \
  -t claude-hitl-worker:latest \
  .
```

**Option 2: Pull from Registry** (recommended)
```bash
# Set up authentication
export GITHUB_TOKEN=ghp_...
export GITHUB_USERNAME=your-username

# Login to ghcr.io
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Pull image
docker pull ghcr.io/$GITHUB_USERNAME/claude-hitl-worker:latest

# Tag for local use
docker tag ghcr.io/$GITHUB_USERNAME/claude-hitl-worker:latest claude-hitl-worker:latest
```

#### 3. Configure Authentication

```bash
# Create .env file from example
cp .env.example .env

# Edit .env and add your Anthropic API key
# Get your API key from: https://console.anthropic.com/settings/keys
nano .env

# Load environment variables
source .env
export ANTHROPIC_API_KEY

# Create service config from example
cp data/config/claude_hitl_template.yaml.example data/config/claude_hitl_template.yaml
```

#### 4. Start the Service

```bash
# Ensure environment variables are loaded
source .env && export ANTHROPIC_API_KEY

# Start everything (Ray + Kodosumi + Admin Panel)
just start

# This will:
# 1. Start Ray cluster
# 2. Deploy the Kodosumi service (pulls container image)
# 3. Start execution spooler (REQUIRED for executions)
# 4. Launch admin panel at http://localhost:3370
```

#### 5. Access the Application

1. Open http://localhost:3370 in your browser
2. Navigate to the Claude HITL Template service
3. Enter a prompt and click "Start Conversation"
4. Interact with Claude through the HITL interface

#### 6. Stop the Service

```bash
just stop
```

---

### Option C: Connect to Remote Ray Cluster

If you have a separate Ray cluster (e.g., production), connect remotely:

```bash
# Configure Ray address
export RAY_ADDRESS=ray://your-cluster-address:10001

# Deploy to remote cluster
source .env && export ANTHROPIC_API_KEY
koco deploy -r

# Remote cluster will pull image from ghcr.io
```

## Ray Actor Architecture

This template uses **Ray Actors running in mandatory containers** to manage Claude SDK lifecycle.

### Why Ray Actors in Containers?

Per [Claude SDK hosting documentation](https://docs.claude.com/en/api/agent-sdk/hosting), Claude SDK is designed for:
- **Long-running container processes** (not stateless request handlers)
- **Persistent sessions** across interactions
- **Sandboxed execution** environment per session

**Our Solution**: Ray Actors provide persistent, stateful processes + containers provide isolation.

```
┌─────────────────────────────────────┐
│ Kodosumi + Ray Serve                │
│ (query.py - orchestration only)     │
│ - Stateless request handler         │
│ - Creates/retrieves actors          │
└──────────────┬──────────────────────┘
               │
               │ Create/retrieve actors
               ▼
┌─────────────────────────────────────┐
│ ClaudeSessionActor (agent.py)       │
│ **RUNS IN CONTAINER** (mandatory)   │
│                                     │
│ - Persistent subprocess manager     │
│ - Named: "claude-session-{id}"      │
│ - Resources: 1 CPU, 1GB RAM         │
│ - Isolated .claude/ configs         │
│ - Security sandbox                  │
└──────────────┬──────────────────────┘
               │
               │ Manages subprocess
               ▼
┌─────────────────────────────────────┐
│ Claude Code CLI (Node.js)           │
│ - Claude API communication          │
│ - Isolated process                  │
│ - Runs inside container             │
└─────────────────────────────────────┘
```

### Actor Lifecycle

```python
# 1. Create actor with container isolation (MANDATORY)
actor = create_actor(execution_id, use_container=True)

# Ray spawns container with image: ghcr.io/<user>/claude-hitl-worker:latest
# Container includes:
# - Baked .claude/ configs
# - Node.js + Claude CLI
# - Python + Claude Agent SDK

# 2. Connect and get initial response
result = await actor.connect.remote(prompt)

# 3. HITL loop - actor persists across interactions
for interaction in conversation:
    # Display messages
    for msg in result["messages"]:
        await tracer.markdown(f"Claude: {msg['content']}")

    # HITL pause (actor stays alive in container!)
    user_input = await tracer.lease("claude-input", F.Model(...))

    # Query actor (still in same container)
    result = await actor.query.remote(user_input["response"])

# 4. Cleanup (disconnect subprocess, kill actor, destroy container)
await cleanup_actor(execution_id)
```

### Key Benefits

1. **Persistence**: Actor maintains state across HITL pauses
2. **Isolation**: Each conversation runs in its own container
3. **Resource Control**: Container enforces CPU/memory limits
4. **Security**: Sandbox prevents host access
5. **Configuration**: Baked `.claude/` configs ensure consistency
6. **Recovery**: Auto-retry on actor crashes

## File Structure

```
claude-kodosumi-hitl-template/
├── claude_hitl_template/
│   ├── __init__.py          # Package initializer
│   ├── agent.py             # Ray Actor + Claude SDK logic (282 lines)
│   └── query.py             # Kodosumi orchestration only (276 lines)
├── data/config/
│   ├── config.yaml          # Global Ray Serve configuration
│   └── claude_hitl_template.yaml  # Service deployment + runtime_env
├── docs/
│   ├── ORBSTACK_SETUP.md    # Complete OrbStack setup guide
│   ├── CLAUDE_CONFIG_REPOS.md # Config repository structure
│   └── GITHUB_REGISTRY_SETUP.md # GitHub PAT setup instructions
├── tests/
│   ├── __init__.py
│   ├── test_basic.py        # Basic smoke tests
│   └── test_actors.py       # Ray Actor integration tests
├── Dockerfile               # Container image definition
├── build-and-push.sh        # Build and push images to ghcr.io
├── justfile                 # Task runner commands
├── pyproject.toml           # Project dependencies
├── pytest.ini               # Test configuration
├── .env.example             # Environment variable template
├── README.md                # This file
└── CLAUDE.md                # Claude Code guidance
```

## Development Commands

```bash
# Start full service stack
just start

# Stop all services
just stop

# Run tests
just test

# Check service status
just status

# Clean up temp files
just clean

# Build Docker image locally
docker build -t claude-hitl-worker:latest .

# Build and push to ghcr.io
./build-and-push.sh
```

## Extending the Template

### Adding Custom Business Logic

**Option 1: Extend `agent.py`**
```python
# claude_hitl_template/agent.py
def analyze_data(data: dict) -> dict:
    """Your custom data analysis logic"""
    # Add your logic here
    return results
```

### Customizing the HITL Flow

```python
# In query.py
user_input = await tracer.lease(
    "custom-interaction",
    F.Model(
        F.Markdown("### Custom Prompt"),
        F.InputArea(label="Custom Field", name="field"),
        F.Select(label="Options", ...),
        F.Submit("Continue")
    )
)
```

### Customizing Container Image

```dockerfile
# Dockerfile
FROM rayproject/ray:2.51.1-py312

# Add custom system packages
RUN apt-get update && apt-get install -y your-package

# Add custom Python packages
RUN pip install your-custom-package

# Continue with standard setup...
```

## Configuration Options

### Adjust Timeouts

```python
# In agent.py, ClaudeSessionActor.__init__()
self.timeout_seconds = 1200  # 20 minutes instead of 11

# In query.py
CONVERSATION_TIMEOUT_SECONDS = 1200
MAX_MESSAGE_ITERATIONS = 100
```

### Resource Allocation

```python
# In agent.py, create_actor()
ClaudeSessionActor.options(
    num_cpus=2,                 # 2 CPUs instead of 1
    memory=2 * 1024 * 1024 * 1024  # 2GB instead of 1GB
).remote(cwd=actor_cwd)
```

```yaml
# In data/config/claude_hitl_template.yaml
num_replicas: 2  # Scale up
max_concurrent_queries: 20  # Handle more concurrent users
```

## Testing

```bash
# Run all tests
just test

# Run with verbose output
pytest tests/ -v

# Run specific test
pytest tests/test_basic.py::test_agent_process_message -v
```

### Test Coverage
- ✅ Module imports
- ✅ Agent placeholder function
- ✅ Query module structure
- ✅ Configuration constants
- ✅ Package metadata

## Troubleshooting

### Container-Related Issues

**"Cannot connect to Ray GCS from container"**
- **macOS**: Use OrbStack setup (Podman networking doesn't work)
- **Linux**: Ensure Docker daemon is running: `systemctl status docker`

**"Image not found: claude-hitl-worker:latest"**
- Build locally: `docker build -t claude-hitl-worker:latest .`
- Or pull from registry: `docker pull ghcr.io/<username>/claude-hitl-worker:latest`

**"Permission denied accessing Docker socket"**
- Add user to docker group: `sudo usermod -aG docker $USER`
- Logout and login again

### Common Errors

**`InputsError.check()` AttributeError**
- **Fix**: Use `if error.has_errors(): raise error` instead

**Ray Version Mismatch**
```bash
ray stop
source .venv/bin/activate
ray --version  # Verify
just start
```

**Kodosumi Deployment Issues**
```bash
# Check logs
koco logs

# Redeploy
koco deploy -r

# Ensure spooler is running (CRITICAL!)
koco spool &
```

### Comprehensive Guide

See [CLAUDE.md - Extended Troubleshooting](CLAUDE.md#extended-troubleshooting) for detailed solutions.

## Production Deployment (Required: Containers)

### Deployment Checklist

- [ ] Build production image with prod configs
- [ ] Push image to ghcr.io or private registry
- [ ] Configure Ray cluster on Linux (native or cloud)
- [ ] Set `ANTHROPIC_API_KEY` in deployment environment
- [ ] Configure resource limits (CPU, memory per actor)
- [ ] Set up monitoring and logging
- [ ] Test container deployment before production

### Authentication

**Option A: Environment Variables** (Recommended)
```bash
export ANTHROPIC_API_KEY=sk-ant-...
koco deploy
```

**Option B: AWS Secrets Manager**
```yaml
# In deployment config
env_vars:
  ANTHROPIC_API_KEY: "{{resolve:secretsmanager:claude-api-key}}"
```

### Monitoring & Best Practices

1. **Ray Dashboard**: Monitor actor status at `http://localhost:8265`
2. **Container Metrics**: Use `docker stats` or Prometheus
3. **Error Logging**: Add structured logging instead of print statements
4. **Rate Limiting**: Configure `max_concurrent_queries` in deployment YAML
5. **Resource Limits**: Ensure adequate RAM (1GB per concurrent conversation)
6. **Health Checks**: Monitor actor lifecycle and cleanup
7. **API Key Rotation**: Use secure secret management (Vault, AWS Secrets Manager)

## Contributing

This is a template project. Fork and customize for your needs!

## License

MIT License - Use freely for your projects

## Related Resources

- [Claude Agent SDK Docs](https://docs.claude.com/en/api/agent-sdk/python)
- [Claude SDK Hosting Guide](https://docs.claude.com/en/api/agent-sdk/hosting)
- [Kodosumi Documentation](https://kodosumi.dev)
- [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html)
- [Claude Code CLI](https://docs.claude.com/en/docs/claude-code)

## Support

For issues or questions:
- Claude SDK: https://docs.claude.com/en/api/agent-sdk
- Kodosumi: Check Kodosumi documentation
- This template: Open an issue on GitHub

---

**Built with Claude Agent SDK + Kodosumi + Mandatory Container Isolation**
