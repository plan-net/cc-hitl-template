---
description: Deploy application to Ray cluster in OrbStack VM
allowed-tools: [Bash]
---

Deploy the application to the Ray cluster running in the OrbStack VM.

This command:
1. Syncs code from macOS to the OrbStack VM
2. Deploys to Ray using koco

## Your Task

1. **Execute the deployment command:**
   ```bash
   just orb-deploy
   ```

2. **Monitor deployment output:**
   - Watch for successful code sync
   - Check for "Deployment successful" or similar confirmation
   - Note any warnings or errors during deployment

3. **Validate deployment succeeded:**
   - Check Ray deployment status:
     ```bash
     just orb-status
     ```
     Expected: Ray cluster running

   - Verify Admin Panel is accessible:
     ```bash
     curl -s -o /dev/null -w "%{http_code}" http://localhost:3370
     ```
     Expected: HTTP 200

4. **Report results to user:**
   - ✅ If deployment succeeded:
     ```
     Deployment successful!

     - Code synced to OrbStack VM
     - Application deployed to Ray cluster
     - Admin Panel: http://localhost:3370
     - Ray Dashboard: http://localhost:8265

     Next: Test your changes in the Admin Panel
     ```

   - ❌ If deployment failed:
     ```
     Deployment failed!

     Error: [show error from deployment]

     Troubleshooting:
     - Check logs: just orb-logs
     - Verify Ray is running: just orb-status
     - Try restarting: just orb-restart
     ```

## Success Criteria

- `just orb-deploy` completes without errors
- Code successfully synced to VM
- Ray cluster is running
- Admin Panel is accessible
- No deployment errors in output

## Notes

This handles all SSH connection and deployment automatically.
Use this after making code changes to update the running application.
