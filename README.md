# Claude + Kodosumi HITL Template

A **Claude Code first** template for building interactive AI agents with Human-in-the-Loop (HITL) capabilities using Claude Agent SDK, Kodosumi, and Ray.

## What This Template Does

Build production-ready conversational AI agents with:
- ✅ **Back-and-forth conversations** with Claude via HITL interface
- ✅ **Persistent sessions** across interactions using Ray Actors
- ✅ **Container isolation** for security and configuration management
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

**Why OrbStack on macOS?** Ray's container networking requires native Linux. Podman on macOS uses QEMU which breaks Ray's `127.0.0.1` assumptions. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#why-macos-needs-orbstack).

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

### Morning Startup (macOS)
```bash
just orb-up  # Starts Ray cluster in VM + Kodosumi services on macOS
```

### Morning Startup (Linux)
```bash
just start  # Starts Ray cluster + Kodosumi services
```

### Development Cycle

1. **Edit code** on your machine (IDE, git workflow unchanged)
2. **Deploy changes**:
   ```bash
   /cc-deploy  # Claude Code - autonomous deployment
   # OR
   just orb-deploy  # macOS manual
   just deploy      # Linux manual
   ```
3. **Test** at http://localhost:3370
4. **View logs**: `just local-logs` (macOS) or `just logs` (Linux)

### Evening Shutdown
```bash
/cc-shutdown  # Claude Code
# OR
just orb-down  # macOS manual
just stop      # Linux manual
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
- **[Architecture](docs/ARCHITECTURE.md)** - System design and rationale
- **[Reference](docs/REFERENCE.md)** - Commands, configs, patterns, FAQ
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Error solutions
- **[Known Issues](docs/KNOWN_ISSUES.md)** - SDK bugs and workarounds

### Development
- **[Development Guide](docs/DEVELOPMENT.md)** - Extending the template
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment

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
- **Master config** (`template_user/.claude/`): Template-level settings
- **Project config** (`project/.claude/`): Deployment-specific settings
- **Settings merge**: `setting_sources=["user", "project", "local"]`

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design details.

---

## Project Structure

```
cc-hitl-template/
├── claude_hitl_template/
│   ├── agent.py             # Ray Actor + Claude SDK (282 lines)
│   └── query.py             # Kodosumi HITL orchestration (276 lines)
├── .claude/
│   ├── agents/              # Autonomous agents (deployment, setup)
│   ├── skills/              # Reusable capabilities
│   ├── commands/            # Slash commands (/cc-setup, /cc-deploy, /cc-shutdown)
│   └── settings.json        # Auto-approval permissions
├── data/config/
│   ├── config.yaml          # Global Ray Serve config
│   └── claude_hitl_template.yaml  # Service deployment config
├── docs/                    # Documentation
├── tests/                   # Test suite
├── Dockerfile               # Container image definition
├── build-and-push.sh        # Image build script
├── justfile                 # Task automation commands
└── README.md                # This file
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
1. Create agent: `.claude/agents/my-agent.md`
2. Create skills if needed: `.claude/skills/my-skill/`
3. Create command: `.claude/commands/my-command.md`

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for complete guide.

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
