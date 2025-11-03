---
description: Build Docker image with baked .claude configs and push to ghcr.io
allowed-tools: [Bash]
---

Build the Docker image with baked-in .claude configurations from both config repos and push to GitHub Container Registry.

Steps:
1. Validate .env file exists (contains GITHUB_TOKEN and GITHUB_USERNAME)
2. Load environment variables
3. Run build-and-push.sh script
4. Report success with next steps

Use bash commands to execute this workflow. Report any errors clearly.
