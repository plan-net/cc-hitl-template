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

### Prerequisites
- Python 3.12+ (pyenv recommended)
- Claude Code CLI (required for authentication)
- kodosumi v1.0.0+
- Ray cluster

### Installation
```bash
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Verify Claude Code CLI
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

### Core Components

#### `claude_hitl_template/agent.py` (26 lines)
- **Purpose**: Minimal placeholder for business logic
- **Current**: Simple `process_message()` echo function
- **Extend with**: API calls, data processing, custom tools

#### `claude_hitl_template/query.py` (307 lines)
- **Purpose**: Main Kodosumi + Claude SDK integration
- **Key Sections**:
  1. **Form Definition** (`prompt_form`) - Input form
  2. **Entry Point** (`@app.enter()`) - Validation & launch
  3. **Conversation Loop** (`run_conversation()`) - HITL logic
  4. **Summary Helper** (`_show_conversation_summary()`) - Display stats

### Key Patterns

#### HITL Pattern (Human-in-the-Loop)
```python
# After Claude responds, pause and get user input
user_input = await tracer.lease(
    "claude-input",
    F.Model(
        F.InputArea(label="Your Response", name="response"),
        F.Submit("Send")
    )
)

# Resume conversation
await client.query(user_input["response"])
```

#### Claude SDK Integration
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

# Initialize
client = ClaudeSDKClient(
    options=ClaudeAgentOptions(
        permission_mode="acceptEdits",
        cwd="/path/to/project"
    )
)

# Connect and start
await client.connect(prompt)

# Stream responses
async for message in client.receive_response():
    if isinstance(message, AssistantMessage):
        # Process text blocks
        ...
    elif isinstance(message, ResultMessage):
        # Task complete
        break
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
