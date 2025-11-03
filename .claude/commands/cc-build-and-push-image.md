---
description: Build Docker image with baked .claude configs and push to ghcr.io
allowed-tools: [Bash]
---

Build the Docker image with baked-in .claude configurations from both config repos and push to GitHub Container Registry.

## Your Task

1. **Pre-flight checks:**
   - Verify .env file exists:
     ```bash
     [ -f .env ] && echo ".env exists" || echo "ERROR: .env not found"
     ```

   - Load environment variables and verify required vars:
     ```bash
     source .env
     [ -n "$GITHUB_TOKEN" ] && echo "GITHUB_TOKEN set" || echo "ERROR: GITHUB_TOKEN missing"
     [ -n "$GITHUB_USERNAME" ] && echo "GITHUB_USERNAME set" || echo "ERROR: GITHUB_USERNAME missing"
     [ -n "$ANTHROPIC_API_KEY" ] && echo "ANTHROPIC_API_KEY set" || echo "ERROR: ANTHROPIC_API_KEY missing"
     ```

2. **Execute build and push:**
   ```bash
   ./build-and-push.sh
   ```

3. **Monitor build process:**
   - Watch for successful git clone of config repos
   - Check for successful Docker/Podman build
   - Verify image push to ghcr.io
   - Note the final image name

4. **Validate build succeeded:**
   - Check if image exists (if using Podman locally):
     ```bash
     podman images | grep claude-hitl-worker || docker images | grep claude-hitl-worker
     ```
     Expected: Should show image with "latest" tag

5. **Report results to user:**
   - ✅ If build succeeded:
     ```
     Docker image built and pushed successfully!

     Image: ghcr.io/plan-net/claude-hitl-worker:latest

     Config repos included:
     - cc-master-agent-config (.claude → /app/template_user/.claude)
     - cc-example-agent-config (.claude → /app/project/.claude)

     Next steps:
     - Deploy to Ray: /cc-deploy
     - Or full rebuild + deploy: /cc-rebuild-deploy
     ```

   - ❌ If build failed:
     ```
     Docker image build failed!

     Error: [show error from build]

     Common issues:
     - Missing .env file
     - Invalid GITHUB_TOKEN (needs packages:write scope)
     - Git clone failed (check repo access)
     - Docker/Podman not running

     Troubleshooting:
     - Verify .env has all required variables
     - Check GitHub token permissions
     - Ensure Docker/Podman is running
     ```

## Success Criteria

- .env file exists with all required variables
- Config repos cloned successfully
- Docker/Podman build completes without errors
- Image pushed to ghcr.io/plan-net/claude-hitl-worker:latest
- Build configs cleaned up

## Notes

This command runs on your macOS machine (not in OrbStack VM).
The built image will be pulled by Ray when creating new actors.
