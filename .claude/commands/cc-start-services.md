---
description: Start full development stack (Ray + deploy + Kodosumi services)
allowed-tools: [Bash]
---

Start the complete development environment in the OrbStack VM.

This command starts:
1. Ray cluster in the VM
2. Deploys the application
3. Starts Kodosumi spooler
4. Starts Kodosumi admin panel

Run: `just orb-up`

After completion, services will be available at:
- Ray Dashboard: http://localhost:8265
- Admin Panel: http://localhost:3370
