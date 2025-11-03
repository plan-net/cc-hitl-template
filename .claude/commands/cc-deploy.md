---
description: Deploy application to Ray cluster in OrbStack VM
allowed-tools: [Bash]
---

Deploy the application to the Ray cluster running in the OrbStack VM.

This command:
1. Syncs code from macOS to the OrbStack VM
2. Deploys to Ray using koco

Run: `just orb-deploy`

This handles all the SSH connection and deployment automatically.
