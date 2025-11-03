---
description: Full rebuild and deploy workflow (build image + deploy to Ray)
allowed-tools: [Bash]
---

Complete workflow: build new Docker image and deploy to Ray cluster.

Use this when you've made changes that require a new container image
(e.g., config changes, dependency updates).

## Your Task

### Phase 1: Build Docker Image

1. **Pre-flight checks:**
   ```bash
   [ -f .env ] && echo ".env exists" || echo "ERROR: .env not found"
   source .env
   [ -n "$GITHUB_TOKEN" ] && echo "GITHUB_TOKEN set" || echo "ERROR: GITHUB_TOKEN missing"
   ```

2. **Build and push image:**
   ```bash
   ./build-and-push.sh
   ```

3. **Validate Phase 1:**
   - Build completed without errors
   - Image pushed to ghcr.io/plan-net/claude-hitl-worker:latest
   - Build configs cleaned up

### Phase 2: Deploy to Ray

4. **Deploy to Ray cluster:**
   ```bash
   just orb-deploy
   ```

5. **Validate Phase 2:**
   - Code synced to OrbStack VM
   - Deployment completed successfully
   - Ray cluster running

6. **Final validation:**
   ```bash
   just orb-status
   curl -s -o /dev/null -w "%{http_code}" http://localhost:3370
   ```

7. **Report results to user:**
   - ✅ If both phases succeeded:
     ```
     Rebuild and deploy completed successfully!

     Phase 1: Docker Image ✓
     - Image: ghcr.io/plan-net/claude-hitl-worker:latest
     - Configs: cc-master-agent-config + cc-example-agent-config

     Phase 2: Deployment ✓
     - Code synced to OrbStack VM
     - Application deployed to Ray cluster
     - Services running

     Access:
     - Admin Panel: http://localhost:3370
     - Ray Dashboard: http://localhost:8265

     Ray will use the new image when creating new actors.
     ```

   - ❌ If Phase 1 failed:
     ```
     Phase 1 (Build) failed!

     Error: [show build error]

     The deployment was NOT attempted.

     Fix the build issue and try again.
     See /cc-build-and-push-image for troubleshooting.
     ```

   - ❌ If Phase 2 failed:
     ```
     Phase 1 (Build) succeeded, but Phase 2 (Deploy) failed!

     Image built: ghcr.io/plan-net/claude-hitl-worker:latest ✓
     Deploy error: [show deploy error]

     Troubleshooting:
     - Check logs: just orb-logs
     - Verify Ray: just orb-status
     - Try manual deploy: /cc-deploy
     ```

## Success Criteria

**Phase 1:**
- Docker image built successfully
- Image pushed to ghcr.io

**Phase 2:**
- Code deployed to Ray cluster
- Services accessible
- No errors in deployment

## Notes

The new image will be: ghcr.io/plan-net/claude-hitl-worker:latest

Ray will automatically pull the updated image when creating new actors.
Existing actors will continue using the old image until restarted.
