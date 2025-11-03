---
description: Stop all services (Ray cluster + Kodosumi services)
allowed-tools: [Bash]
---

Stop all running services in the OrbStack VM.

This command stops:
1. Kodosumi services (spooler + admin panel)
2. Ray cluster

Run: `just orb-down`

Use this at the end of your development session or before rebooting.
