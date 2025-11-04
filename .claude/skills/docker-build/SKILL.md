---
name: docker-build
description: Build and push container images with baked-in `.claude` configuration folders from git repositories for Claude HITL Ray actors. Use this skill when remote configuration repositories have new commits that need to be baked into the container image, when local `.claude/` folders have been modified and need to be included in a fresh build, when the Dockerfile or project dependencies (requirements.txt, package.json) have changed, when deploying updated Claude Code commands, skills, or agent configurations to production, when the deployment agent detects configuration drift between local state and remote repositories, or when you need to ensure Ray actors are running with the latest immutable container image version with a new SHA256 digest.
---

# Container Build Skill

## When to use this skill

- When remote configuration repositories (master config or project config) have new commits that need to be baked into the container image
- When local `.claude/` folders have been modified and need to be included in a fresh build
- When the Dockerfile or project dependencies (requirements.txt, package.json, etc.) have changed
- When deploying updated Claude Code commands, skills, or agent configurations to production
- When the deployment agent detects configuration drift between local state and remote repositories via `git ls-remote`
- When you need to ensure Ray actors are running with the latest immutable container image version
- When updating the container image to get a new SHA256 digest for deployment tracking
- When troubleshooting issues related to stale configurations or mismatched container versions
- When the user explicitly requests to build a new container image or rebuild the worker image

## Purpose

This skill builds container images for the Claude HITL worker with baked-in `.claude` configuration folders from separate git repositories, ensuring Ray actors run with immutable, versioned configurations.

## How It Works

The skill:
1. Loads required environment variables from `.env`
2. Clones the latest `.claude` folders from configured git repos
3. Builds Docker image with these configurations
4. Pushes image to GitHub Container Registry (ghcr.io)
5. Captures complete deployment state including:
   - Commit hashes from config repos
   - Image digest (SHA256)
   - Image size and build timestamp

## Execution

The skill activates automatically when you describe needing to build a Docker image with updated configs.

Alternatively, run directly:

```bash
bash .claude/skills/docker-build/scripts/build.sh
```

## Output Format

The skill outputs deployment state in a parseable format:

```
=== DEPLOYMENT STATE ===
MASTER_CONFIG_COMMIT=abc123...
PROJECT_CONFIG_COMMIT=def456...
CONTAINER_IMAGE_URI=ghcr.io/<username>/claude-hitl-worker@sha256:abc123def456...
IMAGE_SIZE=1200MB
BUILD_TIMESTAMP=2025-11-03T12:30:45Z
BUILD_STATUS=success
========================
```

This output is captured by the deployment agent for state tracking and verification.

## Post-Build Actions

**CRITICAL**: After the build completes successfully, you MUST update configuration files with the new `CONTAINER_IMAGE_URI`:

### 1. Update `.env` file
Use the Edit tool to update the CONTAINER_IMAGE_URI variable:

```bash
CONTAINER_IMAGE_URI=ghcr.io/<username>/claude-hitl-worker@sha256:<new-digest>
```

### 2. Update `data/config/claude_hitl_template.yaml`
Use the Edit tool to update the runtime_env.env_vars section with **literal values**:

```yaml
runtime_env:
  env_vars:
    CONTAINER_IMAGE_URI: "ghcr.io/<username>/claude-hitl-worker@sha256:<new-digest>"
    ANTHROPIC_API_KEY: "sk-ant-your-actual-key-here"
```

**IMPORTANT**:
- Copy the EXACT literal value from your `.env` file for ANTHROPIC_API_KEY
- Do NOT use variable syntax like `"${ANTHROPIC_API_KEY}"` - it does NOT work
- Ray Serve YAML does NOT support variable substitution
- Both CONTAINER_IMAGE_URI and ANTHROPIC_API_KEY must be literal values

### 3. Verify consistency
Read both files to confirm they have matching values:
- CONTAINER_IMAGE_URI must match in both files
- ANTHROPIC_API_KEY must be the same literal key in both files

### Why Both Files?
- `.env` → Read by Python code (agent.py) at runtime via `os.getenv()`
- `yaml` → Read by Ray Serve, makes env vars available to the serve application
- **Must contain identical LITERAL values** for consistent configuration
- YAML does NOT support shell variable substitution like `${VAR_NAME}`

The digest format (`@sha256:...`) ensures Ray actors use the exact immutable image version, not the mutable `:latest` tag.

## Prerequisites

**Environment Variables** (in `.env`):
- `GITHUB_TOKEN` - Personal access token with `packages:write` scope
- `GITHUB_USERNAME` - Your GitHub username (for image path)
- `MASTER_CONFIG_REPO` - Git URL for master config repo
- `PROJECT_CONFIG_REPO` - Git URL for project config repo
- `ANTHROPIC_API_KEY` - Claude API key (baked into image)

**Tools Required**:
- Docker or Podman
- Git
- SSH keys for accessing config repos

## Output

**Success:**
- Docker image: `ghcr.io/<username>/claude-hitl-worker:latest`
- Image digest: `sha256:...` (unique identifier)
- Image pushed to registry
- Complete deployment state including:
  - Config repo commit hashes
  - Image digest for verification
  - Build timestamp and image size

**Failure:**
- Clear error messages about missing prerequisites
- Build logs for debugging
- Exit code 1

## Validation

After building, validate:

```bash
# Check image exists locally
docker images | grep claude-hitl-worker

# Verify image was pushed
docker pull ghcr.io/<username>/claude-hitl-worker:latest
```

## Integration

The deployment agent uses this skill when:
- Remote config repo changes detected (via `git ls-remote`)
- User confirms rebuild when prompted
- State file is updated with new commit hashes after successful build

## Notes

- Build typically takes 2-5 minutes
- Requires network access to GitHub
- Temporary files are cleaned up automatically
- Old local images are replaced (tag: latest)
