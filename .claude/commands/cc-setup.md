---
description: Autonomous setup automation for complete project installation
allowed-tools: [Task]
---

Set up the entire Claude + Kodosumi HITL development environment automatically.

## Your Task

Use the Task tool to invoke the setup agent. Tell the agent to:
1. Detect the operating system and current environment
2. Check prerequisites (Python, OrbStack/Docker, Node.js, Claude CLI)
3. Guide through missing installations
4. Set up OrbStack VM (macOS) or Docker (Linux)
5. Configure .env file with required secrets
6. Clone configuration repositories
7. Build/pull Docker images
8. Start and validate full stack
9. Report final status and next steps

The setup agent will handle everything autonomously and report back when done.

## Expected Outcome

After running `/cc-setup`, you should have:
- ✅ All prerequisites installed and verified
- ✅ OrbStack VM running (macOS) or Docker ready (Linux)
- ✅ Configuration repositories cloned
- ✅ .env file configured
- ✅ Docker image built/pulled
- ✅ Ray cluster running in VM
- ✅ Kodosumi services deployed
- ✅ Admin panel accessible at http://localhost:3370

The agent will guide you through any manual steps (e.g., providing API keys) and fix common issues automatically.
