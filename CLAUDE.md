# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Claude + Kodosumi HITL Template** is a minimal, reusable template demonstrating how to integrate Claude Agent SDK with Kodosumi's Human-in-the-Loop (HITL) functionality.

**Purpose**: Serve as a starting point for building interactive AI agents with back-and-forth conversation capabilities.

**Compatibility**: Optimized for:
- Python 3.12+
- Claude Agent SDK 0.1.6+
- Kodosumi 1.0.0+
- Ray 2.47.1+

## Development Setup

### Recommended: Hybrid Setup (macOS Users)

For macOS users, we recommend the **hybrid approach** where Ray cluster runs in OrbStack Linux VM while development happens on macOS:

**Why?** Ray's `image_uri` container feature requires native Linux networking. On macOS, Podman uses QEMU VM which breaks Ray's `127.0.0.1` assumptions.

**Benefits:**
- Native Linux Ray cluster (containers work as designed)
- macOS development experience (familiar IDE, tools)
- Lightweight (<0.1% CPU background usage)
- Automatic port forwarding

See **[docs/ORBSTACK_SETUP.md](docs/ORBSTACK_SETUP.md)** for complete setup guide.

### Alternative: Native Linux or Remote Cluster

If you're on Linux or have access to a remote Ray cluster:

#### Prerequisites
- Python 3.12+ (pyenv recommended)
- Claude Code CLI (required for authentication)
- kodosumi v1.0.0+
- Ray cluster (local or remote)

#### Installation
```bash
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

#### Verify Claude Code CLI
```bash
claude --version
# If not installed: https://docs.claude.com/en/docs/claude-code
```

## Commands

### Development Workflow
- `just start` - Start full stack (Ray + Kodosumi deployment + spooler + admin panel)
- `just stop` - Stop all services
- `just test` - Run tests
- `just status` - Check service status
- `just clean` - Clean temp files/caches

### Manual Workflow (if needed)
```bash
source .venv/bin/activate

# 1. Start Ray cluster
ray start --head --disable-usage-stats

# 2. Deploy application
koco deploy -r

# 3. Start execution spooler (REQUIRED!)
koco spool &

# 4. Start admin panel
koco serve --register http://localhost:8001/-/routes

# Access at http://localhost:3370
```

## Architecture

### Why Containers? (Optional but Recommended)

This template supports **optional containerization** via `use_container=True` when creating actors. Here's why you might want to use it:

**Problem**: Claude SDK uses `.claude/` folders for configuration (settings, commands, skills). In production scenarios with multiple concurrent sessions, you may want isolation between:
- **Template behavior** - Generic `.claude/` configuration for all instances
- **Project-specific behavior** - Custom `.claude/` configuration per deployment
- **User configurations** - Avoiding mixing with personal `~/.claude/` settings

**Solution**: Run ClaudeSessionActors in containers with:
1. `template_user/.claude/` baked into Docker image (generic template)
2. Project `.claude/` mounted from deployed code (project-specific)
3. Settings merged via `ClaudeAgentOptions(setting_sources=["user", "project", "local"])`

**When to use containers:**
- Production deployments with multiple concurrent conversations
- Need to isolate `.claude/` configurations between instances
- Want reproducible execution environment
- Running on Linux (native) or hybrid setup (OrbStack)

**When to skip containers** (`use_container=False`):
- Local development/testing on macOS without OrbStack
- Single-user scenarios
- Simpler setup without Docker/Podman

See `claude_hitl_template/agent.py:268-323` and `Dockerfile` for implementation details.

### Ray Actor Pattern

This template uses **Ray Actors** to solve the Claude SDK subprocess lifecycle problem.

**Architecture Overview:**
```
┌──────────────────────────────┐
│ query.py (Kodosumi only)     │  ← Lean orchestration
└────────────┬─────────────────┘
             │ create_actor()
             ▼
┌──────────────────────────────┐
│ ClaudeSessionActor (agent.py) │  ← Persistent subprocess manager
│ - Named: "claude-session-{id}"│
│ - Resources: 1 CPU, 512MB     │
└────────────┬─────────────────┘
             │ Manages
             ▼
┌──────────────────────────────┐
│ Claude Code CLI subprocess    │  ← Node.js process
└──────────────────────────────┘
```

**Why Ray Actors?**
- Claude SDK requires long-running subprocess (Node.js CLI)
- Direct subprocess spawning in Ray Serve workers fails during HITL pauses
- Actors provide persistent, stateful processes that survive HITL pauses
- Named actors can be retrieved after worker state changes

### Core Components

#### `claude_hitl_template/agent.py` (282 lines)
- **Purpose**: All Claude SDK logic using Ray Actors
- **Key Classes**:
  1. **ClaudeSessionActor** (`@ray.remote`) - Persistent Ray Actor
     - `connect(prompt)`: Initialize Claude SDK subprocess
     - `query(message)`: Send message and collect response batch
     - `check_timeout()`: Detect idle timeout (11 minutes)
     - `disconnect()`: Cleanup subprocess
  2. **Helper Functions**:
     - `create_actor(execution_id)`: Spawn named actor with resources
     - `get_actor(execution_id)`: Retrieve existing actor
     - `cleanup_actor(execution_id)`: Disconnect and kill actor

#### `claude_hitl_template/query.py` (276 lines)
- **Purpose**: Lean Kodosumi orchestration only
- **Key Sections**:
  1. **Form Definition** (`prompt_form`) - Input form
  2. **Entry Point** (`@app.enter()`) - Validation & launch
  3. **Orchestration** (`run_conversation()`) - Actor lifecycle & HITL
  4. **Summary Helper** (`_show_conversation_summary()`) - Display stats

### Key Patterns

#### Ray Actor Pattern
```python
from .agent import create_actor, get_actor, cleanup_actor

# Create persistent actor
actor = create_actor(execution_id)

# Connect and get initial response
result = await actor.connect.remote(initial_prompt)

# Display messages
for msg in result["messages"]:
    await tracer.markdown(f"Claude: {msg['content']}")

# HITL pause (actor stays alive!)
user_input = await tracer.lease("claude-input", F.Model(...))

# Resume - retrieve actor (handles worker restarts)
actor = get_actor(execution_id)
result = await actor.query.remote(user_input["response"])

# Cleanup
await cleanup_actor(execution_id)
```

#### HITL Pattern (Human-in-the-Loop)
```python
# After displaying Claude's response, pause for user input
user_input = await tracer.lease(
    "claude-input",
    F.Model(
        F.InputArea(label="Your Response", name="response"),
        F.Submit("Send"),
        F.Cancel("End Conversation")
    )
)

# Send to actor (not direct client)
result = await actor.query.remote(user_input["response"])
```

#### Runtime Environment Configuration
```yaml
# data/config/claude_hitl_template.yaml
runtime_env:
  pip:
    - claude-agent-sdk>=0.1.6  # Required for actor workers
  env_vars:
    OTEL_SDK_DISABLED: "true"
```

### Configuration Files

**`data/config/config.yaml`** - Global Ray Serve config
**`data/config/claude_hitl_template.yaml`** - Service-specific config:
```yaml
name: claude_hitl_template
route_prefix: /claude-hitl
import_path: claude_hitl_template.query:fast_app
```

### Key Dependencies
- `claude-agent-sdk` - Claude Agent SDK for conversation
- `kodosumi` - Service framework with HITL support
- `ray` - Distributed computing
- `python-dotenv` - Environment variables
- `pytest` - Testing framework

## Code Style & Conventions

### When Extending This Template

1. **Keep `agent.py` lean** - Pure business logic only
2. **Kodosumi integration stays in `query.py`** - All UI, forms, HITL
3. **Use type hints** - For function parameters and returns
4. **Add docstrings** - Explain purpose, args, returns
5. **Follow existing patterns** - HITL via `tracer.lease()`, Claude SDK via `async for`

### Adding New Features

**Example: Add custom tool for Claude**
```python
# In query.py or new tools.py
from claude_agent_sdk import tool

@tool("calculator", "Performs calculations", {"expression": str})
async def calculator_tool(args: dict) -> dict:
    result = eval(args["expression"])  # Use safe eval in production!
    return {"content": [{"type": "text", "text": str(result)}]}
```

**Example: Add API integration**
```python
# In agent.py
import os
import requests

def fetch_external_data(query: str) -> dict:
    api_key = os.getenv("EXTERNAL_API_KEY")
    response = requests.get(
        f"https://api.example.com/search?q={query}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    return response.json()
```

## Testing

### Run Tests
```bash
just test  # All tests
pytest tests/ -v  # Verbose
pytest tests/test_basic.py::test_agent_process_message  # Specific test
```

### Test Structure
- `tests/test_basic.py` - Smoke tests for imports and basic functionality
- Add new tests in `tests/` directory
- Use pytest markers if needed

## Troubleshooting

### Common Issues

**Claude SDK Import Errors**
- Ensure Claude Code CLI is installed: `claude --version`
- Reinstall SDK: `pip install --upgrade claude-agent-sdk`

**Ray Cluster Won't Start**
- Check if already running: `ray status`
- Stop and restart: `ray stop && ray start --head --disable-usage-stats`

**Kodosumi Deployment Fails**
- Verify spooler is running: `koco spool &` (REQUIRED!)
- Check logs: `koco logs`
- Redeploy: `koco deploy -r`

**Hardcoded Path in query.py**
- Line 137 has hardcoded `cwd` - update for your project:
  ```python
  cwd=os.getcwd()  # Use current directory
  # OR
  cwd="/your/project/path"
  ```

**ProcessTransport Error in Local Development**

**Error**: `CLIConnectionError: ProcessTransport is not ready for writing`

**Root Cause**: Ray's `runtime_env.pip` creates an isolated virtualenv that modifies PATH. When ClaudeSDKClient spawns the Claude CLI subprocess, it can't find `node` or `claude` binaries because the virtualenv's PATH doesn't include system binary directories like `/opt/homebrew/bin` or `/usr/local/bin`.

**Solution**: Add system binary paths to `runtime_env.env_vars.PATH` in `claude_hitl_template.yaml`:

```yaml
runtime_env:
  pip:
    - claude-agent-sdk>=0.1.6
  env_vars:
    OTEL_SDK_DISABLED: "true"
    ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"

    # macOS with Homebrew - add system binary paths
    PATH: "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:${PATH}"

    # OR for Linux
    # PATH: "/usr/local/bin:/usr/bin:/bin:${PATH}"
```

**Why this works**: Ray merges `runtime_env.env_vars` with the worker environment. The `${PATH}` expands to the existing PATH, and system paths are prepended so `which node` finds your installation. ClaudeSDKClient's subprocess inherits this corrected PATH.

**Testing**:
```bash
# Stop services
just stop

# Restart with updated config
just start

# Test conversation - should work without ProcessTransport error
```

## Known Issues & Workarounds

### Claude Agent SDK v0.1.6: connect(prompt) Bug

**Issue**: The documented pattern `await client.connect("prompt string")` causes `CLIConnectionError: ProcessTransport is not ready for writing`.

**Root Cause**:
- When passing a string prompt to `connect()`, the SDK closes stdin immediately (non-streaming mode)
- However, the Claude CLI subprocess expects stdin to remain open for the control protocol
- This causes EPIPE (broken pipe) errors when the CLI tries to write responses
- Related GitHub issues: [#176](https://github.com/anthropics/claude-agent-sdk-python/issues/176), [#266](https://github.com/anthropics/claude-agent-sdk-python/issues/266)

**Official Documentation Says:**
```python
# Should work according to docs (v0.1.6)
await client.connect("your prompt here")  # ❌ BROKEN - causes ProcessTransport error
async for msg in client.receive_response():
    print(msg)
```

**Working Workaround (Also Documented):**
```python
# Use connect(None) + query() pattern instead
await client.connect(None)  # ✅ Keeps stdin open for control protocol
await client.query("your prompt here")  # ✅ Works correctly
async for msg in client.receive_response():
    print(msg)
```

**Why This Works:**
- `connect(None)` creates an empty async generator internally
- This is treated as streaming mode, so stdin stays open
- The control protocol can communicate bidirectionally
- Both patterns are documented, but only one works in v0.1.6

**Impact on This Template:**
Our `ClaudeSessionActor.connect()` method (agent.py:65-97) uses the working pattern. This is not a workaround—it's a legitimate API usage documented in the official SDK docs. We simply chose the working pattern over the broken one.

**Future**: This bug may be fixed in future SDK versions. When upgrading, test both patterns to see if the string-prompt mode works again.

## Known Limitations & Requirements

### System Dependencies (Critical)

The Ray Actor implementation requires these to be pre-installed on ALL Ray worker nodes:

#### 1. Node.js 18+
- **Why**: Claude SDK requires Node.js to run Claude Code CLI subprocess
- **Local Dev**: Already installed on your machine
- **Production**: Must pre-install in container image or worker nodes

```bash
# Verify Node.js is available
node --version  # Should be 18.0.0 or higher
```

#### 2. Claude Code CLI
- **Why**: ClaudeSDKClient spawns this as subprocess
- **Local Dev**: Install globally with `npm install -g @anthropic-ai/claude-code`
- **Production**: Include in container image

```bash
# Verify Claude CLI is available
claude --version
```

#### 3. Authentication via ANTHROPIC_API_KEY
- **Why**: Claude SDK needs API key to make requests
- **Local Dev**: Set in `.env` file and load before starting
- **Production**: Set as environment variable in deployment

```bash
# Local development setup
cp .env.example .env
# Edit .env and add your API key
source .env
export ANTHROPIC_API_KEY
```

### Why Ray Actors Can't Install These

Ray's `runtime_env.pip` **only installs Python packages**. It cannot install:
- System binaries like Node.js
- npm packages like Claude Code CLI
- Operating system dependencies

These must be pre-installed on worker nodes or in container images.

### Local Development Setup

For local development, the good news is that Ray workers run on your local machine,
so they have access to the same Node.js and Claude CLI you've already installed.

```bash
# 1. Verify Node.js and Claude CLI
node --version
claude --version

# 2. Set up authentication
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Create config from example
cp data/config/claude_hitl_template.yaml.example data/config/claude_hitl_template.yaml

# 4. Load environment and start
source .env
export ANTHROPIC_API_KEY
just start
```

### Production Deployment

#### Hybrid Setup (macOS Development)

For macOS users using OrbStack, follow the hybrid approach:
1. Ray cluster runs in OrbStack Linux VM
2. Development code stays on macOS
3. Build Docker image inside the VM
4. Connect from macOS via Ray Client

See **[docs/ORBSTACK_SETUP.md](docs/ORBSTACK_SETUP.md)** for complete guide.

#### Native Linux Deployment

For Linux servers or production clusters, build the container image:

```bash
# Build the Docker image
docker build -t claude-hitl-worker:latest .

# Start Ray cluster
ray start --head --disable-usage-stats

# Deploy
koco deploy -r
```

The `Dockerfile` includes all system dependencies (Node.js 18, Claude CLI) required for containerized actors.

See README.md for full deployment details.

### Resource Requirements

- **Memory**: 1GB per actor (conversation session)
- **Disk**: 5GB recommended for Claude CLI cache
- **CPU**: 1 CPU core per actor
- **Network**: Outbound HTTPS to `api.anthropic.com`

## Best Practices

### For Template Users

1. **Start Simple** - Use this template as-is first, then customize
2. **Test Locally** - Always test with `just start` before deploying
3. **Remove Hardcoding** - Update paths, API keys to use env vars
4. **Add Error Handling** - Expand error handling in production
5. **Monitor Timeouts** - Adjust `CONVERSATION_TIMEOUT_SECONDS` as needed

### For Developers Extending

1. **Preserve HITL Pattern** - Keep `tracer.lease()` structure intact
2. **Maintain Async Flow** - All Claude SDK calls are async
3. **Track Conversation History** - Maintain `conversation_history` list
4. **Handle Termination** - Multiple exit conditions (timeout, user, Claude)
5. **Clean Up Resources** - Always disconnect Claude SDK in `finally` block

## Architecture Decision Records

### Why Kodosumi + Claude SDK?
- **Kodosumi**: Provides HITL, deployment, Ray integration
- **Claude SDK**: Native Claude conversation API
- **Together**: Best of both - interactive UI + powerful AI

### Why Minimal Template?
- Easy to understand and extend
- No unnecessary abstractions
- Clear extension points
- ~300 lines total - readable in one sitting

### Key Design Choices
1. **Single `query.py` file** - All integration logic in one place for clarity
2. **Minimal `agent.py`** - Placeholder to show where business logic goes
3. **No external APIs** - Template doesn't require API keys
4. **Explicit HITL** - Shows exact pattern for pause/resume
5. **Conversation tracking** - Simple list for extensibility

## Kodosumi Patterns & Gotchas

### InputsError API
**Wrong:**
```python
error = InputsError()
error.add("field", "message")  # ❌ Positional args don't work
error.check()  # ❌ Method doesn't exist
```

**Correct:**
```python
error = InputsError()
error.add(field_name="message")  # ✅ Keyword argument
if error.has_errors():  # ✅ Correct method
    raise error
```

### Launch Execution Function Signature
**Wrong:**
```python
async def run_task(request: fastapi.Request, tracer: Tracer, inputs: dict):
    # ❌ Launch doesn't pass request
```

**Correct:**
```python
async def run_task(inputs: dict, tracer: Tracer):
    # ✅ Only inputs and tracer, in this order
```

The `request` object is only available in `@app.enter()` handlers, not in launched execution functions.

### Ray Serve Deployment Wrapper
**Wrong:**
```python
app = ServeAPI()
# ...
fast_app = app  # ❌ Direct export doesn't work
```

**Correct:**
```python
app = ServeAPI()
# ...
@serve.deployment
@serve.ingress(app)
class MyService:
    pass

fast_app = MyService.bind()  # ✅ Wrapped with Ray Serve deployment
```

This pattern is **required** for Kodosumi applications deployed via Ray Serve.

### Deployment Configuration
**Wrong:**
```yaml
runtime_env:
  working_dir: .  # ❌ Ray Serve rejects this
  pip:
    - package>=1.0.0
```

**Correct:**
```yaml
# Don't specify runtime_env if dependencies are in venv
# OR specify without working_dir:
runtime_env:
  env_vars:
    MY_VAR: "value"
```

## Claude SDK Integration Challenges

### The Subprocess Problem

**Issue:** `ClaudeSDKClient` spawns the Claude Code CLI as a subprocess:
```python
client = ClaudeSDKClient(options=...)
await client.connect(prompt)  # Spawns `claude` CLI process
```

**Error in Ray Serve workers:**
```
CLIConnectionError: ProcessTransport is not ready for writing
```

**Why it fails:**
1. Ray Serve workers are isolated processes
2. They may not have access to Claude Code CLI executable
3. Authentication/credentials not available in worker context
4. Subprocess spawning restricted or unreliable

### Claude SDK Hosting Requirements

Per [Claude SDK hosting docs](https://docs.claude.com/en/api/agent-sdk/hosting):
- Claude SDK is designed for **long-running container processes**
- Not for stateless request handlers
- Requires persistent session across interactions
- Needs sandboxed container environment per session

**Our current architecture mismatch:**
- ✅ Kodosumi: Stateless request handling
- ❌ Claude SDK: Expects long-running process
- 🔄 **Solution**: Use Ray Actors for persistence

## Architecture Decision: Ray Actors for Claude SDK

### Why Ray Actors?

**Problem:** Claude SDK needs long-running process, but Ray Serve workers are stateless.

**Solution:** Use Ray Actors as persistent session containers:

```python
@ray.remote
class ClaudeConversationActor:
    """
    Persistent Ray Actor maintaining Claude SDK session.
    One actor per user conversation.
    """
    def __init__(self, prompt: str):
        self.client = ClaudeSDKClient(...)
        # Initialize in actor's persistent context

    async def send_message(self, message: str):
        # SDK subprocess persists in actor
        return await self.client.query(message)

    async def cleanup(self):
        await self.client.disconnect()
```

### Actor Lifecycle Pattern

```
User starts conversation
    ↓
Create Ray Actor (new persistent session)
    ↓
Actor spawns Claude SDK subprocess
    ↓
HITL Loop:
  User → Kodosumi → Ray Actor → Claude SDK → Response
  ↓
  Actor persists between HITL interactions
    ↓
Conversation ends (timeout or user done)
    ↓
Destroy Ray Actor (cleanup subprocess)
```

### Benefits

1. **Persistence** - Actor maintains state across HITL interactions
2. **Isolation** - Each conversation has dedicated actor/subprocess
3. **Lifecycle Control** - Create on start, destroy on end/timeout
4. **Ray Native** - Fits existing Kodosumi + Ray architecture

### Implementation Status

🚧 **TO DO**: Refactor `run_conversation()` to use Ray Actor pattern instead of direct ClaudeSDKClient instantiation.

## Current Status & Known Limitations

### ✅ Working

- Kodosumi service deployment (Ray Serve + Kodosumi patterns)
- Form submission and input validation
- HITL pattern structure (`tracer.lease()`)
- Basic execution flow with async Launch
- Configuration and deployment via `koco deploy`

### ⚠️ Partial / In Progress

- **Claude SDK Integration**: Needs Ray Actor refactor
  - Current: Direct subprocess spawn fails in workers
  - Planned: Ray Actor wrapper for persistent sessions

### 🚧 Next Steps

1. Implement `ClaudeConversationActor` Ray Actor class
2. Refactor `run_conversation()` to create/use actor
3. Add actor lifecycle management (create, persist, cleanup)
4. Test HITL flow with actor-based Claude SDK
5. Add timeout and cleanup handlers

## Extended Troubleshooting

### Error: `AttributeError: 'InputsError' object has no attribute 'check'`

**Cause:** Incorrect InputsError API usage

**Fix:**
```python
# Change from:
error.check()

# To:
if error.has_errors():
    raise error
```

### Error: `runtime_envs support only remote URIs in working_dir`

**Cause:** Invalid `working_dir: .` in deployment config

**Fix:** Remove the `runtime_env` section if dependencies are in venv:
```yaml
# Remove this entire section:
runtime_env:
  working_dir: .
  pip: [...]
```

### Error: `Expected a built Serve application but got: <class 'ServeAPI'>`

**Cause:** Missing Ray Serve deployment wrapper

**Fix:** Add the wrapper pattern:
```python
@serve.deployment
@serve.ingress(app)
class MyService:
    pass

fast_app = MyService.bind()
```

### Error: `run_conversation() missing 1 required positional argument: 'request'`

**Cause:** Wrong function signature for Launch execution

**Fix:** Remove `request` parameter:
```python
# Change from:
async def run_conversation(request: Request, tracer: Tracer, inputs: dict):

# To:
async def run_conversation(inputs: dict, tracer: Tracer):
```

### Error: `CLIConnectionError: ProcessTransport is not ready for writing`

**Cause:** Claude SDK trying to spawn subprocess in Ray Serve worker

**Status:** Known limitation - requires Ray Actor refactor

**Workaround:** (Temporary) Use Anthropic API directly, or wait for Ray Actor implementation

**Permanent Fix:** Implement Ray Actor wrapper for ClaudeSDKClient (see Architecture Decision section)

### Ray Version Mismatch

**Symptom:**
```
RuntimeError: Version mismatch: The cluster was started with:
    Ray: 2.51.1
This process was started with:
    Ray: 2.47.1
```

**Cause:** Ray cluster started outside venv or with different Ray version

**Fix:**
```bash
# Stop existing cluster
ray stop

# Activate venv
source .venv/bin/activate

# Verify Ray version
ray --version

# Start fresh cluster
just start
```

## Related Resources

- [Claude Agent SDK Python Docs](https://docs.claude.com/en/api/agent-sdk/python)
- [Claude SDK Hosting Guide](https://docs.claude.com/en/api/agent-sdk/hosting)
- [Claude Code CLI](https://docs.claude.com/en/docs/claude-code)
- [Kodosumi Documentation](https://kodosumi.dev)
- [Ray Serve Guide](https://docs.ray.io/en/latest/serve/index.html)
- [Ray Actors Guide](https://docs.ray.io/en/latest/ray-core/actors.html)

## Support

For questions:
- **Claude SDK**: https://docs.claude.com/en/api/agent-sdk
- **Kodosumi**: Check Kodosumi docs
- **This Template**: See README.md
