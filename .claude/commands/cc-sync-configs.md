---
description: Pull latest .claude configs from both repos and rebuild image
allowed-tools: [Bash]
---

Pull the latest configurations from both config repositories and rebuild the Docker image.

Config repositories:
- cc-master-agent-config (template/user-level settings)
- cc-example-agent-config (project-specific settings)

This command will:
1. Pull latest from cc-master-agent-config
2. Pull latest from cc-example-agent-config
3. Rebuild and push Docker image
4. Optionally deploy to Ray

Use this when configurations have been updated in the config repos.
