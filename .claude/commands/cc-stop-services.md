---
description: Stop all services (Ray cluster + Kodosumi services)
allowed-tools: [Bash]
---

Stop all running services in the OrbStack VM.

This command stops:
1. Kodosumi services (spooler + admin panel)
2. Ray cluster

## Your Task

1. **Execute the shutdown command:**
   ```bash
   just orb-down
   ```

2. **Validate services stopped successfully:**
   - Check Ray cluster status:
     ```bash
     just orb-status
     ```
     Expected: "Ray not running"

   - Verify ports are no longer accessible:
     ```bash
     curl -s -o /dev/null -w "%{http_code}" http://localhost:8265 || echo "Port 8265 closed"
     curl -s -o /dev/null -w "%{http_code}" http://localhost:3370 || echo "Port 3370 closed"
     ```
     Expected: Ports should not respond or return connection refused

3. **Report results to user:**
   - ✅ If all services stopped successfully:
     ```
     All services stopped successfully!

     - Ray cluster: Stopped
     - Ray Dashboard: Not accessible
     - Admin Panel: Not accessible
     - OrbStack VM: Still running (normal)
     ```

   - ❌ If services are still running:
     ```
     Some services are still running:

     - Ray Status: [status]

     Try: just orb-restart
     ```

## Success Criteria

- `just orb-down` completes without errors
- Ray cluster status shows "Ray not running"
- Dashboard and Admin Panel ports are not accessible
- OrbStack VM remains running (expected behavior)

## Notes

Use this at the end of your development session or before rebooting.
The OrbStack VM itself stays running in the background - this is normal.
