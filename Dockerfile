# Dockerfile for Claude HITL Worker
# This container runs ClaudeSessionActor with isolated .claude/ folders
#
# Purpose:
#   - Isolate .claude/ configuration between template and project-specific usage
#   - Provide reproducible execution environment
#   - Enable multiple independent Claude instances via Ray's image_uri
#
# Architecture:
#   - template_user/.claude/: Generic template behavior (baked into image)
#   - Project .claude/: Project-specific configuration (from deployed code)
#   - Merged via ClaudeAgentOptions(setting_sources=["user", "project", "local"])

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

# Copy template_user/.claude/ into image (generic template behavior)
COPY template_user/.claude /app/template_user/.claude

# Set HOME to template_user so "user" settings load from there
# This enables ClaudeAgentOptions(setting_sources=["user", ...]) to find template config
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
