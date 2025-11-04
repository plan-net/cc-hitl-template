# Plugin System Guide

Comprehensive guide to the plugin-based architecture in the Claude + Kodosumi HITL template.

## Overview

This template uses a **plugin-based architecture** for organizing and distributing reusable capabilities:

- **Commands**: Slash commands like `/cc-setup`, `/cc-deploy`
- **Agents**: Autonomous multi-step orchestrators
- **Skills**: Reusable shell scripts with documentation
- **Hooks**: Event-triggered automations
- **MCP Servers**: Model Context Protocol integrations

All these components are distributed via **plugin marketplaces** - GitHub repositories containing structured plugin packages.

---

## Architecture

### Two Types of Plugins

**1. Development Plugins** (`cc-marketplace-developers`)
- Installed on: Your local machine
- Used by: Claude Code CLI on your development machine
- Purpose: Development tools, testing utilities, setup automation
- Installation: Automatic via Claude Code CLI
- Location: `~/.cache/claude-code/plugins/`

**2. Runtime Plugins** (`cc-marketplace-agents`)
- Installed in: Container images
- Used by: Containerized Ray Actors running Claude SDK
- Purpose: Agent capabilities, HITL operations, production features
- Installation: Baked into image at build time
- Location: `/app/plugins/{marketplace}/plugins/{plugin}/`

### Plugin Loading Flow

**Local Development**:
```
.claude/settings.json
        ↓
Claude Code CLI reads config
        ↓
Downloads from GitHub
        ↓
Installs to ~/.cache/claude-code/plugins/
        ↓
Available immediately to main agent
```

**Container Deployment**:
```
Config repos (master + project)
        ↓
build.sh reads settings.json
        ↓
Clones marketplaces from GitHub
        ↓
Copies enabled plugins to build context
        ↓
Dockerfile bakes into image
        ↓
agent.py loads at runtime
```

### Container Folder Structure

When plugins are baked into the container image, they're organized as:

```
/app/
├── template_user/.claude/          # Master config
│   └── settings.json               # Declares plugins to load
├── .claude/                        # Project config
│   └── settings.json               # Overrides master
└── plugins/                        # Marketplace plugins
    └── {marketplace}/
        └── plugins/
            └── {plugin}/
                ├── commands/
                ├── agents/
                └── skills/
```

**Example**:
```
/app/plugins/cc-marketplace-agents/plugins/master-core/
├── commands/
│   ├── cc-deploy.md
│   ├── cc-setup.md
│   └── cc-shutdown.md
├── agents/
│   ├── deployment.md
│   └── setup.md
└── skills/
    ├── docker-build/
    ├── prerequisite-check/
    └── vm-setup/
```

**Permission handling**:
All directories are owned by `ray:users` to prevent permission errors when the Claude SDK subprocess accesses configs at runtime.

---

## Marketplace Configuration

### Available Marketplaces

#### cc-marketplace-developers

**Repository**: `https://github.com/plan-net/cc-marketplace-developers`

**Purpose**: Development-time tools and utilities

**Available Plugins**:
- `general` - General development utilities
- `claude-agent-sdk` - SDK-specific helpers and documentation

**Typical Use Cases**:
- Local development assistance
- Testing and debugging tools
- Setup and configuration helpers

#### cc-marketplace-agents

**Repository**: `https://github.com/plan-net/cc-marketplace-agents`

**Purpose**: Runtime capabilities for deployed agents

**Available Plugins**:
- `master-core` - Core template operations (setup, deploy, shutdown)
- `hitl-example` - Example HITL patterns and templates

**What master-core provides**:
- `/cc-setup` - Guided setup automation
- `/cc-deploy` - Intelligent deployment
- `/cc-shutdown` - Clean service shutdown
- `docker-build` skill - Container image building
- `prerequisite-check` skill - Dependency validation
- `vm-setup` skill - OrbStack VM creation
- Setup agent - System analysis and configuration
- Deployment agent - Change detection and orchestration

---

## Managing Plugins

### View Current Configuration

Check which marketplaces and plugins are enabled:

```bash
# View settings
cat .claude/settings.json

# Look for these sections:
# - extraKnownMarketplaces: Available marketplaces
# - enabledPlugins: Which plugins are active
```

### Enable a Plugin

1. **Edit `.claude/settings.json`**:
```json
{
  "enabledPlugins": {
    "existing-plugin@marketplace": true,
    "new-plugin@marketplace": true  // Add this line
  }
}
```

2. **For local development**:
```bash
# Restart Claude Code
# Cmd/Ctrl + Q, then relaunch
claude
```

3. **For container deployment**:
```bash
# Rebuild container image
/cc-deploy  # In Claude Code (detects config change)
# OR
bash .claude/skills/docker-build/scripts/build.sh
```

### Disable a Plugin

1. **Edit `.claude/settings.json`**:
```json
{
  "enabledPlugins": {
    "plugin-to-disable@marketplace": false  // Change to false or remove
  }
}
```

2. **Restart Claude Code** (local) or **rebuild image** (deployment)

### Add a Custom Marketplace

1. **Edit `.claude/settings.json`**:
```json
{
  "extraKnownMarketplaces": {
    "my-custom-marketplace": {
      "source": {
        "source": "github",
        "repo": "my-org/my-marketplace"
      }
    }
  }
}
```

2. **Supported source types**:
   - `"source": "github"` - GitHub repository
   - `"source": "git"` - Any git URL

3. **For GitHub**:
```json
{
  "source": {
    "source": "github",
    "repo": "org-name/repo-name"
  }
}
```

4. **For custom git URL**:
```json
{
  "source": {
    "source": "git",
    "url": "https://gitlab.com/org/repo.git"
  }
}
```

---

## Plugin Structure

### Standard Layout

Each plugin follows this structure:

```
plugin-name/
├── marketplace.json       # Plugin metadata (optional)
├── commands/              # Slash commands
│   ├── my-command.md
│   └── another-command.md
├── agents/                # Autonomous agents
│   ├── my-agent.md
│   └── another-agent.md
├── skills/                # Reusable capabilities
│   └── my-skill/
│       ├── SKILL.md       # Documentation
│       └── scripts/       # Executable scripts
│           └── run.sh
├── hooks/                 # Event-triggered scripts
│   └── pre-commit.sh
└── mcp_servers/           # MCP server configs
    └── my-server.json
```

### Components Explained

**Commands** (`commands/*.md`):
- Entry points for user interactions
- Trigger agents or run simple operations
- Example: `/cc-setup`, `/cc-deploy`

**Agents** (`agents/*.md`):
- Complex multi-step orchestration
- Analyze → Decide → Execute → Validate → Report
- Have their own context window
- Example: Setup agent, deployment agent

**Skills** (`skills/*/`):
- Reusable shell scripts with documentation
- Progressive disclosure pattern (SKILL.md + scripts/)
- Can be invoked by agents or directly
- Example: docker-build, prerequisite-check

**Hooks** (`hooks/*.sh`):
- Event-triggered automations
- Run on specific events (tool calls, submissions)
- Example: Auto-format code, run tests

**MCP Servers** (`mcp_servers/*.json`):
- Model Context Protocol integrations
- Extend Claude's capabilities
- Example: Database access, API integrations

---

## Creating Custom Plugins

### Step 1: Create Plugin Structure

**For project-specific plugins** (in local `.claude/`):
```bash
mkdir -p .claude/commands
mkdir -p .claude/agents
mkdir -p .claude/skills/my-skill/scripts
```

**For shared plugins** (in marketplace repo):
```bash
cd ~/path/to/my-marketplace
mkdir -p plugins/my-plugin/{commands,agents,skills}
```

### Step 2: Add Plugin Content

**Example command** (`commands/my-command.md`):
```markdown
---
description: Brief description of what this command does
---

Detailed instructions for what this command should do.

## Task

When the user runs /my-command, you should:
1. Analyze the current state
2. Perform the necessary actions
3. Report results
```

**Example skill** (`skills/my-skill/SKILL.md`):
```markdown
---
description: Brief description of the skill capability
---

## Usage

This skill does X, Y, and Z.

## How to Use

```bash
bash scripts/run.sh [arguments]
```

## Examples

...
```

**Example skill script** (`skills/my-skill/scripts/run.sh`):
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Running my skill..."
# Your script logic here
```

### Step 3: Make Scripts Executable

```bash
chmod +x skills/*/scripts/*.sh
```

### Step 4: Enable Plugin

**In `.claude/settings.json`**:
```json
{
  "enabledPlugins": {
    "my-plugin@my-marketplace": true
  }
}
```

### Step 5: Test

**Local**:
```bash
# Restart Claude Code
claude

# Try your command
/my-command
```

**Container**:
```bash
# Rebuild image
/cc-deploy
```

---

## Plugin Development Best Practices

### Command Design

**Good command**:
- Clear description in frontmatter
- Specific task definition
- Error handling guidance
- Example usage

**Example**:
```markdown
---
description: Analyze codebase for security vulnerabilities
---

## Task

Scan the project for common security issues:
1. Check dependencies for known CVEs
2. Look for hardcoded secrets
3. Validate input sanitization
4. Report findings with severity levels

## Error Handling

If scanning tools are missing, guide user to install them.
```

### Skill Design

**Structure**:
```
skills/my-skill/
├── SKILL.md              # What it does, how to use
└── scripts/
    ├── check.sh          # Validation/verification
    ├── install.sh        # Setup/installation
    └── run.sh            # Main execution
```

**Best practices**:
- Keep SKILL.md focused on "what" and "why"
- Put "how" in shell scripts
- Make scripts idempotent (safe to run multiple times)
- Add clear error messages
- Return meaningful exit codes

### Agent Design

**Pattern to follow**:
```markdown
## Analysis Phase
1. Gather current state
2. Identify what needs to be done

## Decision Phase
3. Determine best approach
4. Check for prerequisites

## Execution Phase
5. Perform actions in order
6. Validate each step

## Reporting Phase
7. Summary of what was done
8. Next steps or recommendations
```

**Use TodoWrite for complex operations**:
- Creates visible progress tracking
- Allows user to see what's completed vs pending
- Provides clear checkpoints

---

## Troubleshooting

### Plugins Not Installing

**Symptom**: `/cc-setup` or other commands not found after restart

**Causes & Solutions**:

1. **Check settings.json exists**:
```bash
ls -la .claude/settings.json
# Should exist with marketplace + plugin config
```

2. **Verify marketplace accessibility**:
```bash
# Test GitHub access
curl -I https://github.com/plan-net/cc-marketplace-developers
# Should return 200 OK
```

3. **Check Claude Code cache**:
```bash
ls ~/.cache/claude-code/plugins/
# Should show installed plugins
```

4. **Force reinstall**:
```bash
# Remove cache
rm -rf ~/.cache/claude-code/plugins/

# Restart Claude Code
claude
# Plugins will reinstall
```

### Plugin Commands Not Working

**Symptom**: Command exists but doesn't work as expected

**Debug steps**:

1. **Check plugin is enabled**:
```bash
cat .claude/settings.json | grep "plugin-name@marketplace"
# Should show "true"
```

2. **Verify plugin structure**:
```bash
ls ~/.cache/claude-code/plugins/marketplace-name/plugins/plugin-name/
# Should show commands/, agents/, skills/, etc.
```

3. **Check command file**:
```bash
cat ~/.cache/claude-code/plugins/marketplace-name/plugins/plugin-name/commands/my-command.md
# Should have valid frontmatter and content
```

### Container Plugins Not Loading

**Symptom**: Plugins work locally but not in deployed containers

**Debug steps**:

1. **Check build process copied plugins**:
```bash
# During build, look for:
# "→ Copying plugins to build context..."
# "✓ Copied N plugins"
```

2. **Verify plugins in image**:
```bash
# Inspect running container
docker exec <container-id> ls -R /app/plugins/
# Should show marketplace/plugins/plugin-name/
```

3. **Check agent.py logs**:
```python
# Look for plugin loading logs:
# "PLUGIN LOADING"
# "Successfully loaded N plugins:"
# "  → /app/plugins/marketplace/plugins/plugin/"
```

4. **Verify settings in config repos**:
```bash
# Check master config
cat ~/path/to/master-config/.claude/settings.json

# Check project config
cat ~/path/to/project-config/.claude/settings.json

# Both should have marketplace + plugin declarations
```

### Build Process Can't Find Plugins

**Symptom**: Build fails with "Plugin not found at path"

**Causes**:

1. **Plugin name mismatch**:
```json
// settings.json says:
"my-plugin@my-marketplace": true

// But actual path is:
marketplaces/my-marketplace/plugins/different-name/
```

2. **Marketplace not cloned**:
   - Check marketplace URL is correct
   - Verify GitHub access token has repo access
   - Ensure marketplace repo exists and is accessible

3. **Plugin doesn't exist in marketplace**:
   - Check marketplace repo on GitHub
   - Verify plugin directory exists: `plugins/plugin-name/`

**Solution**:
```bash
# Manual test of build process
source .env
TMP_DIR=$(mktemp -d)

# Clone marketplace
git clone https://github.com/org/marketplace.git $TMP_DIR/marketplace

# Check plugin exists
ls $TMP_DIR/marketplace/plugins/
# Should show your plugin name
```

---

## Examples

### Example 1: Adding a Custom Marketplace

**Scenario**: You have an internal marketplace for company-specific plugins

1. **Create marketplace repo**:
```bash
mkdir my-company-marketplace
cd my-company-marketplace

# Create structure
mkdir -p plugins/internal-tools/{commands,skills}

# Add marketplace.json
cat > marketplace.json << 'EOF'
{
  "name": "my-company-marketplace",
  "description": "Internal company plugins",
  "version": "1.0.0"
}
EOF

# Commit and push to GitHub
git init
git add .
git commit -m "Initial marketplace structure"
git remote add origin git@github.com:my-company/marketplace.git
git push -u origin main
```

2. **Add to settings.json**:
```json
{
  "extraKnownMarketplaces": {
    "my-company-marketplace": {
      "source": {
        "source": "github",
        "repo": "my-company/marketplace"
      }
    }
  },
  "enabledPlugins": {
    "internal-tools@my-company-marketplace": true
  }
}
```

3. **Restart Claude Code**:
```bash
claude
# Marketplace will be cloned and plugins installed
```

### Example 2: Creating a Custom Skill

**Scenario**: Create a skill that runs database migrations

1. **Create skill structure**:
```bash
mkdir -p skills/db-migrate/scripts
```

2. **Write SKILL.md**:
```markdown
---
description: Run database migrations safely
---

## What This Skill Does

Runs pending database migrations with safety checks:
- Backs up database before running
- Validates migration files
- Runs migrations in transaction
- Verifies schema after completion

## Usage

```bash
bash scripts/run.sh [environment]
```

## Arguments

- `environment`: Target environment (dev, staging, prod)

## Examples

```bash
# Run migrations in development
bash scripts/run.sh dev

# Run migrations in staging
bash scripts/run.sh staging
```
```

3. **Write migration script** (`scripts/run.sh`):
```bash
#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT=${1:-dev}

echo "Running migrations for $ENVIRONMENT..."

# Backup database
pg_dump -h localhost -U user database > backup-$(date +%Y%m%d-%H%M%S).sql

# Run migrations
python manage.py migrate --database=$ENVIRONMENT

echo "✓ Migrations completed"
```

4. **Make executable**:
```bash
chmod +x skills/db-migrate/scripts/run.sh
```

5. **Test**:
```bash
bash skills/db-migrate/scripts/run.sh dev
```

### Example 3: Creating a Deployment Command

**Scenario**: Custom command for deploying to production

1. **Create command** (`commands/deploy-prod.md`):
```markdown
---
description: Deploy to production with safety checks
---

## Task

Deploy the current application to production:

1. **Pre-deployment checks**:
   - Run all tests
   - Check for uncommitted changes
   - Verify staging deployment is healthy

2. **Deployment**:
   - Build production Docker image
   - Push to registry
   - Deploy to production cluster
   - Run database migrations
   - Restart services

3. **Post-deployment validation**:
   - Health check all services
   - Run smoke tests
   - Monitor error rates for 5 minutes

4. **Rollback plan**:
   - If any validation fails, immediately rollback
   - Restore previous image
   - Alert team

## Error Handling

If any step fails:
- Stop immediately
- Show clear error message
- Provide rollback instructions
- Do NOT proceed to next step
```

2. **Enable in settings**:
```json
{
  "enabledPlugins": {
    "my-plugin@my-marketplace": true
  }
}
```

3. **Use**:
```bash
# In Claude Code
/deploy-prod
```

---

## Advanced Topics

### Plugin Versioning

**Pin marketplace to specific commit**:
```json
{
  "extraKnownMarketplaces": {
    "my-marketplace": {
      "source": {
        "source": "github",
        "repo": "my-org/marketplace",
        "ref": "abc123def456"  // Git commit SHA
      }
    }
  }
}
```

**Benefits**:
- Reproducible builds
- No unexpected plugin updates
- Rollback capability

### Multi-Environment Plugins

**Use different plugins per environment**:

**Development** (local `.claude/settings.json`):
```json
{
  "enabledPlugins": {
    "dev-tools@my-marketplace": true,
    "debug-helpers@my-marketplace": true
  }
}
```

**Production** (config repo `.claude/settings.json`):
```json
{
  "enabledPlugins": {
    "prod-monitoring@my-marketplace": true,
    "security-checks@my-marketplace": true
  }
}
```

### Plugin Dependencies

**Document dependencies in SKILL.md**:
```markdown
## Prerequisites

This skill requires:
- Python 3.12+
- PostgreSQL client (`psql`)
- AWS CLI configured

## Installation

```bash
# Install required tools
brew install postgresql awscli
```
```

**Check dependencies in scripts**:
```bash
#!/usr/bin/env bash
set -euo pipefail

# Check prerequisites
if ! command -v psql &> /dev/null; then
    echo "Error: psql not found. Install PostgreSQL client."
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "Error: aws CLI not found. Install AWS CLI."
    exit 1
fi

# Continue with main logic...
```

---

## Reference

### Plugin Specification

**Full plugin structure**:
```
plugin-name/
├── marketplace.json       # Metadata (optional)
├── README.md             # Plugin documentation
├── commands/             # Slash commands
│   └── *.md
├── agents/               # Autonomous agents
│   └── *.md
├── skills/               # Shell script capabilities
│   └── skill-name/
│       ├── SKILL.md
│       └── scripts/
│           └── *.sh
├── hooks/                # Event-triggered scripts
│   └── *.sh
└── mcp_servers/          # MCP server configs
    └── *.json
```

### marketplace.json Schema

```json
{
  "name": "marketplace-name",
  "description": "Human-readable description",
  "version": "1.0.0",
  "plugins": {
    "plugin-name": {
      "description": "Plugin description",
      "version": "1.0.0",
      "dependencies": []
    }
  }
}
```

### Settings Format

**Complete settings.json example**:
```json
{
  "extraKnownMarketplaces": {
    "marketplace-1": {
      "source": {
        "source": "github",
        "repo": "org/repo"
      }
    },
    "marketplace-2": {
      "source": {
        "source": "git",
        "url": "https://gitlab.com/org/repo.git"
      }
    }
  },
  "enabledPlugins": {
    "plugin-1@marketplace-1": true,
    "plugin-2@marketplace-1": true,
    "plugin-3@marketplace-2": true
  },
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(docker:*)"
    ]
  }
}
```

---

## Additional Resources

- **Claude Code Documentation**: https://docs.claude.com/en/docs/claude-code
- **Plugin System Docs**: https://docs.claude.com/en/docs/claude-code/settings
- **Template Documentation**: [../CLAUDE.md](../CLAUDE.md)
- **Setup Guide**: [SETUP.md](SETUP.md)
- **Architecture Details**: [../CLAUDE.md#plugin-architecture](../CLAUDE.md#plugin-architecture)

---

**Questions?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue on GitHub.
