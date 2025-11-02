# Claude + Kodosumi HITL Template

A minimal template demonstrating how to integrate **Claude Agent SDK** with **Kodosumi's Human-in-the-Loop (HITL)** functionality.

## Status

**Fully Functional** ✅

This template is production-ready with Ray Actor-based Claude SDK integration.

**Features:**
- ✅ Claude Agent SDK integration via Ray Actors
- ✅ Persistent conversation sessions across HITL interactions
- ✅ Kodosumi service deployment with Ray Serve
- ✅ Back-and-forth conversation with timeout detection
- ✅ Proper subprocess lifecycle management

**Known Limitations:**
- ⚠️ SDK Bug: `connect(prompt_string)` broken in v0.1.6 - we use `connect(None) + query()` pattern
- See [CLAUDE.md](CLAUDE.md#known-issues--workarounds) for details and workarounds

## Overview

This template showcases a complete integration pattern for building interactive AI agents that combine:
- **Claude Agent SDK** for intelligent conversation and reasoning
- **Kodosumi** for service deployment and execution management
- **Ray Serve** for distributed computing
- **HITL (Human-in-the-Loop)** for back-and-forth interaction between Claude and users

## Features

- ✅ Simple single-prompt input form
- ✅ Kodosumi HITL integration for interactive conversations
- ✅ Ray Serve deployment with proper `@serve.deployment` wrapper
- ✅ Ray Actor pattern for persistent Claude SDK sessions
- ✅ Conversation timeout detection (11 minutes idle)
- ✅ Streaming responses from Claude
- ✅ Automatic retry on actor crashes
- ✅ Minimal, well-commented codebase (~550 lines total)

## Prerequisites

### Required Software
- **Python 3.12+** (managed via pyenv recommended)
- **Node.js 18+** - Required for Claude Code CLI
  ```bash
  # Check Node.js version
  node --version  # Should be 18.0.0 or higher
  ```
- **Claude Code CLI** - Required for Claude Agent SDK
  ```bash
  # Install Claude Code CLI
  npm install -g @anthropic-ai/claude-code

  # Verify installation
  claude --version
  ```
- **Claude Agent SDK 0.1.6** - Python SDK (installed via dependencies)
  - ⚠️ **Known Issue**: v0.1.6 has a bug with `connect(prompt_string)` pattern
  - This template uses the working `connect(None) + query()` pattern
  - See [CLAUDE.md](CLAUDE.md#known-issues--workarounds) for technical details
- **Ray** - Distributed computing framework (installed via dependencies)
- **Kodosumi v1.0.0+** - Service framework

### System Requirements
- macOS, Linux, or WSL2 on Windows
- **Node.js 18+** installed on all Ray worker nodes
- 4GB+ RAM recommended (1GB per concurrent conversation)
- Active internet connection for Claude API
- Network access to `api.anthropic.com`

### Verify Prerequisites
```bash
# Check Node.js
node --version

# Check Claude CLI
claude --version

# Check Python
python3.12 --version
```

## Quick Start

### macOS Users: Hybrid Setup (Recommended)

For macOS developers, we recommend the **hybrid approach** where the Ray cluster runs in an OrbStack Linux VM while development happens on macOS:

**Why?** Ray's `image_uri` container feature requires native Linux networking. On macOS, Podman uses a QEMU VM which breaks Ray's `127.0.0.1` assumptions, causing container actors to fail.

**Benefits:**
- Native Linux Ray cluster (containers work as designed)
- macOS development experience (IDE, git, all tools stay on macOS)
- Lightweight (<0.1% CPU when idle)
- Automatic port forwarding (no manual network config)

**Setup Guide:** See **[docs/ORBSTACK_SETUP.md](docs/ORBSTACK_SETUP.md)** for complete step-by-step setup.

**Summary:**
1. Install OrbStack: `brew install orbstack`
2. Create Ubuntu VM: `orb create ubuntu:24.04 ray-cluster`
3. Setup Ray cluster in VM (install deps, build Docker image)
4. Develop on macOS, connect via `ray.init("ray://localhost:10001")`

---

### Linux Users or Remote Cluster: Native Setup

### 1. Clone and Setup

```bash
# Navigate to project directory
cd claude-kodosumi-hitl-template

# Create virtual environment with Python 3.12+
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Authentication

```bash
# Create .env file from example
cp .env.example .env

# Edit .env and add your Anthropic API key
# Get your API key from: https://console.anthropic.com/settings/keys
nano .env  # or use your preferred editor

# Load environment variables
source .env
export ANTHROPIC_API_KEY

# Create config from example
cp data/config/claude_hitl_template.yaml.example data/config/claude_hitl_template.yaml
```

### 3. Verify Setup

```bash
# Check Claude CLI is installed
claude --version

# Check API key is set
echo $ANTHROPIC_API_KEY
```

### 4. Start the Service

```bash
# Ensure environment variables are loaded
source .env && export ANTHROPIC_API_KEY

# Start everything (Ray + Kodosumi + Admin Panel)
just start

# This will:
# 1. Start Ray cluster
# 2. Deploy the Kodosumi service
# 3. Start execution spooler (REQUIRED for executions)
# 4. Launch admin panel at http://localhost:3370
```

### 4. Access the Application

1. Open http://localhost:3370 in your browser
2. Navigate to the Claude HITL Template service
3. Enter a prompt and click "Start Conversation"
4. Interact with Claude through the HITL interface

### 5. Stop the Service

```bash
just stop
```

## Architecture

### File Structure

```
claude-kodosumi-hitl-template/
├── claude_hitl_template/
│   ├── __init__.py          # Package initializer
│   ├── agent.py             # Ray Actor + Claude SDK logic (282 lines)
│   └── query.py             # Kodosumi orchestration only (276 lines)
├── data/config/
│   ├── config.yaml          # Global Ray Serve configuration
│   └── claude_hitl_template.yaml  # Service deployment + runtime_env
├── tests/
│   ├── __init__.py
│   ├── test_basic.py        # Basic smoke tests
│   └── test_actors.py       # Ray Actor integration tests
├── justfile                 # Task runner commands
├── pyproject.toml           # Project dependencies
├── pytest.ini               # Test configuration
├── README.md                # This file
└── CLAUDE.md                # Claude Code guidance
```

### Ray Actor Architecture

```
┌─────────────────────────────────────┐
│ Kodosumi + Ray Serve                │
│ (query.py - orchestration only)     │
└──────────────┬──────────────────────┘
               │
               │ Create/retrieve actors
               ▼
┌─────────────────────────────────────┐
│ ClaudeSessionActor (agent.py)       │
│ - Persistent subprocess manager     │
│ - Named: "claude-session-{id}"      │
│ - Resources: 1 CPU, 512MB           │
└──────────────┬──────────────────────┘
               │
               │ Manages subprocess
               ▼
┌─────────────────────────────────────┐
│ Claude Code CLI (Node.js)           │
│ - Claude API communication          │
│ - Isolated process                  │
└─────────────────────────────────────┘
```

**Key Benefits:**
- Actor persists across HITL pauses
- Subprocess stays alive during conversation
- Auto-retry on Actor crashes
- Timeout-based cleanup prevents leaks

### Component Breakdown

#### `agent.py` - Ray Actor + Claude SDK (282 lines)

**All Claude SDK logic lives here:**

1. **ClaudeSessionActor** (Ray Actor class):
   - Owns ClaudeSDKClient instance with subprocess
   - `connect()`: Initializes Claude SDK and collects first response
   - `query()`: Sends message and collects response batch
   - `check_timeout()`: Detects idle timeout (11 minutes)
   - `disconnect()`: Cleans up subprocess

2. **Helper Functions**:
   - `create_actor()`: Spawns named actor with resources (1 CPU, 512MB)
   - `get_actor()`: Retrieves actor by execution ID
   - `cleanup_actor()`: Disconnects and kills actor

**Actor Pattern:**
```python
# Create persistent actor
actor = create_actor(execution_id)

# Connect and get initial response
result = await actor.connect.remote(prompt)

# Query and get batched messages
result = await actor.query.remote(user_message)

# Cleanup
await cleanup_actor(execution_id)
```

#### `query.py` - Kodosumi Orchestration (276 lines)

**Lean integration focused on Kodosumi patterns:**

1. **Form Definition** - Simple input form with prompt field
2. **Entry Point** (`@app.enter()`) - Validates input and launches execution
3. **Orchestration** (`run_conversation()`) - Actor lifecycle management:
   - Creates/retrieves ClaudeSessionActor
   - Displays messages via `tracer.markdown()`
   - HITL pauses via `tracer.lease()`
   - Auto-retry on actor crashes
   - Cleanup on completion/timeout
4. **Conversation Summary** - Shows iteration count at end

**HITL Pattern:**
```python
# Display Claude's messages
for msg in result["messages"]:
    await tracer.markdown(f"\n**Claude:** {msg['content']}\n")

# HITL pause - get user input
user_input = await tracer.lease("claude-input", F.Model(...))

# Send to actor
result = await actor.query.remote(user_input["response"])
```

#### Configuration Files

**`data/config/claude_hitl_template.yaml`:**
```yaml
name: claude_hitl_template
route_prefix: /claude-hitl
import_path: claude_hitl_template.query:fast_app

# Runtime environment for Ray workers
runtime_env:
  pip:
    - claude-agent-sdk>=0.1.6
  env_vars:
    OTEL_SDK_DISABLED: "true"

num_replicas: 1
max_concurrent_queries: 10

# Note: ClaudeSessionActor resources (1 CPU, 512MB) configured in agent.py
```

## Conversation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User submits prompt via Kodosumi form                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Launch async execution with Claude SDK                       │
│    - Initialize ClaudeSDKClient                                 │
│    - Connect with initial prompt                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Stream Claude's response                                     │
│    - Display text blocks via tracer.markdown()                  │
│    - Track conversation history                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. HITL Pause - tracer.lease()                                  │
│    - Show form asking for user's next input                     │
│    - User can continue, type 'done', or cancel                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
           ┌─────────┴─────────┐
           │                   │
           ▼                   ▼
    ┌───────────┐      ┌──────────────┐
    │  User     │      │  User types  │
    │  cancels  │      │  'done' or   │
    │  or times │      │  provides    │
    │  out      │      │  input       │
    └─────┬─────┘      └──────┬───────┘
          │                   │
          ▼                   │
    ┌──────────┐              │
    │   End    │              │
    │ Convo    │              │
    └──────────┘              │
                              ▼
                      ┌────────────────┐
                      │ Send to Claude │
                      │ via query()    │
                      └────────┬───────┘
                               │
                               │
                    ┌──────────┴──────────┐
                    │ Loop back to step 3  │
                    └─────────────────────┘
```

### Termination Conditions

The conversation automatically ends when:
1. **Claude Completes Task** - `ResultMessage` received from Claude SDK
2. **10-Minute Timeout** - Configurable via `CONVERSATION_TIMEOUT_SECONDS`
3. **User Terminates** - User types 'done', 'exit', 'quit', or 'stop'
4. **User Cancels** - User clicks "Cancel" or "End Conversation"
5. **Max Iterations** - Safety limit of 50 iterations reached

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

**Option 2: Add Claude SDK Tools**
```python
# In query.py or separate tools.py
from claude_agent_sdk import tool

@tool("data_analyzer", "Analyzes dataset", {"data": dict})
async def analyze_tool(args: dict) -> dict:
    result = analyze_data(args["data"])
    return {"content": [{"type": "text", "text": str(result)}]}

# Register tools when creating ClaudeSDKClient
client = ClaudeSDKClient(
    options=ClaudeAgentOptions(
        mcp_servers=[your_tool_config]
    )
)
```

### Customizing the HITL Flow

The HITL pause happens via `tracer.lease()`. Customize the form:

```python
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

### Adding API Integrations

```python
# In agent.py
import requests

def call_external_api(query: str) -> dict:
    response = requests.post(
        "https://api.example.com/endpoint",
        json={"query": query},
        headers={"Authorization": f"Bearer {os.getenv('API_KEY')}"}
    )
    return response.json()
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

### Common Errors

**`InputsError.check()` AttributeError**
- **Fix**: Use `if error.has_errors(): raise error` instead of `error.check()`

**`runtime_envs support only remote URIs in working_dir`**
- **Fix**: Remove `runtime_env.working_dir` from deployment config

**`Expected a built Serve application but got: ServeAPI`**
- **Fix**: Add `@serve.deployment` wrapper to query.py

**`run_conversation() missing argument: 'request'`**
- **Fix**: Remove `request` parameter from execution function signature

**`CLIConnectionError: ProcessTransport is not ready`**
- **Status**: Known limitation - Claude SDK needs Ray Actor refactor
- **Workaround**: See [CLAUDE.md](CLAUDE.md#architecture-decision-ray-actors-for-claude-sdk)

**Ray Version Mismatch**
```bash
ray stop
source .venv/bin/activate
ray --version  # Verify
just start
```

### Kodosumi Deployment
```bash
# Check logs
koco logs

# Redeploy
koco deploy -r

# Ensure spooler is running (CRITICAL!)
koco spool &
```

### Comprehensive Guide

See [CLAUDE.md - Extended Troubleshooting](CLAUDE.md#extended-troubleshooting) for detailed solutions to all errors encountered during development.

## Configuration Options

### Adjust Timeouts

```python
# In query.py
CONVERSATION_TIMEOUT_SECONDS = 1200  # 20 minutes
MAX_MESSAGE_ITERATIONS = 100  # More iterations
```

### Change Working Directory

```python
# In query.py, run_conversation()
client = ClaudeSDKClient(
    options=ClaudeAgentOptions(
        cwd="/path/to/your/project",  # Update this
        permission_mode="plan"  # or "bypassPermissions"
    )
)
```

### Resource Allocation

```yaml
# In data/config/claude_hitl_template.yaml
num_replicas: 2  # Scale up
max_concurrent_queries: 20  # Handle more concurrent users

ray_actor_options:
  num_cpus: 2
  num_gpus: 0
```

## Production Deployment

### Ray Worker Requirements

**CRITICAL:** All Ray worker nodes MUST have these dependencies installed:

#### 1. Node.js 18+
```bash
# Ubuntu/Debian
apt-get update && apt-get install -y nodejs npm

# Or use NodeSource for specific version
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs
```

#### 2. Claude Code CLI
```bash
npm install -g @anthropic-ai/claude-code
```

#### 3. Network Access
- Outbound HTTPS to `api.anthropic.com`
- Port 443 (HTTPS) must be allowed

### Recommended: Container-Based Deployment

Create a custom Docker image with all dependencies:

```dockerfile
FROM rayproject/ray:latest

# Install Node.js 18+
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Set working directory
WORKDIR /app
```

Build and push:
```bash
docker build -t your-registry/ray-claude:latest .
docker push your-registry/ray-claude:latest
```

Configure in deployment:
```yaml
# data/config/claude_hitl_template.yaml
runtime_env:
  container:
    image: "your-registry/ray-claude:latest"
  pip:
    - claude-agent-sdk>=0.1.6
  env_vars:
    ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
    OTEL_SDK_DISABLED: "true"
```

### Authentication

**Option A: Environment Variables** (Recommended)
```bash
export ANTHROPIC_API_KEY=sk-ant-...
koco deploy
```

**Option B: AWS Bedrock**
```yaml
env_vars:
  CLAUDE_CODE_USE_BEDROCK: "1"
  # AWS credentials from instance profile or environment
```

**Option C: Google Vertex AI**
```yaml
env_vars:
  CLAUDE_CODE_USE_VERTEX: "1"
  # GCP credentials from service account
```

### Monitoring & Best Practices

1. **Ray Dashboard**: Monitor actor status at `http://localhost:8265`
2. **Error Logging**: Add structured logging instead of print statements
3. **Rate Limiting**: Configure max_concurrent_queries in deployment YAML
4. **Resource Limits**: Ensure adequate RAM (1GB per concurrent conversation)
5. **Timeout Configuration**: Adjust CONVERSATION_TIMEOUT_SECONDS as needed
6. **Health Checks**: Monitor actor lifecycle and cleanup
7. **API Key Rotation**: Use secure secret management (Vault, AWS Secrets Manager)

## Contributing

This is a template project. Fork and customize for your needs!

## License

MIT License - Use freely for your projects

## Related Resources

- [Claude Agent SDK Docs](https://docs.claude.com/en/api/agent-sdk/python)
- [Kodosumi Documentation](https://kodosumi.dev)
- [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html)
- [Claude Code CLI](https://docs.claude.com/en/docs/claude-code)

## Support

For issues or questions:
- Claude SDK: https://docs.claude.com/en/api/agent-sdk
- Kodosumi: Check Kodosumi documentation
- This template: Open an issue on GitHub

---

**Built with Claude Agent SDK + Kodosumi**
