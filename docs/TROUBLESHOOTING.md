# Troubleshooting Guide

Comprehensive troubleshooting guide for the Claude + Kodosumi HITL Template.

**Quick Links:**
- [Container Runtime Issues](#container-runtime-issues)
- [Ray Cluster Issues](#ray-cluster-issues)
- [Service Issues](#service-issues)
- [Build Issues](#build-issues)
- [Network Issues](#network-issues)

---

## Container Runtime Issues

### Installing Podman in OrbStack VM

**When needed:** macOS users running Ray cluster in OrbStack VM with containerized actors.

**Podman vs Docker choice:**
- **Docker**: Simpler, works out of the box for most cases
- **Podman**: Daemonless, rootless by default, better security model
- Both work for this template

**Installation steps:**

```bash
# SSH into VM
orb -m ray-cluster bash

# Update package lists
sudo apt-get update

# Install podman
sudo apt-get install -y podman

# Verify installation
podman --version
# Should show: podman version 4.9.3 or higher
```

**After installation:** You must configure user namespaces (see next section).

---

### User Namespace Configuration for Rootless Podman

**Symptom:**
```
Error: potentially insufficient UIDs or GIDs available in user namespace
(requested 0:42 for /etc/gshadow): Check /etc/subuid and /etc/subgid
if configured locally and run "podman system migrate"
```

**Root cause:**
- Rootless podman requires subordinate UID/GID ranges to map container users to host users
- Container runs as `ray` user (UID 1000) inside
- Host user is `sebkuepers` (UID 501)
- Without mapping, podman can't create containers with different UIDs

**Fix:**

```bash
# SSH into VM
orb -m ray-cluster bash

# Configure subordinate UIDs and GIDs
# Format: username:start_uid:count
sudo bash -c 'echo "sebkuepers:100000:65536" >> /etc/subuid'
sudo bash -c 'echo "sebkuepers:100000:65536" >> /etc/subgid'

# Apply configuration
podman system migrate

# Verify configuration
cat /etc/subuid
# Should show: sebkuepers:100000:65536

cat /etc/subgid
# Should show: sebkuepers:100000:65536
```

**Test the fix:**

```bash
# Create test directory
mkdir -p /tmp/test

# Run test container
podman run --rm -v /tmp/test:/shared:Z \
  ghcr.io/plan-net/claude-hitl-worker@sha256:<digest> \
  echo 'test successful'

# Should output: test successful
```

**Explanation:**
- `sebkuepers:100000:65536` provides UIDs 100000-165535 for user namespace mapping
- Must configure both `/etc/subuid` AND `/etc/subgid`
- `podman system migrate` regenerates podman's user namespace configuration
- After this, podman can map container UID 1000 to host subordinate UID range

---

### Permission Issues: /tmp/ray File Locking

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/tmp/ray/session_*/ports_by_node.json.lock'
```

Ray actors stuck in `PENDING_CREATION` state.

**Root cause:**
- Ray HEAD node runs as host user (UID 501 - `sebkuepers`)
- Ray WORKER actors run in containers as `ray` user (UID 1000)
- Both need to access shared files in `/tmp/ray`
- File locks created with 644 permissions by HEAD node
- Rootless podman's user namespace mapping prevents cross-UID file locking
- Even 777 permissions don't work without correct ownership

**Fix (Permanent - already implemented in justfile):**

The `justfile` automatically fixes permissions on every startup:

```just
start:
    @echo "Starting ray-cluster VM..."
    @orb start ray-cluster
    @sleep 2
    @echo "Starting Ray cluster in VM..."
    @orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray start --head ..."
    @sleep 2
    @echo "Fixing /tmp/ray permissions for containers..."
    @orb -m ray-cluster bash -c "sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"
    @echo "Deploying application..."
    # ... continues
```

**What this does:**
1. Changes ownership to UID 1000 (container `ray` user)
2. Sets 777 permissions for all files/directories
3. Runs after Ray starts but before deployment
4. Ensures containers can access Ray's internal files

**Manual fix (if needed):**
```bash
# In VM
orb -m ray-cluster bash

# Fix permissions
sudo chown -R 1000:1000 /tmp/ray
sudo chmod -R 777 /tmp/ray

# Verify
ls -la /tmp/ray/session_*/ports_by_node.json.lock
# Should show: -rwxrwxrwx 1 1000 1000 ...
```

**Why this works:**
- UID 1000 is the `ray` user inside containers
- Ownership by container user allows file locking to work
- 777 permissions ensure all processes can read/write
- Must be done after each Ray restart (hence justfile automation)

---

### Debug Directory Permission Issues

**Symptom:**
```
Error: EACCES: permission denied, open '/app/template_user/.claude/debug/f44d0a7e-8e1d-402e-b9ef-99185354c7ec.txt'
```

Ray actor starts but immediately dies when Claude SDK tries to write debug logs.

**Root cause:**
- Claude SDK writes debug logs to `.claude/debug/` directory
- Directory didn't exist in container image
- Container runs as `ray` user (UID 1000)
- Can't create directories in read-only filesystem

**Fix (Permanent - already implemented in Dockerfile):**

The `Dockerfile` creates debug directories with correct ownership:

```dockerfile
# Create debug directories for Claude SDK logging
# Claude SDK writes debug logs to .claude/debug/ which must be writable
RUN mkdir -p /app/template_user/.claude/debug /app/.claude/debug

# Fix ownership of all config directories for ray user
# This prevents permission errors when Claude CLI or SDK tries to access configs
RUN chown -R ray:users /app/template_user/.claude /app/.claude /app/plugins /app/claude_hitl_template
```

**If rebuilding image:**
1. Make changes to code or configs
2. Rebuild image: `bash .claude/skills/docker-build/scripts/build.sh` or use `/cc-deploy`
3. Image will include debug directories automatically

**Verification:**
```bash
# After actor starts, check container
orb -m ray-cluster bash -c "podman exec -it <container_id> ls -la /app/template_user/.claude/debug"
# Should show directory owned by ray:users
```

---

### Container Image Digests: Local vs Registry

**Symptom:**
- Built image locally with one digest
- Pushed to ghcr.io
- Configs reference wrong digest
- Ray can't find image: "image not found" errors

**Root cause:**
Container image digests differ between local builds and registry storage.

**Understanding digests:**

```bash
# After local build
podman images --format json | jq '.[] | select(.RepoTags[0] | contains("claude-hitl-worker"))'
# Shows TWO digest fields:
# - .Digest: sha256:90ecaabb... (local build digest)
# - .RepoDigests[0]: "" (empty until pushed)

# After push to ghcr.io
podman images --format json | jq '.[] | select(.RepoTags[0] | contains("claude-hitl-worker"))'
# Shows:
# - .Digest: sha256:90ecaabb... (unchanged local digest)
# - .RepoDigests[0]: "ghcr.io/plan-net/claude-hitl-worker@sha256:5a0eb9323..." (registry assigned digest)
```

**Key insight:**
- Local `.Digest` is what `podman build` calculates
- Registry `.RepoDigests[0]` is what the registry assigns after push
- They are DIFFERENT because registry repackages the image
- **Always use `.RepoDigests` from registry** for deployment configs

**Fix:**

```bash
# After pushing to registry
podman images --format json | jq -r '.[] | select(.RepoTags[0] | contains("claude-hitl-worker")) | .RepoDigests[0]'
# Output: ghcr.io/plan-net/claude-hitl-worker@sha256:3ca151211ed...

# Use this digest in configs
```

**Update both config files:**

1. `.env`:
```bash
CONTAINER_IMAGE_URI=ghcr.io/plan-net/claude-hitl-worker@sha256:3ca151211ed...
```

2. `data/config/claude_hitl_template.yaml`:
```yaml
runtime_env:
  env_vars:
    CONTAINER_IMAGE_URI: "ghcr.io/plan-net/claude-hitl-worker@sha256:3ca151211ed..."
```

**Sync to VM:**
```bash
rsync -av .env ray-cluster@orb:~/dev/cc-hitl-template/
rsync -av data/config/claude_hitl_template.yaml ray-cluster@orb:~/dev/cc-hitl-template/data/config/
```

**The `/cc-deploy` command handles this automatically.**

---

## Ray Cluster Issues

### Ray Connection Refused

**Symptom:**
```
ConnectionError: ray://localhost:10001 connection refused
```

**Fix:**
```bash
# Check if Ray is running in VM
orb -m ray-cluster bash -c "ray status"

# If not running, start it
just start

# Or manually
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray start --head --disable-usage-stats --port=6379"
```

---

### Port Already in Use

**Symptom:**
```
OSError: [Errno 48] Address already in use
```

**Fix:**
```bash
# On macOS - find what's using the port
lsof -i :10001
lsof -i :8265
lsof -i :3370

# Stop all services and restart
just stop
just start
```

**For specific port conflicts:**
```bash
# Find process
lsof -i :<port>

# Kill process
kill -9 <PID>
```

---

### Ray Actors Stuck in PENDING_CREATION

**Symptom:**
Ray dashboard shows actors in `PENDING_CREATION` state for >30 seconds.

**Common causes and fixes:**

**1. Permission issues** (most common)
```bash
# Check if permission fix ran
orb -m ray-cluster bash -c "ls -la /tmp/ray/session_*/ports_by_node.json.lock | head -5"
# Should show: -rwxrwxrwx 1 1000 1000

# If not, run manually
orb -m ray-cluster bash -c "sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"
```

**2. Container image not found**
```bash
# Check image exists in VM
orb -m ray-cluster bash -c "podman images | grep claude-hitl-worker"

# If missing, pull or rebuild
orb -m ray-cluster bash -c "podman pull ghcr.io/plan-net/claude-hitl-worker@sha256:<digest>"
```

**3. Runtime environment setup failure**
```bash
# Check Ray runtime env logs
orb -m ray-cluster bash -c "cat /tmp/ray/session_*/logs/runtime_env_setup*.log"

# Common issues:
# - Podman not installed → see "Installing Podman" section
# - User namespace not configured → see "User Namespace Configuration" section
# - Wrong image digest → see "Container Image Digests" section
```

**4. Resource constraints**
```bash
# Check available resources
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray status"

# If no CPUs available, stop old actors
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray list actors"
# Kill old actors if needed
```

---

## Service Issues

### ANTHROPIC_API_KEY Not Found

**Symptom:**
```
Error: ANTHROPIC_API_KEY environment variable not set
```

**Fix:**

**1. Check .env file:**
```bash
cat .env | grep ANTHROPIC_API_KEY
# Should show: ANTHROPIC_API_KEY=sk-ant-...
```

**2. Check YAML config:**
```bash
cat data/config/claude_hitl_template.yaml | grep ANTHROPIC_API_KEY
# Should show literal key: ANTHROPIC_API_KEY: "sk-ant-..."
```

**3. Sync to VM:**
```bash
rsync -av .env ray-cluster@orb:~/dev/cc-hitl-template/
rsync -av data/config/claude_hitl_template.yaml ray-cluster@orb:~/dev/cc-hitl-template/data/config/
```

**4. Restart services:**
```bash
just stop
just start
```

**Important:** Ray Serve YAML does NOT support variable substitution. The key must be a literal string, not `"${ANTHROPIC_API_KEY}"`.

---

### Services Won't Start

**Symptom:**
`just start` fails or services don't respond.

**Systematic diagnosis:**

```bash
# 1. Check VM is running
orb list | grep ray-cluster
# Should show ray-cluster as running

# 2. Check Ray cluster
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray status"
# Should show node as Active

# 3. Check Ray Serve deployment
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && RAY_ADDRESS=http://localhost:8265 serve status"
# Should show claude_hitl_template: RUNNING

# 4. Check Kodosumi services
orb -m ray-cluster bash -c "ps aux | grep koco"
# Should show koco spool and koco serve processes

# 5. Check logs
orb -m ray-cluster bash -c "tail -50 /tmp/koco-serve.log"
orb -m ray-cluster bash -c "tail -50 /tmp/koco-spool.log"
```

**Clean restart:**
```bash
just stop
# Wait 5 seconds
just start
```

**Nuclear option:**
```bash
just stop
orb stop ray-cluster
orb start ray-cluster
just start
```

---

### Code Changes Not Reflected

**Symptom:**
You changed code on macOS but Ray actors still use old code.

**Root cause:**
When using `image_uri` in Ray runtime environment, code must be baked into the container image.

**Fix:**

**Option 1: Use /cc-deploy command (recommended)**
```bash
# In Claude Code
/cc-deploy

# This will:
# - Detect changes in code or configs
# - Rebuild container image if needed
# - Push to registry
# - Update configs with new digest
# - Redeploy to Ray
# - Verify actors are using new image
```

**Option 2: Manual rebuild and deploy**
```bash
# 1. Rebuild container image
bash .claude/skills/docker-build/scripts/build.sh

# 2. Get new digest
NEW_DIGEST=$(podman images --format json | jq -r '.[] | select(.RepoTags[0] | contains("claude-hitl-worker")) | .RepoDigests[0]')

# 3. Update .env
echo "CONTAINER_IMAGE_URI=$NEW_DIGEST" >> .env

# 4. Update data/config/claude_hitl_template.yaml
# (Edit manually to update CONTAINER_IMAGE_URI value)

# 5. Sync to VM
rsync -av .env ray-cluster@orb:~/dev/cc-hitl-template/
rsync -av data/config/claude_hitl_template.yaml ray-cluster@orb:~/dev/cc-hitl-template/data/config/

# 6. Redeploy
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && koco deploy -r"
```

---

## Build Issues

### Docker/Podman Build Fails

**Symptom:**
`bash .claude/skills/docker-build/scripts/build.sh` fails.

**Common causes:**

**1. GITHUB_TOKEN not set or invalid**
```bash
# Check token in .env
cat .env | grep GITHUB_TOKEN
# Should show: GITHUB_TOKEN=ghp_...

# Test token
curl -H "Authorization: token $(grep GITHUB_TOKEN .env | cut -d= -f2)" https://api.github.com/user
# Should return user info, not 401 Unauthorized
```

**2. Git authentication issues**
```bash
# Check SSH keys for git@ URLs
ssh -T git@github.com
# Should show: Hi <username>! You've successfully authenticated

# Or use HTTPS with token
git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
```

**3. Config repositories not accessible**
```bash
# Test master config repo
git ls-remote $(grep MASTER_CONFIG_REPO .env | cut -d= -f2)

# Test project config repo
git ls-remote $(grep PROJECT_CONFIG_REPO .env | cut -d= -f2)

# Should show refs, not permission errors
```

**4. Podman/Docker not running**
```bash
# macOS - check podman machine
podman machine list
# Should show machine running

# Or check Docker Desktop
docker ps
# Should connect without errors

# In VM
orb -m ray-cluster bash -c "podman ps"
# Should show running containers or empty list (not errors)
```

---

### Push to Registry Fails

**Symptom:**
`podman push` or `docker push` fails with authentication errors.

**Fix:**

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | podman login ghcr.io -u plan-net --password-stdin

# Or for Docker
echo $GITHUB_TOKEN | docker login ghcr.io -u plan-net --password-stdin

# Verify login
podman login ghcr.io --get-login
# Should show: plan-net

# Retry push
podman push ghcr.io/plan-net/claude-hitl-worker:latest
```

---

## Network Issues

### Can't Reach Ray Dashboard

**Symptom:**
`http://localhost:8265` times out or connection refused.

**Fix:**

```bash
# 1. Check Ray is running
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray status"

# 2. Check dashboard port forwarding (OrbStack does this automatically)
curl http://localhost:8265
# Should return HTML, not connection refused

# 3. Check firewall (macOS)
# System Settings → Network → Firewall → allow incoming connections

# 4. Check Ray started with dashboard
orb -m ray-cluster bash -c "ps aux | grep dashboard"
# Should show ray dashboard process

# 5. Restart Ray with explicit dashboard host
just stop
just start
```

---

### Admin Panel Not Accessible

**Symptom:**
`http://localhost:3370` not responding.

**Fix:**

```bash
# 1. Check Kodosumi services running
orb -m ray-cluster bash -c "ps aux | grep 'koco serve'"
# Should show koco serve process

# 2. Check logs
orb -m ray-cluster bash -c "tail -50 /tmp/koco-serve.log"
# Look for errors or port conflicts

# 3. Check port forwarding
lsof -i :3370
# Should show connection to VM

# 4. Restart Kodosumi services
just stop
just start
```

---

### SSH/rsync Errors to OrbStack VM

**Symptom:**
`rsync` or `orb ssh` fails with connection errors.

**Fix:**

**1. Use correct hostname format:**
```bash
# ✓ Correct
rsync -av file.txt ray-cluster@orb:~/

# ✗ Wrong
rsync -av file.txt ray-cluster.orb.local:~/
```

**2. Check VM is running:**
```bash
orb list | grep ray-cluster
# Should show running state

# If stopped
orb start ray-cluster
```

**3. Test SSH connection:**
```bash
orb -m ray-cluster bash -c "echo test"
# Should output: test

# If fails, check OrbStack
orb version
# Should show OrbStack version
```

---

## Quick Command Reference

**Check system status:**
```bash
just start                    # Start everything
just stop                     # Stop everything
orb list                      # List VMs
ray status                    # Check Ray cluster (in VM)
serve status                  # Check Ray Serve (in VM)
ray list actors               # List all actors (in VM)
```

**View logs:**
```bash
orb -m ray-cluster bash -c "tail -f /tmp/koco-serve.log"
orb -m ray-cluster bash -c "tail -f /tmp/koco-spool.log"
orb -m ray-cluster bash -c "tail -f /tmp/ray/session_latest/logs/raylet.out"
```

**Permissions:**
```bash
# Fix /tmp/ray permissions
orb -m ray-cluster bash -c "sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"

# Check lock file ownership
orb -m ray-cluster bash -c "ls -la /tmp/ray/session_*/ports_by_node.json.lock"
```

**Container debugging:**
```bash
# List containers
orb -m ray-cluster bash -c "podman ps -a"

# Inspect container
orb -m ray-cluster bash -c "podman inspect <container_id>"

# View container logs
orb -m ray-cluster bash -c "podman logs <container_id>"

# Exec into container
orb -m ray-cluster bash -c "podman exec -it <container_id> bash"
```

---

## When All Else Fails

**Complete reset:**

```bash
# 1. Stop everything
just stop

# 2. Stop VM
orb stop ray-cluster

# 3. Clean Ray state
orb -m ray-cluster bash -c "rm -rf /tmp/ray/*"

# 4. Restart from scratch
orb start ray-cluster
just start
```

**Still broken?**
- Check `.env` file has all required values
- Check `data/config/claude_hitl_template.yaml` has literal env vars
- Check container image exists in VM: `orb -m ray-cluster bash -c "podman images"`
- Check GitHub token is valid
- Check config repositories are accessible
- Review this guide's "Container Runtime Issues" section

**Get help:**
- Review main `CLAUDE.md` documentation
- Check `docs/SETUP.md` for setup instructions
- See `docs/ORBSTACK_SETUP.md` for VM configuration
- Open an issue in the template repository
