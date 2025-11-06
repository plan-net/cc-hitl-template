# CLAUDE.md

Essential context for Claude Code when working with this repository.

## Project Overview

**Claude + Kodosumi HITL Template** - Production-ready template for interactive AI agents with Human-in-the-Loop capabilities.

**Architecture**: Kodosumi (macOS) → Ray cluster (OrbStack VM/Linux) → Containerized Ray Actors → Claude SDK subprocess

**Key Pattern**: Sub-Agent + Skills for autonomous operations (`/cc-setup`, `/cc-deploy`, `/cc-shutdown`)

**Compatibility**: Python 3.12+, Claude Agent SDK 0.1.6+, Kodosumi 1.0.0+, Ray 2.51.1+

---

## ⚠️ CRITICAL RULES - READ FIRST

**NEVER DO THESE THINGS:**

1. **❌ NEVER call build scripts directly** - Always use `/cc-deploy` command
   - ❌ WRONG: `bash build.sh` or `bash ~/.claude/plugins/.../build.sh`
   - ✅ CORRECT: `/cc-deploy` (uses Skill tool properly)

2. **❌ NEVER use raw Bash for service control** - Always use `just` commands
   - ❌ WRONG: `ray stop`, `ray start`, `orb -m ray-cluster bash -c "..."`
   - ✅ CORRECT: `just stop`, `just start`

3. **❌ NEVER skip `just stop` before `just start`** - Always stop first
   - ❌ WRONG: `just start` (when services running)
   - ✅ CORRECT: `just stop && just start`

**Why these rules exist:**
- `/cc-deploy` handles change detection, approvals, and state tracking
- `just` commands handle VM/Ray/Kodosumi coordination correctly
- Direct script calls bypass safety checks and cause inconsistent state

---

## Development Context

### System Architecture

**macOS**:
- Development: macOS (IDE, git)
- Everything else: OrbStack Linux VM (Ray + Kodosumi + containers)
- Why: Ray's container networking requires Linux; running everything in VM simplifies architecture

**Linux (Native)**:
- Everything runs natively on Linux
- Docker works out of the box

### Key Technologies

| Component | Purpose | Location |
|-----------|---------|----------|
| Kodosumi | HITL framework + admin panel | Runs in OrbStack VM (macOS) or natively (Linux) |
| Ray 2.51.1+ | Distributed computing + actors | Runs in OrbStack VM (macOS) or natively (Linux) |
| Docker/Podman | Container runtime | Required for actor isolation |
| Claude SDK 0.1.6 | AI conversation API | Runs in containerized actors |
| OrbStack | Linux VM for macOS | macOS only |

---

## Plugin Architecture

This template uses a **plugin-based architecture** with two marketplaces providing reusable capabilities:

### Marketplaces

**cc-marketplace-developers** (Development-time plugins)
- Repository: `plan-net/cc-marketplace-developers`
- Purpose: Tools for setup, deployment, testing
- Installed on: Developer machine (Claude Code CLI)
- Examples: `general`, `claude-agent-sdk`

**cc-marketplace-agents** (Runtime plugins)
- Repository: `plan-net/cc-marketplace-agents`
- Purpose: Runtime capabilities for deployed HITL agents
- Installed in: Container images (baked at build time)
- Examples: `master-core`, `hitl-example`

### How Plugins Work

**Local Development (Claude Code CLI)**:
1. Marketplaces declared in `.claude/settings.json` (`extraKnownMarketplaces`)
2. Plugins enabled in `.claude/settings.json` (`enabledPlugins`)
3. Claude Code CLI auto-installs on restart
4. Plugins available to main agent immediately
5. Location: `~/.cache/claude-code/plugins/`

**Container Deployment (Ray Actors)**:
1. Same settings in config repos (master + project)
2. `build.sh` reads settings → clones marketplaces → copies plugins
3. Dockerfile bakes plugins into image at `/app/plugins/{marketplace}/plugins/{plugin}/`
4. `agent.py` loads plugins at runtime via `ClaudeAgentOptions(plugins=[...])`
5. Plugins available to containerized Claude agents

### Plugin Settings Resolution

The SDK uses a three-tier settings hierarchy:

```python
ClaudeAgentOptions(
    setting_sources=["user", "project", "local"]
)
```

**In containers**:
- **"user"** → `$HOME/.claude/` = `/app/template_user/.claude/` (master config repo)
- **"project"** → `{cwd}/.claude/` = `/app/.claude/` (project config repo)
- **"local"** → Runtime overrides (not used in this template)

Project settings override master settings. This allows:
- Master config: Template-level defaults (user/organization plugins)
- Project config: Project-specific plugins (overrides master)

### Enabled Plugins

Current configuration in `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "cc-marketplace-developers": {
      "source": {"source": "github", "repo": "plan-net/cc-marketplace-developers"}
    },
    "cc-marketplace-agents": {
      "source": {"source": "github", "repo": "plan-net/cc-marketplace-agents"}
    }
  },
  "enabledPlugins": {
    "general@cc-marketplace-developers": true,
    "claude-agent-sdk@cc-marketplace-developers": true,
    "master-core@cc-marketplace-agents": true
  }
}
```

### Adding Custom Plugins

**To add a new marketplace**:
1. Add to `.claude/settings.json`:
```json
"extraKnownMarketplaces": {
  "my-marketplace": {
    "source": {"source": "github", "repo": "org/repo"}
  }
}
```

**To enable a plugin**:
1. Add to `.claude/settings.json`:
```json
"enabledPlugins": {
  "my-plugin@my-marketplace": true
}
```

2. For development: Restart Claude Code CLI
3. For deployment: Rebuild container image (`/cc-deploy` will detect config change)

### Plugin Migration

Commands, skills, and agents previously in `.claude/` are now plugins:

| Old Location | New Location | Marketplace | Plugin |
|--------------|--------------|-------------|--------|
| `.claude/commands/cc-setup.md` | `master-core` | cc-marketplace-agents | `/cc-setup` |
| `.claude/commands/cc-deploy.md` | `master-core` | cc-marketplace-agents | `/cc-deploy` |
| `.claude/commands/cc-shutdown.md` | `master-core` | cc-marketplace-agents | `/cc-shutdown` |
| `.claude/agents/setup.md` | `master-core` | cc-marketplace-agents | Setup agent |
| `.claude/agents/deployment.md` | `master-core` | cc-marketplace-agents | Deployment agent |
| `.claude/skills/docker-build/` | `master-core` | cc-marketplace-agents | docker-build skill |
| `.claude/skills/prerequisite-check/` | `master-core` | cc-marketplace-agents | prerequisite-check skill |
| `.claude/skills/vm-setup/` | `master-core` | cc-marketplace-agents | vm-setup skill |

All functionality remains the same - just distributed via plugins.

### Benefits

**Reusability**: Share plugins across multiple projects
**Versioning**: Pin to specific marketplace commits
**Separation**: Template code vs operational tooling
**Modularity**: Enable/disable capabilities per project
**Maintainability**: Update plugins independently

---

## Commands

### Claude Code Slash Commands

- **`/cc-setup`** - Guided setup automation (analyzer-only pattern)
  - Sub-agent analyzes system and creates TodoWrite list
  - Main agent executes pending items with individual approvals
  - Detects OS, checks prerequisites
  - Creates OrbStack VM (macOS) or configures Docker (Linux)
  - Guides through API key configuration
  - Starts and validates services
  - Agent: `.claude/agents/setup.md`
  - Skills: `prerequisite-check`, `vm-setup`
  - Pattern: Analyzer (sub-agent) → TodoWrite → Executor (main agent)

- **`/cc-deploy`** - Autonomous deployment with change detection
  - Analyzes local code changes
  - Checks remote config repo changes (git ls-remote)
  - Decides: rebuild image, redeploy, or restart
  - Asks confirmation for risky ops (rebuild with detailed reasoning)
  - Auto-approves safe ops (redeploy, restart)
  - Reports image digest and verifies Ray is using new image
  - Agent: `.claude/agents/deployment.md`
  - Skills: `docker-build` (auto-invoked)
  - State: `.claude/.last-deploy-state.json` (includes image digest)

- **`/cc-shutdown`** - Stop all services cleanly
  - Stops Kodosumi services in VM
  - Stops Ray cluster in VM
  - Stops OrbStack VM (macOS)
  - Validates shutdown

### justfile Commands

**macOS:**
```bash
just start    # Start everything (VM + Ray + Kodosumi)
just stop     # Stop everything
```

**What `just start` does:**
1. Starts OrbStack VM (`ray-cluster`)
2. Starts Ray cluster in VM
3. Deploys application to Ray
4. Starts koco spool in VM
5. Starts koco serve in VM
6. Admin panel accessible at http://localhost:3370

**What `just stop` does:**
1. Stops koco processes in VM
2. Stops Ray cluster in VM
3. Stops OrbStack VM

**Logs:**
All logs are in the VM at `/tmp/koco-*.log`

To view logs:
```bash
orb -m ray-cluster bash -c "tail -f /tmp/koco-serve.log"
```

**Linux:**
```bash
just start    # Start Ray + Kodosumi + deploy
just stop     # Stop all services
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

**Analyzer-Only Pattern** (Setup Agent):
- Sub-agent analyzes system state (prerequisites, config, services)
- Creates TodoWrite list showing completed vs pending items
- Main agent executes pending todos with user approvals
- Benefits: Full visibility, individual control, progress tracking
- Example: `/cc-setup` command

### State Tracking

**Deployment state** (`.claude/.last-deploy-state.json`):
```json
{
  "timestamp": "2025-11-03T12:30:00Z",
  "master_config_commit": "abc123",
  "project_config_commit": "def456",
  "docker_image_tag": "ghcr.io/<user>/claude-hitl-worker:latest",
  "docker_image_digest": "sha256:abc123def456...",
  "build_timestamp": "2025-11-03T12:28:45Z",
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
COPY project/.claude /app/.claude                      # Project config
ENV HOME=/app/template_user  # "user" settings load from master
```

```python
# agent.py - Settings merge
ClaudeAgentOptions(
    setting_sources=["user", "project", "local"]
    # user = $HOME/.claude (master config)
    # project = {cwd}/.claude (project config)
    # local = runtime overrides (not used in this template)
)
```

### Container Folder Structure

Docker images contain this complete folder layout:

```
/app/
├── template_user/.claude/          # Master config (user-level)
│   ├── settings.json               # Marketplaces + enabled plugins
│   └── CLAUDE.md                   # Master instructions
│
├── .claude/                        # Project config (project-specific)
│   ├── settings.json               # Project overrides
│   └── CLAUDE.md                   # Project instructions
│
├── plugins/                        # Baked marketplace plugins
│   ├── cc-marketplace-developers/
│   │   └── plugins/
│   │       ├── general/
│   │       └── claude-agent-sdk/
│   └── cc-marketplace-agents/
│       └── plugins/
│           ├── master-core/        # /cc-setup, /cc-deploy, etc.
│           └── hitl-example/
│
└── claude_hitl_template/           # Application code
    ├── agent.py
    └── query.py
```

**Key details**:
- **HOME=/app/template_user**: SDK's "user" settings load from master config
- **Ownership**: All config directories owned by `ray:users` for proper permissions
- **Plugins**: Baked at build time from marketplace repos
- **Settings merge**: Project overrides master (via `setting_sources=["user", "project", "local"]`)

---

## File Organization

### Where Things Live

```
claude_hitl_template/
├── agent.py (282 lines)      # All Claude SDK logic + Ray Actors
│                              # - ClaudeSessionActor class
│                              # - create_actor, get_actor, cleanup_actor
│                              # - Plugin loading functions
│                              # - Pure business logic
│
└── query.py (276 lines)       # Kodosumi HITL orchestration only
                               # - Form definition (prompt_form)
                               # - Entry point (@app.enter)
                               # - Orchestration (run_conversation)
                               # - No Claude SDK logic here

.claude/
├── CLAUDE.md                  # Project-specific instructions
├── settings.json              # Marketplace + plugin config
│                              # - extraKnownMarketplaces
│                              # - enabledPlugins
│                              # - permissions (auto-approvals)
│
├── .last-deploy-state.json    # Deployment state (gitignored)
└── .setup-state.json          # Setup state (gitignored)

# Commands, agents, and skills now come from plugins:
# - Installed via settings.json marketplace declarations
# - Development: Auto-installed by Claude Code CLI
# - Deployment: Baked into container at /app/plugins/
# See "Plugin Architecture" section above for details

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

**For project-specific operations** (not shared across projects):
1. Create plugin in marketplace repo or local `.claude/` directory
2. **Agent**: `agents/my-agent.md` (orchestration logic)
3. **Skill** (optional): `skills/my-skill/` (reusable capability)
4. **Command**: `commands/my-command.md` (entry point)
5. **Permissions**: Update `settings.json`

**For shared operations** (reusable across projects):
1. Create plugin in your marketplace repository
2. Follow marketplace plugin structure
3. Add marketplace to `settings.json` (`extraKnownMarketplaces`)
4. Enable plugin in `settings.json` (`enabledPlugins`)

**Pattern to follow**: See `master-core@cc-marketplace-agents` plugin structure.

### Skill Structure Pattern

Each skill follows this standard structure:

```
skills/<skill-name>/
├── SKILL.md              # Documentation (frontmatter + usage)
└── scripts/
    └── <script-name>.sh  # Executable scripts
```

**When creating new skills:**
- Place all executable code in `scripts/` subdirectory
- Keep SKILL.md at the root for documentation
- This separates concerns: documentation vs implementation
- Allows multiple scripts per skill if needed
- Makes it easy to add tests/ or lib/ folders later

**Example (in marketplace or local .claude/)**:
```bash
# Create new skill structure
mkdir -p skills/my-skill/scripts
touch skills/my-skill/SKILL.md
touch skills/my-skill/scripts/run.sh
chmod +x skills/my-skill/scripts/run.sh
```

### Add Configuration
**Development**: `data/config/claude_hitl_template.yaml.example`
**Deployment**: User copies to `claude_hitl_template.yaml` and customizes

**IMPORTANT**: YAML configuration files require literal values, not variable references.

Ray Serve YAML does NOT support shell variable substitution:
- ✗ **Wrong**: `ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"`
- ✓ **Correct**: `ANTHROPIC_API_KEY: "sk-ant-your-actual-key-here"`

All values in `runtime_env.env_vars` must be copied exactly from `.env` file as literal strings. This applies to:
- `ANTHROPIC_API_KEY` - Copy the actual sk-ant-... key
- `CONTAINER_IMAGE_URI` - Copy the full URI with digest

**Why both files?**
- `.env` → Read by Python code via `os.getenv()` (shell environment)
- `yaml` → Read by Ray Serve to configure runtime environment (YAML parser, no shell expansion)
- Both must contain identical literal values for consistent configuration

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
just stop && just start  # Clean restart
```

**Ray actors stuck in PENDING_CREATION**:
```bash
# Fix /tmp/ray permissions (for containerized actors)
orb -m ray-cluster bash -c "sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"
```
See: [Container Runtime Issues](docs/TROUBLESHOOTING.md#container-runtime-issues)

**Can't reach Ray Dashboard**:
```bash
just start  # Start all services
curl http://localhost:8265  # Test accessibility
```

**Container image not found**:
- Check digest in `.env` matches `data/config/claude_hitl_template.yaml`
- Use registry digest from `.RepoDigests`, not local `.Digest`
- See: [Container Image Digests](docs/TROUBLESHOOTING.md#container-image-digests-local-vs-registry)

**Podman user namespace errors**:
```bash
# Configure subordinate UID/GID ranges
orb -m ray-cluster bash -c "sudo bash -c 'echo sebkuepers:100000:65536 >> /etc/subuid && echo sebkuepers:100000:65536 >> /etc/subgid'"
orb -m ray-cluster bash -c "podman system migrate"
```
See: [User Namespace Configuration](docs/TROUBLESHOOTING.md#user-namespace-configuration-for-rootless-podman)

**SSH/rsync errors (macOS)**:
- Use `ray-cluster@orb` format (not `ray-cluster.orb.local`)
- OrbStack handles SSH keys automatically
- Check VM running: `orb list | grep ray-cluster`

**Docker/Podman build fails**:
- Check GITHUB_TOKEN in .env
- Verify Docker/Podman running
- See: [Build Issues](docs/TROUBLESHOOTING.md#build-issues)

**CRITICAL - VM Directory Structure**:
- **NEVER** sync macOS `.venv` to VM - it has wrong architecture binaries
- VM has its own venv at `~/.venv` (Linux binaries)
- Project at `~/dev/cc-hitl-template/.venv` is a **symlink** to `~/.venv`
- When syncing project: `rsync -avz --exclude='.venv' ./ ray-cluster@orb:~/dev/cc-hitl-template/`
- If packages missing in VM: `orb -m ray-cluster bash -c "source ~/.venv/bin/activate && cd ~/dev/cc-hitl-template && pip install -e ."`
- Justfile runs **from macOS** but executes **in VM** via `orb -m ray-cluster bash -c "..."`

For comprehensive solutions: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## Immutable Container Environment

### Understanding Container Immutability

**CRITICAL**: Containerized agents run in **immutable Docker environments**.

**What this means**:
- ✗ **Cannot install** packages via pip, npm, apt at runtime
- ✗ **No write access** to system directories or package managers
- ✓ **Can use** any packages baked into the container at build time
- ✓ **Can check** available packages via `/app/.dependency-manifest.json`

**All runtime dependencies must be declared in config repositories before building the container.**

### Dependency Manifest

Every container includes `.dependency-manifest.json` listing installed packages:

```bash
# Check what's available in your container
cat /app/.dependency-manifest.json | jq '.'

# List installed Python packages
pip list

# List installed Node.js packages
npm list -g --depth=0
```

**Example manifest**:
```json
{
  "timestamp": "2025-11-06T10:30:00Z",
  "source": "Config repositories (master + project)",
  "python_packages": ["beautifulsoup4>=4.12.0", "lxml>=4.9.0"],
  "nodejs_packages": ["docx", "puppeteer"],
  "system_packages": ["chromium", "chromium-driver"]
}
```

### Working with Missing Dependencies

**If a skill/task requires a package not in the manifest**:

1. **DO NOT** attempt installation (will fail)
2. **Check alternatives** using available packages
3. **Communicate clearly** to the user about the limitation
4. **Suggest addition** for future container builds

**Communication Pattern**:
```markdown
⚠️ **Dependency Limitation**

**Task**: Generate Word document report

**Missing Package**: `docx` (Node.js package for .docx generation)

**Current Approach**: Generating Markdown report instead

**To Add This Capability**:
1. Add `"docx": "^8.5.0"` to config repo's `dependencies/package.json`
2. Rebuild container: Run `/cc-deploy` (will detect dependency change)
3. Next execution will have Word export capability

**Would you like me to proceed with the Markdown report?**
```

### Helper Function for Agents

Use `send_dependency_suggestion()` from `query.py` to communicate missing dependencies:

```python
from claude_hitl_template.query import send_dependency_suggestion

# When you detect a missing dependency
response = await send_dependency_suggestion(
    tracer=tracer,
    task="Generate Word document",
    missing_packages=[{
        "name": "docx",
        "type": "nodejs",
        "purpose": "Create .docx files with formatting"
    }],
    current_approach="Generate Markdown report instead",
    ask_user=True
)

if response and response.get("proceed") == "no":
    await tracer.markdown("Please add dependencies and rebuild, then try again.")
    return
```

### Best Practices for Agents

1. **Check Before Using**: Verify packages exist before importing
   ```python
   try:
       import beautifulsoup4
       has_bs4 = True
   except ImportError:
       has_bs4 = False
   ```

2. **Graceful Degradation**: Offer alternatives when deps missing
   ```python
   if has_docx:
       await generate_word_report()
   else:
       await generate_markdown_report()
       await send_dependency_suggestion(...)
   ```

3. **Clear Communication**: Explain what's possible vs. what's not

4. **Suggest Improvements**: Help users understand how to add capabilities

### For Template Users

**Adding new dependencies**:

See: [docs/DEPENDENCY-MANAGEMENT.md](docs/DEPENDENCY-MANAGEMENT.md) for user guide
See: [specs/immutable-container-dependencies.md](specs/immutable-container-dependencies.md) for complete system documentation

**Quick steps**:
1. Edit config repo's `dependencies/` files (requirements.txt, package.json, etc.)
2. Commit and push changes
3. Run `/cc-deploy` to rebuild container with new dependencies
4. Test with new capabilities available

---

**This is a Claude Code first template. Use `/cc-setup` to get started!**
