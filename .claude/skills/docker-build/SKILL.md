---
name: docker-build
description: Build and push Docker images with baked .claude configurations from git repos
---

# Docker Build Skill

## Purpose

This skill builds Docker images for the Claude HITL worker with baked-in `.claude` configuration folders from separate git repositories.

## When to Use

Use this skill when you need to rebuild the Docker image because:
- Configuration repos have new commits (remote changes detected)
- Local `.claude/` folders have been modified
- Dependencies or Dockerfile have changed
- You need to ensure latest configurations are baked into the image

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
bash .claude/skills/docker-build/build.sh
```

## Output Format

The skill outputs deployment state in a parseable format:

```
=== DEPLOYMENT STATE ===
MASTER_CONFIG_COMMIT=abc123...
PROJECT_CONFIG_COMMIT=def456...
DOCKER_IMAGE_TAG=ghcr.io/<username>/claude-hitl-worker:latest
DOCKER_IMAGE_DIGEST=sha256:abc123def456...
IMAGE_SIZE=1200MB
BUILD_TIMESTAMP=2025-11-03T12:30:45Z
BUILD_STATUS=success
========================
```

This output is captured by the deployment agent for state tracking and verification.

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
