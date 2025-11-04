# Dockerfile for Claude HITL Worker
# This container runs ClaudeSessionActor with isolated .claude/ folders
#
# Purpose:
#   - Isolate .claude/ configuration between template and project-specific usage
#   - Provide reproducible execution environment
#   - Enable multiple independent Claude instances via Ray's image_uri
#
# Architecture:
#   - cc-master-agent-config/.claude/: Generic template behavior (baked into image)
#   - cc-example-agent-config/.claude/: Project-specific configuration (baked into image)
#   - Merged via ClaudeAgentOptions(setting_sources=["user", "project", "local"])
#
# Build Args:
#   - MASTER_CONFIG_PATH: Path to cc-master-agent-config/.claude directory
#   - PROJECT_CONFIG_PATH: Path to cc-example-agent-config/.claude directory
#
# Container Folder Structure:
#   /app/
#   ├── template_user/.claude/     # Master config (user-level settings)
#   ├── .claude/                   # Project config (project-specific settings)
#   ├── plugins/                   # Baked marketplace plugins
#   │   ├── cc-marketplace-developers/
#   │   │   └── plugins/
#   │   │       ├── general/
#   │   │       └── claude-agent-sdk/
#   │   └── cc-marketplace-agents/
#   │       └── plugins/
#   │           ├── master-core/
#   │           └── hitl-example/
#   └── claude_hitl_template/      # Application code
#
# All owned by ray:users for proper permissions
# HOME=/app/template_user so SDK "user" settings resolve to master config

FROM rayproject/ray:2.51.1-py312

# Switch to root for installation
USER root

# Install Node.js 18 (required for Claude CLI)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies from pyproject.toml
# Dependencies: claude-agent-sdk, kodosumi, ray, python-dotenv, pytest
RUN pip install --no-cache-dir \
    claude-agent-sdk>=0.1.6 \
    kodosumi>=1.0.0 \
    python-dotenv>=1.1.0 \
    pytest>=8.4.1

# Build args for config paths
ARG MASTER_CONFIG_PATH=template_user/.claude
ARG PROJECT_CONFIG_PATH=project/.claude

# Copy master agent config (template/user-level settings)
COPY ${MASTER_CONFIG_PATH} /app/template_user/.claude

# Copy project agent config (project-specific settings)
# SDK looks for "project" settings at {cwd}/.claude/, so copy to /app/.claude/
COPY ${PROJECT_CONFIG_PATH} /app/.claude

# Copy plugins from marketplaces (populated by build.sh if configured)
# Plugins are organized as /app/plugins/{marketplace}/plugins/{plugin}/
COPY build_configs/plugins /app/plugins

# Fix ownership of all config directories for ray user
# This prevents permission errors when Claude CLI or SDK tries to access configs
RUN chown -R ray:users /app/template_user/.claude /app/.claude /app/plugins

# Set HOME to template_user so "user" settings load from master config
# This enables ClaudeAgentOptions(setting_sources=["user", "project", "local"]) to find configs
# - "user" → $HOME/.claude/ = /app/template_user/.claude/ (master config)
# - "project" → {cwd}/.claude/ = /app/.claude/ (project config)
ENV HOME=/app/template_user

# Create working directory
WORKDIR /app

# Verify installations
RUN node --version && \
    claude --version && \
    python --version && \
    ray --version

# Switch back to ray user for runtime (Ray base image default user)
USER ray

# Default command (Ray will override this when spawning actors)
CMD ["python"]
