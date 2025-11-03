# Daily Workflow Guide - OrbStack Hybrid Setup

Quick-start guide for daily development with the OrbStack Linux VM setup.

## Overview

This guide assumes you've completed the [OrbStack Setup](ORBSTACK_SETUP.md) and have:
- OrbStack VM named `ray-cluster` running Ubuntu 24.04
- Repository cloned at `~/cc-hitl-template` in the VM
- Python 3.12 virtual environment at `~/cc-hitl-template/.venv` in the VM
- All dependencies installed (Ray, Kodosumi, Claude SDK)

**Key Concept**: All commands run from your **macOS terminal** in the project directory. You never need to SSH into the VM manually.

## Morning Startup (One Command)

Start everything with a single command:

```bash
just orb-up
```

This command:
1. Starts Ray cluster in the VM
2. Syncs your latest code to the VM
3. Deploys the application to Ray
4. Starts Kodosumi spooler and admin panel

**Output**:
```
====================================
✓ Everything is running!
====================================
  Ray Dashboard: http://localhost:8265
  Admin Panel: http://localhost:3370
```

## Development Cycle

### 1. Edit Code (on macOS)

Edit files in your local project directory using your favorite editor:
- `claude_hitl_template/agent.py` - Claude SDK actor logic
- `claude_hitl_template/query.py` - Kodosumi endpoint logic
- `data/config/claude_hitl_template.yaml` - Configuration

### 2. Deploy Changes (from macOS)

After making changes, deploy them:

```bash
just orb-deploy
```

This syncs your code to the VM and redeploys to Ray.

### 3. Test (via Browser)

- **Admin Panel**: http://localhost:3370
  - Submit prompts via the form
  - Monitor execution progress
  - View HITL lock interactions

- **Ray Dashboard**: http://localhost:8265
  - Monitor cluster resources
  - View actor instances
  - Check logs and metrics

### 4. View Logs (if needed)

Stream Kodosumi logs:

```bash
just orb-logs
```

Press `Ctrl+C` to exit.

### 5. Repeat

Edit → Deploy → Test → Repeat

## Evening Shutdown

Stop everything:

```bash
just orb-down
```

This stops the Ray cluster and all services in the VM.

## Quick Reference - Common Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `just orb-up` | Start everything | Every morning / after reboot |
| `just orb-deploy` | Sync code and redeploy | After editing code |
| `just orb-down` | Stop everything | End of day / before reboot |
| `just orb-logs` | View service logs | Debugging issues |
| `just orb-status` | Check VM and Ray status | Verify everything is running |
| `just orb-restart` | Restart Ray cluster | After cluster issues |
| `just orb-shell` | SSH into VM | Advanced debugging |

## Typical Daily Session

```bash
# Morning
cd ~/dev/cc-hitl-template
just orb-up
# Wait for "Everything is running!" message
# Open http://localhost:3370 in browser

# During development
# Edit files in VSCode/your editor
just orb-deploy
# Test in browser at http://localhost:3370

# End of day
just orb-down
```

## Quick Troubleshooting

### "Ray cluster failed to start"

**Check VM status**:
```bash
just orb-status
```

**Restart Ray**:
```bash
just orb-restart
```

### "Admin panel not responding"

**Restart services**:
```bash
just orb-services
```

### "Code changes not visible"

**Redeploy**:
```bash
just orb-deploy
```

### "Can't access dashboard/admin panel"

**Check OrbStack is running**:
```bash
orb list
```

If `ray-cluster` VM is not running, start OrbStack and run:
```bash
just orb-up
```

### "Need to debug inside VM"

**SSH into VM**:
```bash
just orb-shell
# Inside VM:
cd ~/cc-hitl-template
source .venv/bin/activate
ray status
# Exit with: exit
```

## Dashboard URLs

Always accessible from macOS browser when services are running:

- **Ray Dashboard**: http://localhost:8265
  - Cluster overview
  - Actor instances
  - Resource usage
  - Logs and metrics

- **Kodosumi Admin Panel**: http://localhost:3370
  - Submit prompts
  - Monitor executions
  - Manage HITL locks
  - View conversation history

## Environment Variables

Your `.env` file on macOS is automatically synced to the VM during `just orb-deploy`.

**Important**: If you update `.env`, you must redeploy:

```bash
# After editing .env
just orb-deploy
```

## Advanced Scenarios

### Deploy Without Starting Services

```bash
just orb-start   # Start Ray only
just orb-deploy  # Deploy code
# Services stay stopped
```

### Start Services Separately

```bash
just orb-services  # Start spooler + admin panel
```

### Restart Ray Without Full Shutdown

```bash
just orb-restart  # Stop + Start Ray
# Services will need to be restarted
just orb-services
```

## What NOT to Do

❌ Don't SSH into the VM and run commands manually
✅ Use `just orb-*` commands from macOS

❌ Don't edit code inside the VM
✅ Edit on macOS and deploy with `just orb-deploy`

❌ Don't manually sync files with `rsync`
✅ Use `just orb-deploy` which handles sync correctly

❌ Don't run `ray start` directly
✅ Use `just orb-start` or `just orb-up`

## Tips

1. **Keep the VM running**: OrbStack uses <0.1% CPU when idle. No need to shut down between sessions unless rebooting your Mac.

2. **Fast iteration**: Use `just orb-deploy` frequently during development. It's fast (only syncs changed files).

3. **Monitor with dashboards**: Keep Ray Dashboard and Admin Panel open in browser tabs during development.

4. **Check logs first**: When debugging, run `just orb-logs` before diving into VM.

5. **Clean restart**: If something seems broken, try `just orb-restart` before investigating deeper.

## Next Steps

- Read [OrbStack Setup Guide](ORBSTACK_SETUP.md) for architecture details
- Read [README.md](../README.md) for project overview
- Read [CLAUDE.md](../CLAUDE.md) for development guidelines
