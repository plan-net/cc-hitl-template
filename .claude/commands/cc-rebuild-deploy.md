---
description: Full rebuild and deploy workflow (build image + deploy to Ray)
allowed-tools: [Bash]
---

Complete workflow: build new Docker image and deploy to Ray cluster.

Use this when you've made changes that require a new container image
(e.g., config changes, dependency updates).

Steps:
1. Build and push Docker image with baked configs
2. Deploy to Ray cluster in OrbStack VM

The new image will be: ghcr.io/plan-net/claude-hitl-worker:latest

Ray will automatically pull the updated image when creating new actors.
