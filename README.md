# Claude + Kodosumi HITL Template

A **Claude Code first** template for building interactive AI agents with Human-in-the-Loop (HITL) capabilities using Claude Agent SDK, Kodosumi, and Ray.

## What This Template Does

Build production-ready conversational AI agents with:
- ✅ **Back-and-forth conversations** with Claude via HITL interface
- ✅ **Persistent sessions** across interactions using Ray Actors
- ✅ **Container isolation** for security and configuration management
- ✅ **Plugin-based architecture** for reusable capabilities
- ✅ **Autonomous operations** with Sub-Agent + Skills pattern
- ✅ **One-command setup** via `/cc-setup` in Claude Code

## Claude Code First Approach

This template is designed for **Claude Code** - Anthropic's official CLI that brings AI assistance to your development workflow.

**Setup in one command**:
```bash
git clone <your-repo-url> cc-hitl-template
cd cc-hitl-template

# In Claude Code:
/cc-setup  # Guided setup with todo list and approvals
```

The setup agent will:
- Analyze your system and detect your OS
- Check which prerequisites are installed vs missing
- Create a comprehensive todo list showing progress
- Guide you through each installation with individual approvals
- Configure environment with your API keys
- Set up OrbStack VM (macOS) or Docker (Linux)
- Start Ray cluster and Kodosumi services
- Validate everything is working

**How it works**: Sub-agent analyzes system → Creates TodoWrite list → Main agent executes with your approval

**Result**: Working system at http://localhost:3370 in ~10-15 minutes.

### Claude Code Features in This Template

- **`/cc-setup`** - Guided setup automation (analyzer-only pattern with TodoWrite)
- **`/cc-deploy`** - Intelligent deployment with change detection and automatic Docker rebuilds
- **`/cc-shutdown`** - Clean shutdown of all services

All powered by **Sub-Agent + Skills** pattern for autonomous, context-aware operations.

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│   macOS Development (or Linux Host)      │
│   - IDE, Git, Source Code               │
│   - Kod osumi CLI (koco)                 │
│   - Connects to Ray via localhost       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   OrbStack Linux VM (macOS only)        │
│   or Native Linux                        │
│                                          │
│   ┌────────────────────────────────┐    │
│   │  Ray Cluster                   │    │
│   │  - Ray Serve deployment        │    │
│   │  - Spawns containerized actors │    │
│   └──────────────┬─────────────────┘    │
│                  │                       │
│                  ▼                       │
│   ┌────────────────────────────────┐    │
│   │  Ray Actor (in Container)      │    │
│   │  - Claude SDK subprocess       │    │
│   │  - Isolated .claude/ configs   │    │
│   │  - Security sandbox            │    │
│   └────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Key components**:
- **Kodosumi**: HITL framework providing interactive UI and execution management
- **Ray**: Distributed computing framework managing actor lifecycle
- **Containers**: Mandatory isolation for Claude SDK sessions (security + config management)
- **OrbStack** (macOS): Lightweight Linux VM enabling native container networking

**Why containers?** Security isolation, configuration layering (master + project configs), and reproducible environments. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

**Why OrbStack on macOS?** Ray's container networking requires native Linux. Podman on macOS uses QEMU which breaks Ray's `127.0.0.1` assumptions.

---

## Plugin Architecture

This template uses a **plugin-based architecture** for organizing reusable capabilities:

### Marketplaces

Two plugin marketplaces provide different types of capabilities:

**🛠️ cc-marketplace-developers** (Development plugins)
- Repository: `plan-net/cc-marketplace-developers`
- Purpose: Tools for development, setup, and testing
- Installed on: Developer machine (Claude Code CLI)
- Examples: `general`, `claude-agent-sdk`

**🤖 cc-marketplace-agents** (Runtime plugins)
- Repository: `plan-net/cc-marketplace-agents`
- Purpose: Runtime capabilities for deployed agents
- Installed in: Container images (baked at build time)
- Examples: `master-core` (provides `/cc-setup`, `/cc-deploy`, `/cc-shutdown`)

### How It Works

**Local Development**:
- Plugins declared in `.claude/settings.json`
- Claude Code CLI automatically installs on restart
- Available immediately to the main agent

**Container Deployment**:
- Same settings in config repositories
- Build process bakes plugins into container image
- Runtime loads plugins from `/app/plugins/` directory

### Benefits

- **Reusability**: Share commands, agents, and skills across projects
- **Versioning**: Pin to specific marketplace commits
- **Modularity**: Enable/disable capabilities per project
- **Separation**: Template code vs operational tooling
- **Maintainability**: Update plugins independently

See **[CLAUDE.md](CLAUDE.md#plugin-architecture)** and **[docs/PLUGINS.md](docs/PLUGINS.md)** for complete plugin guide.

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Claude Code CLI
- **macOS**: OrbStack + Podman
- **Linux**: Docker

See [docs/SETUP.md](docs/SETUP.md) for installation instructions.

### Setup

**Option 1: Guided Setup (Recommended)**
```bash
# In Claude Code
/cc-setup
```

**Option 2: Manual**

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for step-by-step manual setup.

---

## Daily Workflow

### Morning Startup
```bash
just start  # Starts everything (VM + Ray + Kodosumi)
```

Wait ~10 seconds, then access: http://localhost:3370

### Development Cycle

1. **Edit code** on your machine (IDE, git workflow unchanged)
2. **Deploy changes**:
   ```bash
   /cc-deploy  # Claude Code - autonomous deployment
   ```
3. **Test** at http://localhost:3370
4. **View logs**:
   ```bash
   orb -m ray-cluster bash -c "tail -f /tmp/koco-serve.log"
   ```

### Evening Shutdown
```bash
just stop  # Stops everything
```

See [docs/DAILY_WORKFLOW.md](docs/DAILY_WORKFLOW.md) for complete daily workflow guide.

---

## Documentation

### Getting Started
- **[Quick Start](docs/QUICKSTART.md)** - Get running in 5 minutes
- **[Setup Guide](docs/SETUP.md)** - Prerequisites and installation
- **[OrbStack Setup](docs/ORBSTACK_SETUP.md)** - macOS hybrid setup details
- **[Daily Workflow](docs/DAILY_WORKFLOW.md)** - Day-to-day development guide

### Reference
- **[Plugin Guide](docs/PLUGINS.md)** - Plugin system and marketplace usage
- **[Dependency Management](docs/DEPENDENCY-MANAGEMENT.md)** - Managing container dependencies
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Error solutions
- **[Reference](docs/REFERENCE.md)** - Commands, configs, patterns, FAQ
- **[Known Issues](docs/KNOWN_ISSUES.md)** - SDK bugs and workarounds

### Development
- **[Development Guide](docs/DEVELOPMENT.md)** - Extending the template
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Architecture](docs/ARCHITECTURE.md)** - System design and rationale

### Specifications
- **[Immutable Container Dependencies](specs/immutable-container-dependencies.md)** - Complete dependency system specification
- **[Template Repo Changes](specs/template-repo-changes.md)** - Implementation checklist for this repo

---

## Key Features

### Ray Actor Pattern
Solves Claude SDK subprocess lifecycle using persistent Ray Actors:
- Each conversation = one Ray Actor in isolated container
- Actor survives HITL pauses (worker state changes don't affect it)
- Named actors retrievable after interruptions
- Resource limits enforced (1 CPU, 1GB RAM per conversation)

### Sub-Agent + Skills Pattern
Autonomous operations with intelligent decision-making:
- **Agents** (`/cc-setup`, `/cc-deploy`): Complex multi-step orchestration
- **Skills** (docker-build, prerequisite-check, vm-setup): Reusable capabilities
- **State tracking**: Idempotent operations, skip completed steps
- **Error recovery**: Handle common issues automatically
- **Analyzer-only pattern** (`/cc-setup`): Sub-agent analyzes → TodoWrite → Main agent executes

### Configuration Layers
Docker images bake multiple `.claude/` configuration sources:
- **Master config** (`/app/template_user/.claude/`): Template-level settings
- **Project config** (`/app/.claude/`): Deployment-specific settings
- **Plugins** (`/app/plugins/`): Baked marketplace plugins
- **Settings merge**: `setting_sources=["user", "project", "local"]`
- **Environment**: `HOME=/app/template_user` for SDK settings resolution

### Immutable Container Dependencies
All runtime dependencies declared at build time for security and reliability:
- **Immutable containers**: No pip/npm/apt installs at runtime
- **Config repo declarations**: Dependencies live in config repos' `dependencies/` directories
- **Automatic installation**: Build system merges and installs all declared packages
- **Runtime awareness**: Agents can introspect available packages via manifest
- **Clear feedback**: Agents suggest missing dependencies via structured messages
- See: [Dependency Management Guide](docs/DEPENDENCY-MANAGEMENT.md)

See [CLAUDE.md#container-folder-structure](CLAUDE.md#container-folder-structure) and [docs/PLUGINS.md#container-folder-structure](docs/PLUGINS.md#container-folder-structure) for complete container layout.

---

## Project Structure

```
cc-hitl-template/
├── claude_hitl_template/
│   ├── agent.py             # Ray Actor + Claude SDK + Plugin loading
│   └── query.py             # Kodosumi HITL orchestration
├── .claude/
│   ├── CLAUDE.md            # Project-specific instructions
│   └── settings.json        # Marketplace config + auto-approvals
├── data/config/
│   ├── config.yaml          # Global Ray Serve config
│   └── claude_hitl_template.yaml  # Service deployment config
├── docs/                    # Documentation
│   ├── SETUP.md             # Installation guide
│   ├── PLUGINS.md           # Plugin system guide
│   └── ...                  # Additional docs
├── tests/                   # Test suite
├── Dockerfile               # Container image definition
├── justfile                 # Task automation commands
└── README.md                # This file

# Commands, agents, and skills now provided via plugins:
# - Installed from cc-marketplace-developers (dev tools)
# - Installed from cc-marketplace-agents (runtime capabilities)
# See "Plugin Architecture" section above
```

---

## Extending the Template

### Add Business Logic
Edit `claude_hitl_template/agent.py`:
```python
def analyze_data(data: dict) -> dict:
    """Your custom logic here"""
    return results
```

### Add Custom HITL Flow
Edit `claude_hitl_template/query.py`:
```python
user_input = await tracer.lease(
    "custom-interaction",
    F.Model(
        F.InputArea(label="Custom Field", name="field"),
        F.Submit("Continue")
    )
)
```

### Create New Autonomous Operation

**For project-specific operations**:
1. Create in local `.claude/` directory or project marketplace
2. Follow plugin structure (commands/, agents/, skills/)

**For shared/reusable operations**:
1. Create plugin in your marketplace repository
2. Add marketplace to `.claude/settings.json`
3. Enable plugin in `.claude/settings.json`

See [CLAUDE.md](CLAUDE.md#when-extending) and [docs/PLUGINS.md](docs/PLUGINS.md) for complete guide.

---

## Testing

```bash
# Run all tests
just test

# Run with verbose output
pytest tests/ -v

# Run specific test
pytest tests/test_basic.py::test_agent_process_message -v
```

---

## Production Deployment

This template supports production deployment with:
- GitHub Container Registry (ghcr.io) for image distribution
- Baked `.claude/` configurations from separate git repos
- Autonomous deployment via `/cc-deploy`
- Remote Ray cluster support

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production guide.

---

## Troubleshooting

**Services won't start**: `just orb-down && just orb-up` (macOS) or `just stop && just start` (Linux)

**Port conflicts**: Check ports with `lsof -i :8265` and `lsof -i :3370`

**Ray connection errors**: `just orb-restart` (macOS) or `ray stop && ray start --head` (Linux)

**More help**: See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for comprehensive solutions.

---

## Resources

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk/python)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Kodosumi Documentation](https://kodosumi.dev)
- [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html)

---

## Contributing

This is a template project. Fork and customize for your needs!

## License

MIT License - Use freely for your projects

---

**Built with Claude Agent SDK + Kodosumi + Ray + Claude Code**
