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

## Your Task

1. **Execute the startup command:**
   ```bash
   just orb-up
   ```

2. **Validate services started successfully:**
   - Check Ray Dashboard accessibility:
     ```bash
     curl -s -o /dev/null -w "%{http_code}" http://localhost:8265
     ```
     Expected: HTTP 200

   - Check Admin Panel accessibility:
     ```bash
     curl -s -o /dev/null -w "%{http_code}" http://localhost:3370
     ```
     Expected: HTTP 200

   - Check Ray status:
     ```bash
     just orb-status
     ```
     Expected: Ray cluster running

3. **Report results to user:**
   - ✅ If all services started successfully:
     ```
     Services started successfully!

     - Ray Dashboard: http://localhost:8265
     - Admin Panel: http://localhost:3370
     - Ray Status: Running
     ```

   - ❌ If any service failed to start:
     ```
     Some services failed to start:

     - Ray Dashboard: [status]
     - Admin Panel: [status]

     Check logs with: just orb-logs
     ```

## Success Criteria

- `just orb-up` completes without errors
- Ray Dashboard returns HTTP 200
- Admin Panel returns HTTP 200
- Ray cluster status shows "running"
