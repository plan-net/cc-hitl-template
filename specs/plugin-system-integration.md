# Plugin System Integration Specification

**Version:** 1.0
**Date:** 2025-11-04
**Status:** Planning

---

## Table of Contents

1. [Overview](#overview)
2. [Background & Context](#background--context)
3. [Architecture](#architecture)
4. [Repository Structure](#repository-structure)
5. [Implementation Plan](#implementation-plan)
6. [Technical Details](#technical-details)
7. [Success Criteria](#success-criteria)
8. [References](#references)

---

## Overview

This specification defines the integration of the Claude Code plugin system into the cc-hitl-template project. The goal is to transform the HITL template from a monolithic structure into a modular, plugin-based architecture that separates developer tools from agent runtime capabilities while maintaining ease of use and deployment.

### Key Objectives

1. **Modularity**: Extract commands, skills, and agents into reusable plugins
2. **Dual Marketplace**: Separate developer experience tools from agent runtime capabilities
3. **Declarative Dependencies**: Config repos declare required plugins via standard settings.json
4. **Immutable Deployments**: Plugins baked into container images with digest tracking
5. **Developer Experience**: Standard Claude Code plugin workflow for local development
6. **Deployment Experience**: Automatic plugin loading in containerized Ray actors

### Design Principles

- **Use Standard Formats**: Leverage existing settings.json structure (no custom schemas)
- **Explicit Over Implicit**: Agent.py explicitly reads settings.json (SDK doesn't auto-read)
- **Separation of Concerns**: Config repos ≠ plugins (config declares dependencies)
- **Build-Time Resolution**: Clone and bake plugins during image build
- **Convention Over Configuration**: Follow Claude Code plugin standards

---

## Background & Context

### Claude Code Plugin System

Claude Code supports a plugin system for distributing reusable functionality. Key concepts:

**Plugins** are structured directory packages containing:
- Commands (slash commands in markdown)
- Agents (autonomous subagents)
- Skills (model-invoked capabilities)
- Hooks (event handlers)
- MCP Servers (external tool integrations)

**Marketplaces** are catalogs of plugins with:
- Plugin discovery mechanism
- Version tracking
- Distribution via git repositories

**Project Configuration** (`.claude/settings.json`) declares:
- Known marketplaces (`extraKnownMarketplaces`)
- Enabled plugins (`enabledPlugins`)
- Auto-installation when folder is trusted

### Current HITL Template Structure

**Monolithic approach:**
```
cc-hitl-template/
├── .claude/
│   ├── commands/        # /cc-deploy, /cc-setup, /cc-shutdown
│   ├── skills/          # docker-build, prerequisite-check, vm-setup
│   ├── agents/          # deployment, setup
│   └── settings.json
├── claude_hitl_template/
│   ├── agent.py         # Ray actor + Claude SDK integration
│   └── query.py         # Kodosumi HITL orchestration
└── Dockerfile
```

**Problems:**
- All functionality bundled in template repo
- Hard to share/reuse components across projects
- No version control for individual features
- Mixing framework code with tooling
- Config repos (master/project) are just CLAUDE.md files

### Why Plugins?

**Benefits:**
1. **Reusability**: Share plugins across multiple HITL projects
2. **Versioning**: Track versions per plugin/marketplace
3. **Discovery**: Marketplaces make finding capabilities easy
4. **Modularity**: Test and develop components independently
5. **Community**: Enable contributions via plugin ecosystem
6. **Clarity**: Clear boundaries between framework and features

### Two-Marketplace Architecture

**cc-marketplace-developers** (Developer Experience):
- Tools for building/testing/deploying the template
- Examples: deployment automation, prerequisite checking, VM setup
- Used by: Template maintainers, DevOps engineers
- Install context: Local development with Claude Code CLI

**cc-marketplace-agents** (Agent Runtime):
- Business logic and agent capabilities
- Examples: domain workflows, integrations, specialized agents
- Used by: Deployed Ray actors, runtime agents
- Install context: Baked into container images

This separation aligns with the distinct concerns of "developing the template" vs "running agents."

### Key Constraint: Agent SDK ≠ Claude Code CLI

**Critical Understanding:**

The Claude Agent SDK does **NOT** automatically read `.claude/settings.json`. The SDK requires explicit inline plugin loading:

```python
ClaudeAgentOptions(
    plugins=[
        {"type": "local", "path": "/app/plugins/plugin-name"}
    ]
)
```

**Implication:**
Even though config repos use standard settings.json (for Claude Code CLI compatibility), we must implement custom logic in agent.py to read settings.json and convert `enabledPlugins` into SDK plugin specs.

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Development Workflow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Developer works on config repo                               │
│     └─> Edits .claude/settings.json                             │
│         └─> Adds enabledPlugins + extraKnownMarketplaces        │
│                                                                   │
│  2. Claude Code CLI (local dev)                                  │
│     └─> Trusts .claude folder                                   │
│         └─> Auto-installs plugins from marketplaces             │
│             └─> /cc-deploy, /cc-setup commands available        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Build Workflow                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. build.sh clones config repos                                 │
│     └─> cc-master-agent-config                                  │
│     └─> cc-example-agent-config                                 │
│                                                                   │
│  2. build.sh reads settings.json from both repos                 │
│     └─> Extracts extraKnownMarketplaces                         │
│     └─> Extracts enabledPlugins                                 │
│                                                                   │
│  3. build.sh clones marketplaces                                 │
│     └─> cc-marketplace-developers                               │
│     └─> cc-marketplace-agents                                   │
│                                                                   │
│  4. build.sh copies enabled plugins to build context             │
│     └─> Resolves plugin-name@marketplace-name                   │
│     └─> Copies to build-context/plugins/{marketplace}/plugins/  │
│                                                                   │
│  5. Docker build bakes plugins into image                        │
│     └─> COPY plugins/ /app/plugins/                             │
│     └─> COPY configs/ /app/template_user/.claude, etc.          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Runtime Workflow                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Ray actor starts (ClaudeSessionActor.__init__)               │
│                                                                   │
│  2. agent.py reads settings.json                                 │
│     └─> /app/template_user/.claude/settings.json (master)       │
│     └─> /app/project/.claude/settings.json (project)            │
│                                                                   │
│  3. agent.py merges enabledPlugins                               │
│     └─> Project overrides master on conflicts                   │
│                                                                   │
│  4. agent.py resolves plugin paths                               │
│     └─> "plugin@marketplace" → "/app/plugins/marketplace/..."   │
│                                                                   │
│  5. agent.py loads plugins via SDK                               │
│     └─> ClaudeAgentOptions(plugins=[...])                       │
│                                                                   │
│  6. Claude SDK subprocess starts with plugins                    │
│     └─> Commands, skills, agents available in conversation      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Repository Relationships

```
┌───────────────────────────────────────────────────────────────────┐
│                      cc-hitl-template                             │
│                     (Framework Only)                              │
├───────────────────────────────────────────────────────────────────┤
│  - agent.py (plugin loader)                                       │
│  - query.py (Kodosumi orchestration)                              │
│  - Dockerfile (copy plugins)                                      │
│  - build.sh (clone marketplaces + copy plugins)                   │
│  - .claude/settings.json (local dev config)                       │
└───────────────────────────────────────────────────────────────────┘
                              │
                              │ uses plugins from
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              cc-marketplace-developers                          │
│              (Developer Experience)                             │
├─────────────────────────────────────────────────────────────────┤
│  Plugins:                                                        │
│  - general (git helpers, file ops, etc.)                        │
│  - claude-agent-sdk (SDK debugging, testing)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              cc-marketplace-agents                              │
│              (Agent Runtime)                                     │
├─────────────────────────────────────────────────────────────────┤
│  Plugins:                                                        │
│  - master-core (deployment, setup, docker-build, etc.)          │
│  - hitl-example (example workflows for demo)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ declared by
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              cc-master-agent-config                             │
│              (Master Configuration)                             │
├─────────────────────────────────────────────────────────────────┤
│  .claude/settings.json:                                          │
│    extraKnownMarketplaces: {...}                                │
│    enabledPlugins: {                                            │
│      "general@cc-marketplace-developers": true,                 │
│      "claude-agent-sdk@cc-marketplace-developers": true,        │
│      "master-core@cc-marketplace-agents": true                  │
│    }                                                             │
│  .claude/CLAUDE.md (master agent instructions)                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              cc-example-agent-config                            │
│              (Example Project Configuration)                    │
├─────────────────────────────────────────────────────────────────┤
│  .claude/settings.json:                                          │
│    extraKnownMarketplaces: {...}                                │
│    enabledPlugins: {                                            │
│      "hitl-example@cc-marketplace-agents": true                 │
│    }                                                             │
│  .claude/CLAUDE.md (example agent instructions)                 │
└─────────────────────────────────────────────────────────────────┘
```

### Settings Merge Strategy

**Master + Project Config Merge:**

1. Read `/app/template_user/.claude/settings.json` (master config)
2. Read `/app/project/.claude/settings.json` (project config)
3. Merge `extraKnownMarketplaces` (union of both)
4. Merge `enabledPlugins` (project overrides master on key conflict)
5. Convert to SDK plugin specs
6. Load via `ClaudeAgentOptions(plugins=[...])`

**Example:**

```python
# Master config
{
  "enabledPlugins": {
    "general@cc-marketplace-developers": true,
    "master-core@cc-marketplace-agents": true,
    "debug-tools@cc-marketplace-agents": false
  }
}

# Project config
{
  "enabledPlugins": {
    "hitl-example@cc-marketplace-agents": true,
    "debug-tools@cc-marketplace-agents": true  # Override: enable
  }
}

# Merged result
{
  "enabledPlugins": {
    "general@cc-marketplace-developers": true,
    "master-core@cc-marketplace-agents": true,
    "hitl-example@cc-marketplace-agents": true,
    "debug-tools@cc-marketplace-agents": true  # Project wins
  }
}
```

---

## Repository Structure

### cc-marketplace-developers

**Purpose:** Developer experience plugins for building/testing/deploying the template

**Structure:**
```
cc-marketplace-developers/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── general/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── commands/
│   │   │   ├── git-helper.md
│   │   │   ├── file-search.md
│   │   │   └── env-check.md
│   │   └── skills/
│   │       └── common-utils/
│   │           └── SKILL.md
│   │
│   └── claude-agent-sdk/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/
│       │   ├── sdk-debug.md
│       │   ├── connection-test.md
│       │   └── subprocess-inspect.md
│       └── skills/
│           └── sdk-helpers/
│               └── SKILL.md
├── README.md
└── LICENSE
```

**marketplace.json:**
```json
{
  "name": "cc-marketplace-developers",
  "owner": {
    "name": "HITL Template Team",
    "email": "team@example.com",
    "url": "https://github.com/org/cc-marketplace-developers"
  },
  "description": "Developer tools for Claude + Kodosumi HITL template",
  "plugins": [
    {
      "name": "general",
      "source": "./plugins/general",
      "description": "General-purpose development utilities",
      "version": "1.0.0",
      "keywords": ["dev", "utils", "helpers"]
    },
    {
      "name": "claude-agent-sdk",
      "source": "./plugins/claude-agent-sdk",
      "description": "Claude Agent SDK specific tooling",
      "version": "1.0.0",
      "keywords": ["sdk", "debugging", "testing"]
    }
  ]
}
```

### cc-marketplace-agents

**Purpose:** Agent runtime capabilities for deployed HITL agents

**Structure:**
```
cc-marketplace-agents/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── master-core/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── commands/
│   │   │   ├── cc-deploy.md
│   │   │   ├── cc-setup.md
│   │   │   └── cc-shutdown.md
│   │   ├── agents/
│   │   │   ├── deployment.md
│   │   │   └── setup.md
│   │   └── skills/
│   │       ├── docker-build/
│   │       │   ├── SKILL.md
│   │       │   └── scripts/
│   │       │       └── build.sh
│   │       ├── prerequisite-check/
│   │       │   ├── SKILL.md
│   │       │   └── scripts/
│   │       │       └── check.sh
│   │       └── vm-setup/
│   │           ├── SKILL.md
│   │           └── scripts/
│   │               └── setup-vm.sh
│   │
│   └── hitl-example/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── commands/
│           └── example-workflow.md
├── README.md
└── LICENSE
```

**marketplace.json:**
```json
{
  "name": "cc-marketplace-agents",
  "owner": {
    "name": "HITL Template Team",
    "email": "team@example.com",
    "url": "https://github.com/org/cc-marketplace-agents"
  },
  "description": "Runtime plugins for HITL agents",
  "plugins": [
    {
      "name": "master-core",
      "source": "./plugins/master-core",
      "description": "Core master agent capabilities (deployment, setup, docker)",
      "version": "1.0.0",
      "keywords": ["deployment", "docker", "ray", "setup"]
    },
    {
      "name": "hitl-example",
      "source": "./plugins/hitl-example",
      "description": "Example HITL agent for demonstration",
      "version": "1.0.0",
      "keywords": ["example", "demo", "tutorial"]
    }
  ]
}
```

### cc-master-agent-config (Updated)

**Purpose:** Master agent configuration and plugin declarations

**Changes:**
- Add `extraKnownMarketplaces` to settings.json
- Add `enabledPlugins` to settings.json
- Keep CLAUDE.md for agent instructions

**settings.json:**
```json
{
  "extraKnownMarketplaces": {
    "cc-marketplace-developers": {
      "source": {
        "source": "github",
        "repo": "org/cc-marketplace-developers"
      }
    },
    "cc-marketplace-agents": {
      "source": {
        "source": "github",
        "repo": "org/cc-marketplace-agents"
      }
    }
  },
  "enabledPlugins": {
    "general@cc-marketplace-developers": true,
    "claude-agent-sdk@cc-marketplace-developers": true,
    "master-core@cc-marketplace-agents": true
  },
  "permissions": {
    "allow": [
      "Bash(just orb-up:*)",
      "Bash(just orb-down:*)",
      "Bash(docker:*)",
      "Bash(podman:*)"
    ]
  }
}
```

### cc-example-agent-config (Updated)

**Purpose:** Example project configuration

**settings.json:**
```json
{
  "extraKnownMarketplaces": {
    "cc-marketplace-agents": {
      "source": {
        "source": "github",
        "repo": "org/cc-marketplace-agents"
      }
    }
  },
  "enabledPlugins": {
    "hitl-example@cc-marketplace-agents": true
  }
}
```

### cc-hitl-template (Refactored)

**Purpose:** Framework only (no bundled plugins)

**Structure After Refactor:**
```
cc-hitl-template/
├── claude_hitl_template/
│   ├── agent.py              # MODIFIED: Plugin loader
│   └── query.py              # UNCHANGED
│
├── .claude/
│   ├── settings.json         # MODIFIED: Local dev plugin config
│   └── CLAUDE.md             # UPDATED: Document plugin architecture
│
├── specs/
│   └── plugin-system-integration.md  # This document
│
├── docs/
│   ├── ARCHITECTURE.md       # UPDATED: Plugin system section
│   ├── SETUP.md              # UPDATED: Marketplace installation
│   ├── DEVELOPMENT.md        # UPDATED: Plugin development guide
│   ├── PLUGINS.md            # NEW: Comprehensive plugin guide
│   └── MARKETPLACES.md       # NEW: Marketplace usage guide
│
├── Dockerfile                # MODIFIED: Copy plugins
├── .env.example              # UPDATED: Add marketplace URLs
└── README.md                 # UPDATED: Plugin overview
```

**Removed:**
- `.claude/commands/` (moved to plugins)
- `.claude/skills/` (moved to plugins)
- `.claude/agents/` (moved to plugins)

---

## Implementation Plan

### Phase 1: Create Developer Marketplace

**Duration:** Week 1

**Tasks:**

1. **Create cc-marketplace-developers repository**
   - Initialize git repository
   - Add README with marketplace purpose
   - Add LICENSE (MIT)
   - Create `.claude-plugin/marketplace.json`

2. **Create "general" plugin**
   - Create plugin structure: `.claude-plugin/plugin.json`
   - Add general development utilities:
     - `commands/git-helper.md` - Git operation helpers
     - `commands/file-search.md` - File search utilities
     - `commands/env-check.md` - Environment validation
   - Add `skills/common-utils/` if needed
   - Validate with `claude plugin validate` (if available)

3. **Create "claude-agent-sdk" plugin**
   - Create plugin structure
   - Add SDK-specific commands:
     - `commands/sdk-debug.md` - Debug SDK connections
     - `commands/connection-test.md` - Test SDK subprocess
     - `commands/subprocess-inspect.md` - Inspect SDK state
   - Add `skills/sdk-helpers/` for advanced SDK operations
   - Document SDK-specific patterns

4. **Test marketplace locally**
   - Install marketplace: `/plugin marketplace add ./cc-marketplace-developers`
   - Verify plugins appear in `/plugin` list
   - Test installation: `/plugin install general@cc-marketplace-developers`
   - Test commands work in Claude Code CLI
   - Document any issues

**Deliverables:**
- ✅ cc-marketplace-developers repository created
- ✅ Two plugins (general, claude-agent-sdk) functional
- ✅ Marketplace installable via Claude Code CLI
- ✅ README documentation complete

### Phase 2: Create Agent Marketplace

**Duration:** Week 1-2

**Tasks:**

1. **Create cc-marketplace-agents repository**
   - Initialize git repository
   - Add README with marketplace purpose
   - Add LICENSE (MIT)
   - Create `.claude-plugin/marketplace.json`

2. **Migrate existing functionality to "master-core" plugin**

   **From cc-hitl-template:**

   Move to `plugins/master-core/`:
   - `.claude/commands/cc-deploy.md` → `commands/cc-deploy.md`
   - `.claude/commands/cc-setup.md` → `commands/cc-setup.md`
   - `.claude/commands/cc-shutdown.md` → `commands/cc-shutdown.md`
   - `.claude/agents/deployment.md` → `agents/deployment.md`
   - `.claude/agents/setup.md` → `agents/setup.md`
   - `.claude/skills/docker-build/` → `skills/docker-build/`
   - `.claude/skills/prerequisite-check/` → `skills/prerequisite-check/`
   - `.claude/skills/vm-setup/` → `skills/vm-setup/`

   **Updates needed:**
   - Create `plugin.json` with metadata
   - Update any hardcoded paths in scripts
   - Use `${CLAUDE_PLUGIN_ROOT}` for absolute paths
   - Test each component independently

3. **Create "hitl-example" plugin**
   - Create plugin structure
   - Add example commands for demonstration:
     - `commands/example-workflow.md` - Sample HITL workflow
   - Document example use cases
   - Keep minimal (for demo purposes)

4. **Test marketplace locally**
   - Install marketplace locally
   - Test all migrated commands/skills/agents
   - Verify functionality matches original
   - Document any breaking changes

**Deliverables:**
- ✅ cc-marketplace-agents repository created
- ✅ master-core plugin with all migrated functionality
- ✅ hitl-example plugin for demos
- ✅ All components tested and working

### Phase 3: Update Config Repos

**Duration:** Week 2

**Tasks:**

1. **Update cc-master-agent-config/.claude/settings.json**

   Add:
   ```json
   {
     "extraKnownMarketplaces": {
       "cc-marketplace-developers": {
         "source": {
           "source": "github",
           "repo": "org/cc-marketplace-developers"
         }
       },
       "cc-marketplace-agents": {
         "source": {
           "source": "github",
           "repo": "org/cc-marketplace-agents"
         }
       }
     },
     "enabledPlugins": {
       "general@cc-marketplace-developers": true,
       "claude-agent-sdk@cc-marketplace-developers": true,
       "master-core@cc-marketplace-agents": true
     }
   }
   ```

   Keep existing `permissions` section

2. **Update cc-example-agent-config/.claude/settings.json**

   Add:
   ```json
   {
     "extraKnownMarketplaces": {
       "cc-marketplace-agents": {
         "source": {
           "source": "github",
           "repo": "org/cc-marketplace-agents"
         }
       }
     },
     "enabledPlugins": {
       "hitl-example@cc-marketplace-agents": true
     }
   }
   ```

3. **Test config repos with Claude Code CLI**
   - Clone both repos locally
   - Trust folders in Claude Code
   - Verify plugins auto-install
   - Test commands work (e.g., `/cc-deploy`, `/cc-setup`)
   - Verify no conflicts or errors

4. **Update config repo documentation**
   - Update README to mention plugin dependencies
   - Document which plugins are required
   - Add setup instructions for new users

**Deliverables:**
- ✅ Config repos updated with plugin declarations
- ✅ Auto-installation works in Claude Code CLI
- ✅ Documentation updated

### Phase 4: Update Template Build Process

**Duration:** Week 2

**Tasks:**

1. **Modify .claude/skills/docker-build/scripts/build.sh**

   Add after cloning config repos:

   ```bash
   # Extract marketplace configurations
   echo "Reading marketplace configurations..."

   # Combine marketplaces from both configs
   MARKETPLACES=$(jq -s '
     .[0].extraKnownMarketplaces + .[1].extraKnownMarketplaces
   ' /tmp/master-config/.claude/settings.json /tmp/project-config/.claude/settings.json)

   # Clone all marketplaces
   mkdir -p /tmp/marketplaces
   echo "$MARKETPLACES" | jq -r 'to_entries[] | "\(.key) \(.value.source.repo // .value.source.url)"' | while read name source; do
     echo "Cloning marketplace: $name from $source"
     if [[ $source == *"/"* ]]; then
       # GitHub repo format
       git clone --depth 1 "git@github.com:${source}.git" "/tmp/marketplaces/$name"
     else
       # Full URL format
       git clone --depth 1 "$source" "/tmp/marketplaces/$name"
     fi
   done

   # Extract enabled plugins
   ENABLED_PLUGINS=$(jq -s '
     .[0].enabledPlugins + .[1].enabledPlugins | to_entries[] | select(.value == true) | .key
   ' /tmp/master-config/.claude/settings.json /tmp/project-config/.claude/settings.json -r)

   # Copy enabled plugins to build context
   mkdir -p build-context/plugins
   for plugin_spec in $ENABLED_PLUGINS; do
     IFS='@' read -r plugin_name marketplace_name <<< "$plugin_spec"

     source_path="/tmp/marketplaces/$marketplace_name/plugins/$plugin_name"
     dest_path="build-context/plugins/$marketplace_name/plugins/$plugin_name"

     if [ -d "$source_path" ]; then
       echo "Copying plugin: $plugin_name from $marketplace_name"
       mkdir -p "$(dirname "$dest_path")"
       cp -r "$source_path" "$dest_path"
     else
       echo "WARNING: Plugin not found: $source_path"
     fi
   done
   ```

2. **Modify Dockerfile**

   Add after dependencies:

   ```dockerfile
   # Copy plugins (populated by build.sh)
   COPY plugins/ /app/plugins/

   # Copy config repos (contain settings.json)
   COPY template_user/.claude /app/template_user/.claude
   COPY project/.claude /app/project/.claude
   ```

3. **Update .env.example**

   Add marketplace repo URLs:
   ```bash
   # Plugin Marketplaces
   DEV_MARKETPLACE_REPO=git@github.com:org/cc-marketplace-developers.git
   AGENT_MARKETPLACE_REPO=git@github.com:org/cc-marketplace-agents.git
   ```

4. **Test build process**
   - Run `bash .claude/skills/docker-build/scripts/build.sh`
   - Verify marketplaces cloned correctly
   - Verify plugins copied to build context
   - Verify image builds successfully
   - Inspect container: `docker run --rm -it <image> ls -la /app/plugins/`
   - Confirm plugins present in expected locations

**Deliverables:**
- ✅ build.sh reads settings.json and clones marketplaces
- ✅ build.sh copies enabled plugins to build context
- ✅ Dockerfile includes plugins in image
- ✅ Build process tested end-to-end

### Phase 5: Update agent.py Plugin Loading

**Duration:** Week 2-3

**Tasks:**

1. **Implement settings.json reader in agent.py**

   Add functions:

   ```python
   import json
   from pathlib import Path
   from typing import List, Dict
   import logging

   logger = logging.getLogger(__name__)

   def load_marketplace_settings() -> Dict:
       """
       Read and merge marketplace settings from master and project configs.

       Returns:
           Dict with 'marketplaces' and 'enabled_plugins' keys
       """
       marketplaces = {}
       enabled_plugins = {}

       # Read master config
       master_settings_path = Path("/app/template_user/.claude/settings.json")
       if master_settings_path.exists():
           try:
               data = json.loads(master_settings_path.read_text())
               marketplaces.update(data.get("extraKnownMarketplaces", {}))
               enabled_plugins.update(data.get("enabledPlugins", {}))
               logger.info(f"Loaded master settings: {len(enabled_plugins)} plugins")
           except Exception as e:
               logger.error(f"Failed to read master settings: {e}")

       # Read project config (overrides master)
       project_settings_path = Path("/app/project/.claude/settings.json")
       if project_settings_path.exists():
           try:
               data = json.loads(project_settings_path.read_text())
               marketplaces.update(data.get("extraKnownMarketplaces", {}))
               enabled_plugins.update(data.get("enabledPlugins", {}))
               logger.info(f"Loaded project settings: {len(enabled_plugins)} total plugins")
           except Exception as e:
               logger.error(f"Failed to read project settings: {e}")

       return {
           "marketplaces": marketplaces,
           "enabled_plugins": enabled_plugins
       }

   def resolve_plugin_paths(settings: Dict) -> List[Dict[str, str]]:
       """
       Convert enabledPlugins to Agent SDK plugin specs.

       Args:
           settings: Dict from load_marketplace_settings()

       Returns:
           List of plugin specs for ClaudeAgentOptions
       """
       plugin_specs = []

       for plugin_key, enabled in settings["enabled_plugins"].items():
           if not enabled:
               logger.debug(f"Skipping disabled plugin: {plugin_key}")
               continue

           # Parse "plugin-name@marketplace-name" format
           if "@" not in plugin_key:
               logger.warning(f"Invalid plugin key format: {plugin_key}")
               continue

           plugin_name, marketplace_name = plugin_key.split("@", 1)

           # Plugins are baked into /app/plugins/{marketplace}/plugins/{plugin}
           plugin_path = f"/app/plugins/{marketplace_name}/plugins/{plugin_name}"

           if Path(plugin_path).exists():
               plugin_specs.append({
                   "type": "local",
                   "path": plugin_path
               })
               logger.info(f"Found plugin: {plugin_name}@{marketplace_name}")
           else:
               logger.warning(f"Plugin path not found: {plugin_path}")

       return plugin_specs
   ```

2. **Update ClaudeSessionActor class**

   Modify `__init__`:

   ```python
   class ClaudeSessionActor:
       def __init__(self, execution_id: str):
           self.execution_id = execution_id

           # Load plugins from settings.json
           logger.info("Loading plugins from settings.json...")
           settings = load_marketplace_settings()
           plugin_specs = resolve_plugin_paths(settings)

           logger.info(f"Loaded {len(plugin_specs)} plugins:")
           for spec in plugin_specs:
               logger.info(f"  - {spec['path']}")

           # Create options with plugins
           self.options = ClaudeAgentOptions(
               setting_sources=["user", "project", "local"],
               plugins=plugin_specs
           )

           # Rest of initialization...
   ```

3. **Add error handling and validation**
   - Handle missing settings.json gracefully
   - Warn on invalid plugin specs
   - Log plugin loading failures
   - Fail gracefully if critical plugins missing

4. **Test plugin loading**
   - Build container with plugins
   - Start Ray cluster
   - Deploy service
   - Create actor and check logs
   - Verify plugins loaded correctly
   - Test commands/skills/agents available

**Deliverables:**
- ✅ agent.py reads settings.json from both configs
- ✅ Plugin paths resolved correctly
- ✅ Plugins loaded via SDK
- ✅ Comprehensive logging
- ✅ Error handling implemented
- ✅ Tested in Ray actors

### Phase 6: Clean Up Template

**Duration:** Week 3

**Tasks:**

1. **Remove migrated code from cc-hitl-template**
   - Delete `.claude/commands/` directory
   - Delete `.claude/skills/` directory
   - Delete `.claude/agents/` directory
   - Keep `.claude/settings.json` and `.claude/CLAUDE.md`

2. **Update .claude/settings.json for local dev**

   Replace with plugin-based config:
   ```json
   {
     "extraKnownMarketplaces": {
       "cc-marketplace-developers": {
         "source": {
           "source": "github",
           "repo": "org/cc-marketplace-developers"
         }
       },
       "cc-marketplace-agents": {
         "source": {
           "source": "github",
           "repo": "org/cc-marketplace-agents"
         }
       }
     },
     "enabledPlugins": {
       "general@cc-marketplace-developers": true,
       "claude-agent-sdk@cc-marketplace-developers": true,
       "master-core@cc-marketplace-agents": true
     },
     "permissions": {
       "allow": [
         "Bash(just orb-up:*)",
         "Bash(docker:*)",
         "Read",
         "Write",
         "Edit"
       ]
     }
   }
   ```

3. **Update documentation**

   **CLAUDE.md:**
   - Add plugin architecture section
   - Document two-marketplace pattern
   - Explain settings.json structure
   - Link to marketplace repos

   **docs/ARCHITECTURE.md:**
   - Add "Plugin System" section
   - Explain marketplace architecture
   - Document plugin loading flow
   - Diagram repository relationships

   **docs/SETUP.md:**
   - Update installation to include marketplace setup
   - Document trusting folder for auto-install
   - Explain plugin management

   **docs/DEVELOPMENT.md:**
   - Add plugin development guide
   - Document marketplace contribution process
   - Explain how to create new plugins
   - Testing guidelines for plugins

   **README.md:**
   - Add plugin ecosystem overview
   - Link to marketplaces
   - Update quick start with plugin info

4. **Create new documentation**

   **docs/PLUGINS.md:**
   - Comprehensive plugin guide
   - Available plugins catalog
   - Installation instructions
   - Troubleshooting

   **docs/MARKETPLACES.md:**
   - Marketplace usage guide
   - How to add custom marketplaces
   - Contributing plugins
   - Versioning and updates

5. **Update existing docs for consistency**
   - Search/replace references to old `.claude/commands/`
   - Update code examples
   - Fix broken links
   - Verify all paths correct

**Deliverables:**
- ✅ Old commands/skills/agents removed
- ✅ settings.json updated for plugins
- ✅ All documentation updated
- ✅ New plugin/marketplace docs created
- ✅ Links and examples verified

### Phase 7: Testing & Validation

**Duration:** Week 3

**Tasks:**

1. **Test developer workflow**
   - Clone cc-hitl-template
   - Open in Claude Code
   - Trust `.claude` folder
   - Verify plugins auto-install
   - Test `/cc-deploy` command works
   - Test `/cc-setup` command works
   - Test skills trigger correctly
   - Test agents work as expected

2. **Test build & deploy workflow**
   - Clone fresh template
   - Configure `.env` file
   - Run `bash .claude/skills/docker-build/scripts/build.sh`
   - Verify build succeeds
   - Check plugins in container: `docker run --rm <image> ls /app/plugins/`
   - Deploy to Ray cluster
   - Test agent in Kodosumi
   - Verify plugins loaded in actor
   - Test full HITL workflow

3. **Test customization workflow**
   - Create custom plugin in cc-marketplace-agents
   - Add plugin to cc-example-agent-config settings.json
   - Rebuild container
   - Deploy
   - Verify custom plugin available
   - Test custom plugin commands/skills

4. **Test edge cases**
   - Missing settings.json (should work with defaults)
   - Invalid plugin references (should warn, not crash)
   - Plugin not found in marketplace (should skip gracefully)
   - Conflicting plugin names (should use last enabled)
   - Empty enabledPlugins (should work without plugins)

5. **End-to-end validation**
   - Fresh setup from scratch (new developer)
   - Follow SETUP.md step-by-step
   - Document any unclear steps
   - Build image
   - Deploy to Ray
   - Run complete HITL workflow
   - Verify all functionality works
   - Document any issues encountered

6. **Performance testing**
   - Measure build time with plugins
   - Measure actor startup time
   - Compare with pre-plugin template
   - Ensure no significant degradation

7. **Documentation review**
   - Have someone unfamiliar read docs
   - Identify confusing sections
   - Update based on feedback
   - Verify all links work

**Deliverables:**
- ✅ All workflows tested and passing
- ✅ Edge cases handled gracefully
- ✅ End-to-end validation complete
- ✅ Performance acceptable
- ✅ Documentation clear and accurate
- ✅ Issues documented and resolved

---

## Technical Details

### Plugin Loading Flow (Detailed)

**Step-by-step execution:**

1. **Ray actor instantiation**
   ```python
   actor = ClaudeSessionActor.remote(execution_id="session-123")
   ```

2. **Actor __init__ called**
   - Runs on Ray worker node
   - Container environment: `/app/`
   - Config repos mounted at:
     - `/app/template_user/.claude/` (master)
     - `/app/project/.claude/` (project)

3. **load_marketplace_settings() called**
   ```python
   # Read /app/template_user/.claude/settings.json
   master_data = {
     "extraKnownMarketplaces": {...},
     "enabledPlugins": {
       "general@cc-marketplace-developers": true,
       "master-core@cc-marketplace-agents": true
     }
   }

   # Read /app/project/.claude/settings.json
   project_data = {
     "enabledPlugins": {
       "hitl-example@cc-marketplace-agents": true
     }
   }

   # Merge (project overrides master)
   merged = {
     "marketplaces": {...},
     "enabled_plugins": {
       "general@cc-marketplace-developers": true,
       "master-core@cc-marketplace-agents": true,
       "hitl-example@cc-marketplace-agents": true
     }
   }
   ```

4. **resolve_plugin_paths() called**
   ```python
   for "general@cc-marketplace-developers":
     → resolve to "/app/plugins/cc-marketplace-developers/plugins/general"
     → check exists: True
     → add {"type": "local", "path": "..."}

   for "master-core@cc-marketplace-agents":
     → resolve to "/app/plugins/cc-marketplace-agents/plugins/master-core"
     → check exists: True
     → add {"type": "local", "path": "..."}

   for "hitl-example@cc-marketplace-agents":
     → resolve to "/app/plugins/cc-marketplace-agents/plugins/hitl-example"
     → check exists: True
     → add {"type": "local", "path": "..."}

   Result: [
     {"type": "local", "path": "/app/plugins/cc-marketplace-developers/plugins/general"},
     {"type": "local", "path": "/app/plugins/cc-marketplace-agents/plugins/master-core"},
     {"type": "local", "path": "/app/plugins/cc-marketplace-agents/plugins/hitl-example"}
   ]
   ```

5. **ClaudeAgentOptions created**
   ```python
   options = ClaudeAgentOptions(
     setting_sources=["user", "project", "local"],
     plugins=[...]  # 3 plugins
   )
   ```

6. **SDK subprocess started**
   - Claude Code subprocess launches
   - Plugins loaded from paths
   - Commands, skills, agents registered
   - Ready for conversation

### Build Process Flow (Detailed)

**build.sh execution:**

```bash
#!/bin/bash
set -e

# 1. Load environment
source .env
echo "Building with marketplaces:"
echo "  DEV: $DEV_MARKETPLACE_REPO"
echo "  AGENT: $AGENT_MARKETPLACE_REPO"

# 2. Clone config repos
git clone --depth 1 "$MASTER_CONFIG_REPO" /tmp/master-config
git clone --depth 1 "$PROJECT_CONFIG_REPO" /tmp/project-config

# 3. Read settings.json from both
MASTER_SETTINGS="/tmp/master-config/.claude/settings.json"
PROJECT_SETTINGS="/tmp/project-config/.claude/settings.json"

# 4. Extract marketplace configs
# Combine extraKnownMarketplaces from both files
MARKETPLACES=$(jq -s '
  .[0].extraKnownMarketplaces + .[1].extraKnownMarketplaces
' "$MASTER_SETTINGS" "$PROJECT_SETTINGS")

# 5. Clone marketplaces
mkdir -p /tmp/marketplaces

echo "$MARKETPLACES" | jq -r 'to_entries[] | "\(.key) \(.value.source.source) \(.value.source.repo // .value.source.url)"' | \
while read -r name source_type source_value; do
  echo "Cloning marketplace: $name ($source_type)"

  case "$source_type" in
    "github")
      git clone --depth 1 "git@github.com:${source_value}.git" "/tmp/marketplaces/$name"
      ;;
    "git")
      git clone --depth 1 "$source_value" "/tmp/marketplaces/$name"
      ;;
    *)
      echo "Unsupported source type: $source_type"
      exit 1
      ;;
  esac
done

# 6. Extract enabled plugins
# Merge enabledPlugins from both configs (project overrides master)
ENABLED_PLUGINS=$(jq -s '
  (.[0].enabledPlugins // {}) + (.[1].enabledPlugins // {}) |
  to_entries[] |
  select(.value == true) |
  .key
' "$MASTER_SETTINGS" "$PROJECT_SETTINGS" -r)

# 7. Copy plugins to build context
mkdir -p build-context/plugins

for plugin_spec in $ENABLED_PLUGINS; do
  # Parse "plugin-name@marketplace-name"
  IFS='@' read -r plugin_name marketplace_name <<< "$plugin_spec"

  source_path="/tmp/marketplaces/$marketplace_name/plugins/$plugin_name"
  dest_path="build-context/plugins/$marketplace_name/plugins/$plugin_name"

  if [ -d "$source_path" ]; then
    echo "Copying plugin: $plugin_name from $marketplace_name"
    mkdir -p "$(dirname "$dest_path")"
    cp -r "$source_path" "$dest_path"
  else
    echo "WARNING: Plugin not found: $source_path"
  fi
done

# 8. Copy config repos
cp -r /tmp/master-config/.claude build-context/template_user/.claude
cp -r /tmp/project-config/.claude build-context/project/.claude

# 9. Copy application code
cp -r claude_hitl_template/ build-context/
cp Dockerfile build-context/
cp requirements.txt build-context/

# 10. Build container
cd build-context
docker build -t "$IMAGE_NAME" .

# 11. Push to registry
docker push "$IMAGE_NAME"

# 12. Get image digest
IMAGE_DIGEST=$(docker inspect "$IMAGE_NAME" --format='{{index .RepoDigests 0}}' | cut -d@ -f2)

# 13. Output deployment state
echo "=== DEPLOYMENT STATE ==="
echo "MASTER_CONFIG_COMMIT=$(git -C /tmp/master-config rev-parse HEAD)"
echo "PROJECT_CONFIG_COMMIT=$(git -C /tmp/project-config rev-parse HEAD)"
echo "CONTAINER_IMAGE_URI=$IMAGE_NAME@$IMAGE_DIGEST"
echo "BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "========================"
```

### Settings.json Schema

**Complete schema with all supported fields:**

```json
{
  "extraKnownMarketplaces": {
    "<marketplace-name>": {
      "source": {
        "source": "github" | "git" | "directory",
        "repo": "org/repo",              // For GitHub
        "url": "https://...",             // For Git
        "path": "/local/path"             // For Directory (dev only)
      }
    }
  },

  "enabledPlugins": {
    "<plugin-name>@<marketplace-name>": true | false
  },

  "permissions": {
    "allow": [
      "Bash(command:pattern)",
      "Read",
      "Write"
    ],
    "ask": [
      "Bash(dangerous:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)"
    ]
  },

  "enableAllProjectMcpServers": true | false,
  "enabledMcpjsonServers": ["server1", "server2"],
  "disabledMcpjsonServers": ["server3"],
  "useEnterpriseMcpConfigOnly": true | false
}
```

**Note:** Only plugin-related fields are used by agent.py. Other fields are for Claude Code CLI.

### Plugin Spec Format (Agent SDK)

**What agent.py passes to ClaudeAgentOptions:**

```python
plugins = [
    {
        "type": "local",
        "path": "/absolute/path/to/plugin"
    }
]
```

**Path resolution examples:**

```python
# Input: "general@cc-marketplace-developers"
# Marketplace location: /tmp/marketplaces/cc-marketplace-developers/
# Plugin location: /tmp/marketplaces/cc-marketplace-developers/plugins/general/
# Build context: build-context/plugins/cc-marketplace-developers/plugins/general/
# Container: /app/plugins/cc-marketplace-developers/plugins/general/
# SDK spec: {"type": "local", "path": "/app/plugins/cc-marketplace-developers/plugins/general"}
```

### Error Handling Strategy

**Graceful degradation:**

1. **Missing settings.json**
   - Log warning
   - Continue with empty plugin list
   - Agent works without plugins

2. **Invalid JSON syntax**
   - Log error with details
   - Skip that settings file
   - Use other config if available

3. **Plugin not found at path**
   - Log warning with plugin name
   - Skip that plugin
   - Load other plugins successfully

4. **Marketplace clone failure**
   - Log error
   - Continue with other marketplaces
   - Warn about missing plugins

5. **All plugins fail to load**
   - Log critical warning
   - Agent still starts
   - Commands/skills limited to built-in

**Logging levels:**

- `INFO`: Successful plugin loads
- `WARNING`: Missing plugins, skipped items
- `ERROR`: Failed to read configs, clone failures
- `CRITICAL`: No plugins loaded (expected some)

---

## Success Criteria

### Functional Requirements

- ✅ Two marketplaces created and operational
- ✅ Config repos declare plugins via settings.json
- ✅ Build process reads settings.json and clones marketplaces
- ✅ Build process copies enabled plugins to build context
- ✅ Container images include plugins at `/app/plugins/`
- ✅ agent.py reads settings.json from both configs
- ✅ agent.py merges plugin lists (project overrides master)
- ✅ agent.py resolves plugin paths correctly
- ✅ agent.py loads plugins via Agent SDK
- ✅ All existing functionality works via plugins
- ✅ No breaking changes for existing workflows

### Developer Experience

- ✅ Clone template and trust folder → plugins auto-install
- ✅ All commands work in Claude Code CLI
- ✅ Skills trigger correctly
- ✅ Agents work as expected
- ✅ Clear error messages on failures
- ✅ Documentation complete and accurate

### Deployment Experience

- ✅ Build process completes successfully
- ✅ Container includes all enabled plugins
- ✅ Ray actors start with plugins loaded
- ✅ Plugins available in Kodosumi conversations
- ✅ No performance degradation
- ✅ Logs show plugin loading clearly

### Maintainability

- ✅ Plugins versioned independently
- ✅ Easy to add new plugins
- ✅ Easy to disable plugins
- ✅ Clear ownership of components
- ✅ Documentation maintained
- ✅ Examples and templates provided

### Testing

- ✅ Fresh setup from scratch works
- ✅ Build process tested end-to-end
- ✅ Deployment tested end-to-end
- ✅ Custom plugins tested
- ✅ Edge cases handled gracefully
- ✅ Performance acceptable

---

## References

### Official Documentation

**Claude Code Plugin System:**
- **Plugin Overview**: https://docs.claude.com/en/docs/claude-code/plugins
- **Plugin Marketplaces**: https://docs.claude.com/en/docs/claude-code/plugin-marketplaces
- **Plugin Reference**: https://docs.claude.com/en/docs/claude-code/plugins-reference
- **Develop Complex Plugins**: https://docs.claude.com/en/docs/claude-code/plugins#develop-more-complex-plugins
- **Settings.json Reference**: https://docs.claude.com/en/docs/claude-code/settings

**Claude Agent SDK:**
- **Plugin Support**: https://docs.claude.com/en/api/agent-sdk/plugins

### Related Specifications

- `docs/ARCHITECTURE.md` - Overall system architecture
- `docs/DEVELOPMENT.md` - Development guidelines
- `CLAUDE.md` - Project instructions

### Implementation Files

**To be created:**
- `cc-marketplace-developers/` - Developer marketplace repo
- `cc-marketplace-agents/` - Agent marketplace repo

**To be modified:**
- `claude_hitl_template/agent.py` - Plugin loader
- `.claude/skills/docker-build/scripts/build.sh` - Build process
- `Dockerfile` - Container build
- `cc-master-agent-config/.claude/settings.json` - Plugin declarations
- `cc-example-agent-config/.claude/settings.json` - Plugin declarations

**To be removed:**
- `.claude/commands/` - Migrated to plugins
- `.claude/skills/` - Migrated to plugins
- `.claude/agents/` - Migrated to plugins

---

## Appendix: Plugin Structure Examples

### Example Plugin: general

**Location:** `cc-marketplace-developers/plugins/general/`

```
general/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── git-helper.md
│   ├── file-search.md
│   └── env-check.md
├── skills/
│   └── common-utils/
│       └── SKILL.md
├── README.md
└── LICENSE
```

**plugin.json:**
```json
{
  "name": "general",
  "version": "1.0.0",
  "description": "General-purpose development utilities for HITL template",
  "author": {
    "name": "HITL Template Team",
    "email": "team@example.com"
  },
  "keywords": ["dev", "utils", "helpers", "git", "files"],
  "license": "MIT"
}
```

**commands/git-helper.md:**
```markdown
---
description: Git operation helpers for common workflows
---

# Git Helper

Provides assistance with common git operations:
- Checking repository status
- Creating branches
- Managing commits
- Viewing history

When the user asks about git operations, help them with the appropriate commands and best practices.
```

### Example Plugin: master-core

**Location:** `cc-marketplace-agents/plugins/master-core/`

```
master-core/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── cc-deploy.md
│   ├── cc-setup.md
│   └── cc-shutdown.md
├── agents/
│   ├── deployment.md
│   └── setup.md
├── skills/
│   ├── docker-build/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── build.sh
│   ├── prerequisite-check/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── check.sh
│   └── vm-setup/
│       ├── SKILL.md
│       └── scripts/
│           └── setup-vm.sh
├── README.md
└── LICENSE
```

**plugin.json:**
```json
{
  "name": "master-core",
  "version": "1.0.0",
  "description": "Core master agent capabilities for HITL deployment and setup",
  "author": {
    "name": "HITL Template Team",
    "email": "team@example.com"
  },
  "keywords": ["deployment", "setup", "docker", "ray", "core"],
  "license": "MIT"
}
```

---

**End of Specification**

This document is a living specification and should be updated as the implementation progresses and new insights are gained.
