# Sharing Your Working OrbStack Setup with Coworkers

This guide helps you share your exact working OrbStack environment configuration with coworkers who are having trouble getting the repository to work.

## Quick Start (Recommended)

### For You (Working Environment)

**1. Export your working configuration:**
```bash
bash scripts/export-vm-config.sh > vm-config-working.txt
```

**2. Share these files with your coworker:**
- `vm-config-working.txt` - Your working VM configuration
- `scripts/setup-coworker-vm.sh` - Automated setup script
- `scripts/export-vm-config.sh` - For them to export their config
- `scripts/compare-vm-configs.sh` - To compare differences
- `.env.template` - Environment variables (create it):
  ```bash
  cat .env | grep -v "ANTHROPIC_API_KEY\|GITHUB_TOKEN" > .env.template
  ```

**3. Send via your preferred method:**
- Email attachments
- Shared Google Drive / Dropbox
- Company wiki / Confluence
- Slack / Teams

### For Your Coworker (Broken Environment)

**Option A: Automated Setup (Easiest)**

1. Get the files from your coworker
2. Run the automated setup:
   ```bash
   bash scripts/setup-coworker-vm.sh
   ```
3. Follow the prompts
4. Export your config for comparison:
   ```bash
   bash scripts/export-vm-config.sh > vm-config-mine.txt
   ```
5. Compare configurations:
   ```bash
   bash scripts/compare-vm-configs.sh vm-config-working.txt vm-config-mine.txt
   ```

**Option B: Manual Setup (More Control)**

1. Follow the setup guide: `docs/ORBSTACK_SETUP.md`
2. Use `vm-config-working.txt` as reference for exact versions
3. Export your config: `bash scripts/export-vm-config.sh > vm-config-mine.txt`
4. Compare: `bash scripts/compare-vm-configs.sh vm-config-working.txt vm-config-mine.txt`
5. Fix any differences identified

## What Gets Shared

The export includes:
- ✅ Ubuntu version and architecture
- ✅ Python version
- ✅ Container runtime (Docker/Podman) and version
- ✅ Podman user namespace configuration
- ✅ Installed Python packages and versions
- ✅ Directory structure
- ✅ Ray version

The export excludes:
- ❌ API keys (ANTHROPIC_API_KEY)
- ❌ Tokens (GITHUB_TOKEN)
- ❌ Your actual code
- ❌ Personal data

## Common Differences to Check

### 1. Architecture Mismatch
**Problem**: You have Apple Silicon (arm64), coworker has Intel Mac (x86_64)

**Solution**:
- Container images must be rebuilt on their architecture
- OrbStack will automatically create VMs with correct architecture
- Run `/cc-deploy` on their machine to rebuild

### 2. Container Runtime Mismatch
**Problem**: One uses Docker, other uses Podman

**Solution**:
- Both can work, but Podman requires user namespace configuration
- If switching to Podman:
  ```bash
  orb -m ray-cluster bash
  sudo bash -c 'echo $(whoami):100000:65536 >> /etc/subuid'
  sudo bash -c 'echo $(whoami):100000:65536 >> /etc/subgid'
  podman system migrate
  ```

### 3. Python Version Mismatch
**Problem**: Different Python versions (e.g., 3.11 vs 3.12)

**Solution**:
- Install Python 3.12+ in VM:
  ```bash
  orb -m ray-cluster bash
  sudo apt-get install -y python3.12 python3.12-venv
  python3.12 -m venv ~/.venv
  source ~/.venv/bin/activate
  pip install -e .
  ```

### 4. Missing Dependencies
**Problem**: Some Python packages not installed or wrong versions

**Solution**:
- Compare `pip list` output from both exports
- Reinstall in VM:
  ```bash
  orb -m ray-cluster bash
  source ~/.venv/bin/activate
  cd ~/dev/cc-hitl-template
  pip install -e .
  ```

### 5. Ray /tmp/ray Permissions
**Problem**: Container can't write to /tmp/ray

**Solution**:
```bash
orb -m ray-cluster bash -c "sudo mkdir -p /tmp/ray && sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"
```

## Verification Checklist

After setup, your coworker should verify:

```bash
# 1. VM is running
orb list | grep ray-cluster

# 2. Python version matches
orb -m ray-cluster bash -c "python3 --version"

# 3. Container runtime works
orb -m ray-cluster bash -c "docker ps"  # or podman ps

# 4. Ray is installed
orb -m ray-cluster bash -c "source ~/.venv/bin/activate && ray --version"

# 5. User namespaces configured (Podman only)
orb -m ray-cluster bash -c "cat /etc/subuid /etc/subgid | grep \$(whoami)"

# 6. /tmp/ray exists with correct permissions
orb -m ray-cluster bash -c "ls -la /tmp/ray"

# 7. Can start Ray cluster
just start  # or: just orb-up

# 8. Dashboard accessible
curl http://localhost:8265
```

## Troubleshooting

If issues persist after matching configurations:

### Step 1: Clean Slate
```bash
# Stop everything
just stop

# Delete and recreate VM
orb stop ray-cluster
orb delete ray-cluster

# Run automated setup
bash scripts/setup-coworker-vm.sh
```

### Step 2: Line-by-Line Comparison
```bash
# Export both configs
bash scripts/export-vm-config.sh > config-A.txt  # Working
bash scripts/export-vm-config.sh > config-B.txt  # Broken

# Compare
bash scripts/compare-vm-configs.sh config-A.txt config-B.txt
```

### Step 3: Check Logs
```bash
# Ray logs
orb -m ray-cluster bash -c "tail -100 /tmp/ray/session_latest/logs/raylet.out"

# Kodosumi logs
orb -m ray-cluster bash -c "tail -100 /tmp/koco-serve.log"

# Actor logs
orb -m ray-cluster bash -c "tail -100 /tmp/ray/session_latest/logs/worker-*.out"
```

### Step 4: Network Debugging
```bash
# Check ports are listening
orb -m ray-cluster bash -c "netstat -tlnp | grep -E '6379|8265|8001|3370'"

# Test from macOS
curl http://localhost:8265  # Ray dashboard
curl http://localhost:8001  # Kodosumi spooler
curl http://localhost:3370  # Admin panel
```

## Advanced: Snapshot Sharing (Future)

OrbStack doesn't currently support VM export/import, but you can:

1. **Share Dockerfile + build script**
   - Already in repository
   - Ensures identical container images

2. **Share justfile commands**
   - Already in repository
   - Standardizes VM operations

3. **Use /cc-setup command**
   - Automated setup via Claude Code
   - Detects OS and guides through setup
   ```bash
   claude code
   /cc-setup
   ```

## Support Resources

- **Setup documentation**: `docs/ORBSTACK_SETUP.md`
- **Troubleshooting guide**: `docs/TROUBLESHOOTING.md`
- **Daily workflow**: `docs/DAILY_WORKFLOW.md`
- **Architecture details**: `CLAUDE.md`

## Quick Reference: Your Working Configuration

Your exported configuration shows:
- **OS**: Ubuntu 24.04.3 LTS (Noble)
- **Architecture**: arm64 (Apple Silicon)
- **Python**: 3.12.3
- **Container Runtime**: Podman 4.9.3
- **Ray**: 2.51.1
- **User Namespaces**: sebkuepers:100000:65536

Your coworker should match these versions as closely as possible.

---

**Questions?** Open an issue or check the troubleshooting guide.
