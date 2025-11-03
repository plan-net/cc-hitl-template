---
description: Pull latest .claude configs from both repos and rebuild image
allowed-tools: [Bash]
argument-hint: [--deploy]
---

Pull the latest configurations from both config repositories and rebuild the Docker image.

Config repositories:
- cc-master-agent-config (template/user-level settings)
- cc-example-agent-config (project-specific settings)

## Your Task

1. **Explain what will happen:**
   The build script will clone fresh copies of both config repos,
   ensuring you get the absolute latest configurations.

2. **Pre-flight checks:**
   ```bash
   [ -f .env ] && echo ".env exists" || echo "ERROR: .env not found"
   source .env
   [ -n "$GITHUB_TOKEN" ] && echo "GITHUB_TOKEN set" || echo "ERROR: GITHUB_TOKEN missing"
   ```

3. **Build with latest configs:**
   ```bash
   ./build-and-push.sh
   ```

   This will:
   - Clone fresh copies of cc-master-agent-config and cc-example-agent-config
   - Build Docker image with the latest .claude configurations
   - Push to ghcr.io/plan-net/claude-hitl-worker:latest

4. **Validate build:**
   - Check build completed successfully
   - Verify image was pushed to ghcr.io
   - Confirm build configs cleaned up

5. **Ask about deployment:**
   If `$ARGUMENTS` contains "--deploy" or user wants to deploy immediately:
   ```bash
   just orb-deploy
   ```

6. **Report results to user:**
   - ✅ If sync and rebuild succeeded:
     ```
     Config sync and rebuild completed!

     Latest configs pulled from:
     - cc-master-agent-config ✓
     - cc-example-agent-config ✓

     Image rebuilt and pushed:
     - ghcr.io/plan-net/claude-hitl-worker:latest ✓

     [If deployed:]
     Deployed to Ray cluster ✓
     - Admin Panel: http://localhost:3370
     - Ray Dashboard: http://localhost:8265

     [If not deployed:]
     To deploy the updated image:
     - /cc-deploy (just deploy)
     - /cc-rebuild-deploy (rebuild + deploy)

     Note: Ray will use the new image when creating new actors.
     ```

   - ❌ If sync/rebuild failed:
     ```
     Config sync failed!

     Error: [show error from build]

     Common issues:
     - Missing .env or GITHUB_TOKEN
     - Cannot access config repos (check permissions)
     - Docker/Podman not running

     Troubleshooting:
     - Verify GitHub token has read access to both config repos
     - Ensure Docker/Podman is running
     - Check build script output for details
     ```

## Success Criteria

- Both config repos cloned successfully (fresh copies)
- Docker image built with latest configs
- Image pushed to ghcr.io/plan-net/claude-hitl-worker:latest
- Build artifacts cleaned up
- (Optional) Deployed to Ray cluster if requested

## Usage Examples

```bash
# Just sync and rebuild
/cc-sync-configs

# Sync, rebuild, and deploy
/cc-sync-configs --deploy
```

## Notes

Use this when configurations have been updated in the config repos.
The build script clones fresh copies, so you always get the latest changes.
Ray will automatically use the new image when creating new actors.
