# Azure Foundry Integration

This document describes how to use Azure Foundry as an alternative to the public Anthropic API.

## Overview

The template supports both:
- **Public Anthropic API** (default)
- **Azure Foundry** (enterprise deployment)

Switch between them using the `CLAUDE_USE_AZURE_FOUNDRY` environment variable.

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_USE_AZURE_FOUNDRY` | `"0"` = Public API (default), `"1"` = Azure | `"1"` |
| `ANTHROPIC_API_KEY` | Public API key (when Azure=0) | `sk-ant-...` |
| `ANTHROPIC_FOUNDRY_BASE_URL` | Azure endpoint URL | `https://claude-sweden-gateway.azure-api.net/claude-sweden/anthropic` |
| `ANTHROPIC_FOUNDRY_API_KEY` | Azure API key (without prefix) | `abc123def456` |
| `CLAUDE_MODEL` | Model tier: `opus`, `sonnet` | `sonnet` |
| `CLAUDE_ACTOR_CPUS` | CPU allocation per actor | `1` |
| `CLAUDE_ACTOR_MEMORY_GB` | Memory in GB per actor | `2` |

### Model Mapping

| Tier | Public API Model | Azure Model |
|------|------------------|-------------|
| `opus` | `claude-opus-4-20250514` | `claude-opus-4-5` |
| `sonnet` | `claude-sonnet-4-20250514` | `claude-sonnet-4-5` |

### Example .env

```bash
# API Provider: "0" = Public (default), "1" = Azure Foundry
CLAUDE_USE_AZURE_FOUNDRY=1

# Public API (used when CLAUDE_USE_AZURE_FOUNDRY=0)
ANTHROPIC_API_KEY=sk-ant-...

# Azure Foundry (used when CLAUDE_USE_AZURE_FOUNDRY=1)
ANTHROPIC_FOUNDRY_BASE_URL=https://claude-sweden-gateway.azure-api.net/claude-sweden/anthropic
ANTHROPIC_FOUNDRY_API_KEY=your-azure-key-here

# Model: opus | sonnet
CLAUDE_MODEL=sonnet

# Resources
CLAUDE_ACTOR_CPUS=1
CLAUDE_ACTOR_MEMORY_GB=2
```

### Example Expose Config (Kodosumi API)

```yaml
runtime_env:
  env_vars:
    CONTAINER_IMAGE_URI: "ghcr.io/basteiz/claude-hitl-worker:v1.0.1"
    CLAUDE_USE_AZURE_FOUNDRY: "1"
    ANTHROPIC_FOUNDRY_BASE_URL: "https://claude-sweden-gateway.azure-api.net/claude-sweden/anthropic"
    ANTHROPIC_FOUNDRY_API_KEY: "your-azure-key"
    CLAUDE_MODEL: "sonnet"
    CLAUDE_ACTOR_CPUS: "1"
    CLAUDE_ACTOR_MEMORY_GB: "2"
```

## Testing

### Layer 2: Non-Containerized Test

```bash
# Set env vars
source .env

# Run test
source .venv/bin/activate
python tests/test_azure_actor.py
```

### Layer 3: Containerized Test

1. Build container with versioned tag
2. Update Expose config with Azure env vars
3. Boot via Kodosumi API
4. Start HITL session

## Verification

Check agent logs for:
```
Using Azure Foundry API with model: claude-sonnet-4-5
Actor resources: 1 CPUs, 2GB RAM
```

Container metadata should show:
- Memory: 2.0 GB (not 1.0 GB)
- Model configured for Azure

## Implementation Details

The Azure Foundry integration is implemented in `claude_hitl_template/agent.py`:

- `get_container_image_config()` - Reads image info including git commit
- `create_actor()` - Configures API provider based on env vars
- `ClaudeSessionActor.__init__()` - Reads resource allocation from env vars

Key env vars passed to Claude CLI subprocess:
- `CLAUDE_CODE_USE_FOUNDRY=1`
- `ANTHROPIC_FOUNDRY_BASE_URL`
- `ANTHROPIC_FOUNDRY_API_KEY`
- `ANTHROPIC_CUSTOM_HEADERS=api-key: <key>`
- `ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-5`
