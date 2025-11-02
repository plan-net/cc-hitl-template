# Claude + Kodosumi HITL Template

A minimal template demonstrating how to integrate **Claude Agent SDK** with **Kodosumi's Human-in-the-Loop (HITL)** functionality.

## ⚠️ Current Status: Work in Progress

This template is functional for Kodosumi deployment but **Claude SDK integration is being refactored** to use Ray Actors for proper subprocess management.

**Working:**
- ✅ Kodosumi service deployment with Ray Serve
- ✅ Form submission and input validation
- ✅ HITL pattern structure (`tracer.lease()`)
- ✅ Basic execution flow with async Launch

**In Progress:**
- 🚧 Claude SDK integration via Ray Actors
- 🚧 Conversation state management across HITL interactions
- 🚧 Proper subprocess isolation for Claude CLI

**Known Limitation:**
Claude Agent SDK requires long-running processes (not stateless handlers). Current implementation attempts to spawn Claude CLI subprocess in Ray Serve workers, which fails. Solution in progress: Ray Actor wrapper for persistent Claude SDK sessions. See [CLAUDE.md](CLAUDE.md#architecture-decision-ray-actors-for-claude-sdk) for details.

## Overview

This template showcases a complete integration pattern for building interactive AI agents that combine:
- **Claude Agent SDK** for intelligent conversation and reasoning
- **Kodosumi** for service deployment and execution management
- **Ray Serve** for distributed computing
- **HITL (Human-in-the-Loop)** for back-and-forth interaction between Claude and users

## Features

- ✅ Simple single-prompt input form
- ✅ Kodosumi HITL integration structure for user interaction
- ✅ Ray Serve deployment with proper `@serve.deployment` wrapper
- ✅ 10-minute timeout with conversation controls
- ✅ Minimal, well-commented codebase (~350 lines total)
- 🚧 Claude Agent SDK conversation (in progress - needs Ray Actor)
- 🚧 Streaming responses and conversation history (pending Actor implementation)
- 🚧 Automatic conversation termination detection (pending Actor implementation)

## Prerequisites

### Required Software
- **Python 3.12+** (managed via pyenv recommended)
- **Claude Code CLI** - Required for Claude Agent SDK authentication
  ```bash
  # Install Claude Code CLI first
  # Visit https://docs.claude.com/en/docs/claude-code for instructions
  ```
- **Ray** - Distributed computing framework (installed via dependencies)
- **Kodosumi v1.0.0+** - Service framework

### System Requirements
- macOS, Linux, or WSL2 on Windows
- 4GB+ RAM recommended
- Active internet connection for Claude API

## Quick Start

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

### 2. Verify Claude Code CLI

```bash
# Ensure Claude Code CLI is installed and authenticated
claude --version

# If not installed, follow: https://docs.claude.com/en/docs/claude-code
```

### 3. Start the Service

```bash
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
│   ├── agent.py             # Minimal business logic placeholder (26 lines)
│   └── query.py             # Main Kodosumi + Claude SDK integration (307 lines)
├── data/config/
│   ├── config.yaml          # Global Ray Serve configuration
│   └── claude_hitl_template.yaml  # Service-specific deployment config
├── tests/
│   ├── __init__.py
│   └── test_basic.py        # Smoke tests
├── justfile                 # Task runner commands
├── pyproject.toml           # Project dependencies
├── pytest.ini               # Test configuration
├── README.md                # This file
└── CLAUDE.md                # Claude Code guidance
```

### Component Breakdown

#### `query.py` - Main Service Integration (307 lines)

**Key Responsibilities:**
1. **Form Definition** - Simple input form with prompt field
2. **Entry Point** (`@app.enter()`) - Validates input and launches execution
3. **Conversation Loop** (`run_conversation()`) - Core HITL logic:
   - Initializes Claude SDK client
   - Streams responses from Claude
   - Uses `tracer.lease()` for HITL pauses
   - Handles timeouts and termination
4. **Conversation Summary** - Shows message breakdown at end

**HITL Pattern:**
```python
# After Claude responds, pause and ask user for more input
user_input = await tracer.lease(
    "claude-input",
    F.Model(
        F.InputArea(label="Your Response", ...),
        F.Submit("Send")
    )
)

# Resume conversation with user's response
await client.query(user_input["response"])
```

#### `agent.py` - Business Logic Placeholder (26 lines)

Intentionally minimal placeholder demonstrating where to add custom business logic:
- API integrations
- Data processing
- Custom tools for Claude SDK
- Validation logic

**Extend this file** with your own agent logic as needed.

#### Configuration Files

**`data/config/claude_hitl_template.yaml`:**
```yaml
name: claude_hitl_template
route_prefix: /claude-hitl
import_path: claude_hitl_template.query:fast_app
runtime_env:
  pip:
    - claude-agent-sdk>=0.1.6
    - kodosumi>=1.0.0
    # Add your dependencies here
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

For production use:

1. **Remove hardcoded paths** in `query.py` (line 137)
2. **Add proper error logging** instead of print statements
3. **Configure API keys** via environment variables
4. **Set up monitoring** with Ray Dashboard
5. **Add rate limiting** for API calls
6. **Implement caching** for repeated queries
7. **Add user authentication** via Kodosumi

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
