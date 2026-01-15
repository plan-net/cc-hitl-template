# Container Versioning

This document describes how to build, version, and deploy container images.

## Overview

Container images use semantic versioning (`v1.0.1`) instead of `:latest` to ensure:
- Reproducible deployments
- Easy rollback
- Clear traceability via git commit

## Build Script

```bash
./scripts/build-container.sh <version>
```

### Usage

```bash
# Build and push v1.0.1
./scripts/build-container.sh v1.0.1

# Build only (no push)
./scripts/build-container.sh v1.0.1 --no-push
```

### What It Does

1. Creates `.image-info.json` with version and git info
2. Builds image with version tag AND `:latest`
3. Pushes both tags to ghcr.io
4. Captures and stores digest

### Output

```
Image Tags:
  - ghcr.io/basteiz/claude-hitl-worker:v1.0.1
  - ghcr.io/basteiz/claude-hitl-worker:latest

Digest:
  - sha256:5f677bd01e...

To use in Expose config:
  CONTAINER_IMAGE_URI: "ghcr.io/basteiz/claude-hitl-worker:v1.0.1"
```

## Image Metadata

Each image contains `/app/.image-info.json`:

```json
{
    "version": "1.0.1",
    "tag": "v1.0.1",
    "build_timestamp": "2026-01-14T17:00:00Z",
    "github_username": "basteiz",
    "image_name": "ghcr.io/basteiz/claude-hitl-worker",
    "digest": "sha256:5f677bd01e...",
    "git": {
        "commit": "012ab20",
        "commit_full": "012ab207c16648292715e9d22dfa9b5e085356db",
        "branch": "main",
        "dirty": false
    }
}
```

## Agent Logs

When a container starts, the agent logs show:

```
Container Image
  Registry Path: ghcr.io/basteiz/claude-hitl-worker
  Tag: v1.0.1
  Digest: sha256:5f677bd01e...
  Version: 1.0.1
  Git: 012ab20 (main)
  Built: 2026-01-14T17:00:00Z

Resource Allocation
  CPUs: 1
  Memory: 2.0 GB
```

## Deployment Workflow

### 1. Make Code Changes

Edit `claude_hitl_template/agent.py`, `query.py`, etc.

### 2. Sync to VM

```bash
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
  ./ ray-cluster@orb:/home/kodosumi/dev/cc-hitl-template/
```

### 3. Build New Version

```bash
orb -m ray-cluster bash -c "cd /home/kodosumi/dev/cc-hitl-template && \
  sudo chown -R kodosumi:kodosumi . && \
  sudo -u kodosumi bash scripts/build-container.sh v1.0.2"
```

### 4. Update Expose Config

Via Kodosumi Expose API, update:
```yaml
CONTAINER_IMAGE_URI: "ghcr.io/basteiz/claude-hitl-worker:v1.0.2"
```

### 5. Boot

```bash
curl -c /tmp/k.txt "http://localhost:3370/login?name=admin&password=admin"
curl -b /tmp/k.txt -X POST "http://localhost:3370/boot"
```

### 6. Verify

Start new HITL session and check logs show `v1.0.2`.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.1 | 2026-01-14 | Azure Foundry support, versioned builds |
| v1.0.0 | 2026-01-10 | Initial release |

## Troubleshooting

### Old Container Still Running

Ray caches containers. Clean old ones:

```bash
orb -m ray-cluster bash -c "sudo -u kodosumi podman rm -f \$(sudo -u kodosumi podman ps -aq)"
```

### Digest Shows "unknown"

Container was built before `.image-info.json` was added. Rebuild with new script.

### Version Not Updating

1. Verify rsync completed
2. Verify build script ran successfully
3. Verify Expose config has new version tag
4. Clean old containers and restart session
