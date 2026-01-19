# Azure Foundry Integration

This document describes how to use Azure Foundry (Microsoft) as an alternative to the public Anthropic API.

## Overview

The template supports both:
- **Public Anthropic API** (default)
- **Azure Foundry** (Microsoft enterprise deployment)

Environment variables flow from Ray Serve config to the actor container, where the Claude CLI reads them directly.

## Architecture

```
Ray Serve Deployment (runtime_env.env_vars)
       │
       │ env vars available via os.environ
       ▼
create_actor() passthrough
       │
       │ RuntimeEnv(env_vars={...})
       ▼
Actor Container (separate, isolated)
       │
       │ Container inherits env vars
       ▼
Claude CLI (reads CLAUDE_CODE_USE_FOUNDRY, ANTHROPIC_*, etc.)
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_CODE_USE_FOUNDRY` | `"1"` = Azure Foundry, unset = Public API | `"1"` |
| `ANTHROPIC_API_KEY` | Public API key (when Foundry not enabled) | `sk-ant-...` |
| `ANTHROPIC_FOUNDRY_BASE_URL` | Azure Foundry endpoint URL | `https://your-resource.services.ai.azure.com` |
| `ANTHROPIC_FOUNDRY_API_KEY` | Azure API key | `your-azure-key` |
| `CLAUDE_ACTOR_CPUS` | CPU allocation per actor | `1` |
| `CLAUDE_ACTOR_MEMORY_GB` | Memory in GB per actor | `2` |
| `CONTAINER_IMAGE_URI` | Container image for actors | `ghcr.io/org/image:tag` |

### Example Ray Serve Config

```yaml
applications:
  - name: claude_hitl_template
    route_prefix: /claude
    import_path: claude_hitl_template.query:fast_app
    runtime_env:
      container:
        image: "ghcr.io/your-org/claude-hitl-worker:v1.0.0"
        run_options:
          - "--userns=host"
          - "--user=0:0"
      env_vars:
        # Azure Foundry Configuration
        CLAUDE_CODE_USE_FOUNDRY: "1"
        ANTHROPIC_FOUNDRY_BASE_URL: "https://your-resource.services.ai.azure.com"
        ANTHROPIC_FOUNDRY_API_KEY: "your-azure-key"
        # Resources
        CLAUDE_ACTOR_CPUS: "1"
        CLAUDE_ACTOR_MEMORY_GB: "2"
        # Container
        CONTAINER_IMAGE_URI: "ghcr.io/your-org/claude-hitl-worker:v1.0.0"
```

### Example .env (for local development)

```bash
# API Provider: "1" = Azure Foundry, unset = Public API (default)
CLAUDE_CODE_USE_FOUNDRY=1

# Public API (used when CLAUDE_CODE_USE_FOUNDRY is not set)
ANTHROPIC_API_KEY=sk-ant-...

# Azure Foundry (used when CLAUDE_CODE_USE_FOUNDRY=1)
ANTHROPIC_FOUNDRY_BASE_URL=https://your-resource.services.ai.azure.com
ANTHROPIC_FOUNDRY_API_KEY=your-azure-key

# Resources
CLAUDE_ACTOR_CPUS=1
CLAUDE_ACTOR_MEMORY_GB=2
```

## How It Works

1. **Ray Serve config** defines `env_vars` in `runtime_env`
2. **Serve deployment** (query.py) has access to these via `os.environ`
3. **`create_actor()`** filters and passes through relevant env vars:
   - `ANTHROPIC_*` - API configuration
   - `CLAUDE_CODE_*` - Claude Code settings
   - `CLAUDE_MODEL` - Model selection
   - `CLAUDE_ACTOR_*` - Resource configuration
   - `CONTAINER_IMAGE_*` - Container metadata
4. **Actor container** receives env vars via `RuntimeEnv(env_vars={...})`
5. **Claude CLI** reads env vars from its environment

No transformation or construction happens in Python code - env vars flow directly from config to container.

## Verification

Check actor logs for:
```
Using Azure Foundry API (CLAUDE_CODE_USE_FOUNDRY=1)
Passing through X env vars to actor
Actor resources: 1 CPUs, 2GB RAM
```

## Switching Between APIs

### To use Public Anthropic API:
- Remove or unset `CLAUDE_CODE_USE_FOUNDRY`
- Set `ANTHROPIC_API_KEY`

### To use Azure Foundry:
- Set `CLAUDE_CODE_USE_FOUNDRY=1`
- Set `ANTHROPIC_FOUNDRY_BASE_URL`
- Set `ANTHROPIC_FOUNDRY_API_KEY`

## Troubleshooting

### 403 Forbidden Error
- Verify API key is correct
- Check if VPN is required for your Azure endpoint
- Ensure `CLAUDE_CODE_USE_FOUNDRY=1` is set

### Container Not Receiving Env Vars
- Verify env vars are set in Ray Serve config `runtime_env.env_vars`
- Check that create_actor() is being called (not reusing existing actor)
- Look for "Passing through X env vars" in logs

### Model Not Found
- Azure Foundry may use different model names
- Check available models in your Azure deployment
