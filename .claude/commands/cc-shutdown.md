---
description: Shutdown all services (Kodosumi + Ray + VM)
allowed-tools: [Bash]
---

Shut down all running services cleanly.

## Your Task

1. **Execute shutdown:**
   ```bash
   just orb-down
   ```

2. **Validate everything stopped:**
   ```bash
   # Check Ray and VM status
   just orb-status

   # Check ports are closed
   curl -s --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:8265 || echo "8265 closed"
   curl -s --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:3370 || echo "3370 closed"

   # Check no koco processes
   ps aux | grep koco | grep -v grep || echo "No koco processes"
   ```

3. **Report results:**
   - ✅ If shutdown successful:
     ```
     ✅ All services stopped successfully!

     - Kodosumi services (macOS): Stopped
     - Ray cluster: Stopped
     - OrbStack VM: Stopped
     - Port 8265 (Ray Dashboard): Closed
     - Port 3370 (Admin Panel): Closed

     System is fully shut down.
     ```

   - ❌ If services still running:
     ```
     ⚠️ Some services may still be running:

     - [List what's still running]

     Manual cleanup:
     - Kill koco: pkill -f koco
     - Stop Ray: just orb-stop
     - Check processes: ps aux | grep -E 'koco|ray'
     ```

## Success Criteria

- `just orb-down` completes without errors
- No koco processes running on macOS
- Ray cluster stopped
- OrbStack VM stopped
- Ports 8265 and 3370 not accessible

## Notes

This command stops everything cleanly:
1. Stops Kodosumi services on macOS (koco spool, koco serve)
2. Stops Ray cluster in VM
3. Stops OrbStack VM

Use this at the end of your development session.
