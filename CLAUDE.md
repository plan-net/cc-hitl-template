# CLAUDE.md

Essential context for Claude Code when working with this repository.

## Project Overview

**Claude + Kodosumi HITL Template** - Production-ready template for interactive AI agents with Human-in-the-Loop capabilities.

**Architecture**: Kodosumi (macOS) → Ray cluster (OrbStack VM/Linux) → Containerized Ray Actors → Claude SDK subprocess

**Key Pattern**: Sub-Agent + Skills for autonomous operations (`/cc-setup`, `/cc-deploy`, `/cc-shutdown`)

**Compatibility**: Python 3.12+, Claude Agent SDK 0.1.6+, Kodosumi 1.0.0+, Ray 2.51.1+

---

## Development Context

### System Architecture

**macOS (Hybrid Setup)**:
- Development: macOS (IDE, git, koco CLI)
- Ray Cluster: OrbStack Linux VM (containers work natively)
- Why: Ray's container networking requires Linux; Podman on macOS uses QEMU VM which breaks `127.0.0.1` assumptions

**Linux (Native)**:
- Everything runs natively on Linux
- Docker works out of the box

### Key Technologies

| Component | Purpose | Location |
|-----------|---------|----------|
| Kodosumi | HITL framework + admin panel | Runs on macOS/Linux host |
| Ray 2.51.1+ | Distributed computing + actors | Runs in OrbStack VM or native Linux |
| Docker/Podman | Container runtime | Required for actor isolation |
| Claude SDK 0.1.6 | AI conversation API | Runs in containerized actors |
| OrbStack | Linux VM for macOS | macOS only |

---

## Commands

### Claude Code Slash Commands

- **`/cc-setup`** - Autonomous setup automation
  - Detects OS, checks prerequisites
  - Creates OrbStack VM (macOS) or configures Docker (Linux)
  - Guides through API key configuration
  - Starts and validates services
  - Agent: `.claude/agents/setup.md`
  - Skills: `prerequisite-check`, `vm-setup`

- **`/cc-deploy`** - Autonomous deployment with change detection
  - Analyzes local code changes
  - Checks remote config repo changes (git ls-remote)
  - Decides: rebuild image, redeploy, or restart
  - Asks confirmation for risky ops (rebuild)
  - Auto-approves safe ops (redeploy, restart)
  - Agent: `.claude/agents/deployment.md`
  - Skills: `docker-build`
  - State: `.claude/.last-deploy-state.json`

- **`/cc-shutdown`** - Stop all services cleanly
  - Stops Kodosumi services (macOS)
  - Stops Ray cluster
  - Stops OrbStack VM (macOS)
  - Validates shutdown

### justfile Commands (macOS)

```bash
just orb-up         # Complete startup: Ray + deploy + services
just orb-down       # Complete shutdown
just orb-deploy     # Sync code from macOS to VM + redeploy
just orb-start      # Start Ray cluster in VM only
just orb-stop       # Stop Ray cluster and VM
just orb-status     # Check VM and Ray status
just local-services # Start Kodosumi on macOS
just local-logs     # View Kodosumi logs
```

### justfile Commands (Linux)

```bash
just start    # Start Ray + Kodosumi + deploy
just stop     # Stop all services
just test     # Run tests
just status   # Check service status
```

---

## Architecture Patterns

### Ray Actor Pattern

**Problem**: Claude SDK needs long-running subprocess, but Ray Serve workers are stateless

**Solution**: Ray Actors as persistent session containers

```python
# In query.py - Lean orchestration only
from .agent import create_actor, get_actor, cleanup_actor

# Create persistent actor (survives HITL pauses)
actor = create_actor(execution_id)

# Connect and get initial response
result = await actor.connect.remote(initial_prompt)

# Display messages
for msg in result["messages"]:
    await tracer.markdown(f"Claude: {msg['content']}")

# HITL pause - actor stays alive!
user_input = await tracer.lease("claude-input", F.Model(...))

# Resume - retrieve actor (handles worker restarts)
actor = get_actor(execution_id)
result = await actor.query.remote(user_input["response"])

# Cleanup
await cleanup_actor(execution_id)
```

**Key points**:
- One actor per conversation session
- Named actors: `claude-session-{execution_id}`
- Resources: 1 CPU, 1GB RAM per actor
- Runs in container with baked .claude/ configs
- Survives HITL pauses and worker state changes

### Sub-Agent + Skills Pattern

**For complex autonomous operations**:

**Agents** (`.claude/agents/`):
- Complex multi-step orchestration
- Analyze → Decide → Execute → Validate → Report
- Have own context window (separate from main conversation)
- Examples: deployment agent, setup agent

**Skills** (`.claude/skills/`):
- Reusable capabilities
- Shell scripts + documentation
- Progressive disclosure (SKILL.md explains, script executes)
- Examples: docker-build, prerequisite-check, vm-setup

**Commands** (`.claude/commands/`):
- Entry points that trigger agents
- Use Task tool to invoke agent
- Agent returns final report

### State Tracking

**Deployment state** (`.claude/.last-deploy-state.json`):
```json
{
  "timestamp": "2025-11-03T12:30:00Z",
  "master_config_commit": "abc123",
  "project_config_commit": "def456",
  "docker_image_tag": "ghcr.io/<user>/claude-hitl-worker:latest",
  "code_commit": "abc123"
}
```

**Setup state** (`.claude/.setup-state.json`):
```json
{
  "timestamp": "2025-11-03T12:00:00Z",
  "os": "Darwin",
  "prerequisites_checked": true,
  "venv_created": true,
  "setup_completed": true
}
```

Both gitignored (machine-specific).

### Configuration Layers

Docker images bake multiple `.claude/` sources:

```dockerfile
# Baked into image at build time
COPY template_user/.claude /app/template_user/.claude  # Master config
COPY project/.claude /app/project/.claude              # Project config
ENV HOME=/app/template_user  # "user" settings load from master
```

```python
# agent.py - Settings merge
ClaudeAgentOptions(
    setting_sources=["user", "project", "local"]
    # user = $HOME/.claude (master config)
    # project = project/.claude
    # local = cwd/.claude (deployment-specific)
)
```

---

## File Organization

### Where Things Live

```
claude_hitl_template/
├── agent.py (282 lines)      # All Claude SDK logic + Ray Actors
│                              # - ClaudeSessionActor class
│                              # - create_actor, get_actor, cleanup_actor
│                              # - Pure business logic
│
└── query.py (276 lines)       # Kodosumi HITL orchestration only
                               # - Form definition (prompt_form)
                               # - Entry point (@app.enter)
                               # - Orchestration (run_conversation)
                               # - No Claude SDK logic here

.claude/
├── agents/                    # Autonomous agents
│   ├── deployment.md          # Deployment orchestration
│   └── setup.md               # Setup automation
│
├── skills/                    # Reusable capabilities
│   ├── docker-build/          # Build Docker images
│   ├── prerequisite-check/    # Validate dependencies
│   └── vm-setup/              # Create OrbStack VM
│
├── commands/                  # Slash commands
│   ├── cc-deploy.md           # Triggers deployment agent
│   ├── cc-setup.md            # Triggers setup agent
│   └── cc-shutdown.md         # Simple shutdown
│
├── settings.json              # Auto-approval permissions
├── .last-deploy-state.json    # Deployment state (gitignored)
└── .setup-state.json          # Setup state (gitignored)

data/config/
├── config.yaml                        # Global Ray Serve config
└── claude_hitl_template.yaml          # Service-specific config
                                        # - route_prefix, import_path
                                        # - runtime_env (pip, env_vars)
```

---

## When Extending

### Add Business Logic
**File**: `claude_hitl_template/agent.py`
```python
# Keep agent.py lean - business logic only
def your_custom_function(data: dict) -> dict:
    """Your logic here"""
    return results
```

### Add HITL UI / Form
**File**: `claude_hitl_template/query.py`
```python
# All Kodosumi integration stays here
user_input = await tracer.lease(
    "custom-interaction",
    F.Model(
        F.InputArea(label="Custom", name="field"),
        F.Submit("Send")
    )
)
```

### Create New Autonomous Operation
1. **Agent**: `.claude/agents/my-agent.md` (orchestration logic)
2. **Skill** (optional): `.claude/skills/my-skill/` (reusable capability)
3. **Command**: `.claude/commands/my-command.md` (entry point)
4. **Permissions**: Update `.claude/settings.json`

**Pattern to follow**: See deployment agent + docker-build skill as reference.

### Add Configuration
**Development**: `data/config/claude_hitl_template.yaml.example`
**Deployment**: User copies to `claude_hitl_template.yaml` and customizes

---

## Critical Known Issues

### Claude SDK v0.1.6: connect(prompt) Broken

**Issue**: `await client.connect("prompt string")` causes `ProcessTransport is not ready for writing`

**Cause**: SDK closes stdin immediately in non-streaming mode, breaking control protocol

**Working pattern** (already used in agent.py:65-97):
```python
await client.connect(None)  # Keeps stdin open
await client.query("your prompt here")  # Works correctly
async for msg in client.receive_response():
    # Process messages
```

**Don't use**: `await client.connect("prompt")` - this is broken in v0.1.6

### macOS: Requires OrbStack for Containers

**Issue**: Podman on macOS uses QEMU VM where containers can't reach Ray GCS at `127.0.0.1:6379`

**Solution**: Use OrbStack Linux VM for Ray cluster (native container networking)

**Why**: Ray assumes containers share host network namespace. Works on Linux, broken on macOS Podman.

### Kodosumi API Quirks

**InputsError validation**:
```python
# Wrong
error.check()  # Method doesn't exist

# Correct
if error.has_errors():
    raise error
```

**Launch function signature**:
```python
# Wrong
async def run_task(request: Request, tracer: Tracer, inputs: dict):
    # request not passed to launched functions

# Correct
async def run_task(inputs: dict, tracer: Tracer):
    # Only inputs and tracer, in this order
```

**Ray Serve deployment wrapper** (required):
```python
# Wrong
fast_app = app  # Direct export doesn't work

# Correct
@serve.deployment
@serve.ingress(app)
class MyService:
    pass

fast_app = MyService.bind()
```

---

## Where to Find More

- **Architecture decisions**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Setup guide**: [docs/SETUP.md](docs/SETUP.md) or run `/cc-setup`
- **Daily workflow**: [docs/DAILY_WORKFLOW.md](docs/DAILY_WORKFLOW.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **All known issues**: [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)
- **Code patterns**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- **Deployment guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Command reference**: [docs/REFERENCE.md](docs/REFERENCE.md)

---

## Quick Troubleshooting

**Services won't start**:
```bash
just orb-down && just orb-up  # macOS
just stop && just start        # Linux
```

**Can't reach Ray Dashboard**:
```bash
just orb-status  # Check Ray is running
curl http://localhost:8265  # Test accessibility
```

**SSH/rsync errors (macOS)**:
- Use `ray-cluster@orb` format (not `ray-cluster.orb.local`)
- OrbStack handles SSH keys automatically
- Check VM running: `orb list | grep ray-cluster`

**Docker build fails**:
- Check GITHUB_TOKEN in .env
- Verify Docker/Podman running
- Try: `./build-and-push.sh --no-push`

For comprehensive solutions: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

**This is a Claude Code first template. Use `/cc-setup` to get started!**
