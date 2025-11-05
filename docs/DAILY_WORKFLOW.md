# Daily Workflow

This guide describes the typical daily workflow when developing with the Claude + Kodosumi HITL template.

## Starting Your Day

```bash
just start
```

Wait ~10 seconds for all services to start. You'll see:
```
✓ Everything is running!
  Ray Dashboard: http://localhost:8265
  Admin Panel: http://localhost:3370
```

Access the admin panel: http://localhost:3370

## During Development

### Making Code Changes

1. **Edit code** on macOS using your IDE
2. All code lives in the same directory structure
3. Git workflow is unchanged

### Deploying Changes

**Option 1: Autonomous (Recommended)**
```bash
# In Claude Code
/cc-deploy
```

The deployment agent will:
- Detect what changed (code, configs, dependencies)
- Decide: rebuild image, redeploy, or restart
- Ask confirmation for risky operations
- Report deployment status

**Option 2: Manual**
```bash
# Redeploy to Ray cluster
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && koco deploy -r"
```

### Testing

Access the admin panel at http://localhost:3370 and start a conversation.

### Viewing Logs

All logs are in the VM at `/tmp/koco-*.log`

**View serve logs:**
```bash
orb -m ray-cluster bash -c "tail -f /tmp/koco-serve.log"
```

**View spool logs:**
```bash
orb -m ray-cluster bash -c "tail -f /tmp/koco-spool.log"
```

**View Ray logs:**
```bash
# Ray dashboard
open http://localhost:8265
```

### Debugging

**Check if services are running:**
```bash
# In VM
orb -m ray-cluster bash -c "ps aux | grep -E '(ray|koco)'"
```

**Check Ray status:**
```bash
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray status"
```

**Restart services without stopping VM:**
```bash
# Stop koco services
orb -m ray-cluster bash -c "pkill -f koco"

# Start them again
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && nohup koco spool > /tmp/koco-spool.log 2>&1 &"
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && nohup koco serve --register http://localhost:8001/-/routes > /tmp/koco-serve.log 2>&1 &"
```

## Ending Your Day

```bash
just stop
```

This will:
1. Stop koco services in VM
2. Stop Ray cluster in VM
3. Stop OrbStack VM

Everything is cleanly shut down and ready for tomorrow.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `just start` | Start everything (VM + Ray + Kodosumi) |
| `just stop` | Stop everything |
| `/cc-deploy` | Deploy changes (Claude Code) |

## Typical Daily Session

```bash
# Morning
cd ~/dev/cc-hitl-template
just start
# Wait for "Everything is running!" message
# Open http://localhost:3370 in browser

# During development
# Edit files in your IDE
/cc-deploy  # In Claude Code
# Test in browser at http://localhost:3370

# End of day
just stop
```

## Troubleshooting

### Services won't start

```bash
# Full reset
just stop
just start
```

### Can't access admin panel

Check if koco serve is running:
```bash
orb -m ray-cluster bash -c "ps aux | grep 'koco serve'"
```

Check logs:
```bash
orb -m ray-cluster bash -c "tail -50 /tmp/koco-serve.log"
```

### Ray not connecting

Check Ray status:
```bash
orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray status"
```

Check dashboard:
```bash
open http://localhost:8265
```

### VM issues

```bash
# Check VM status
orb list | grep ray-cluster

# Restart VM
orb stop ray-cluster
orb start ray-cluster
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

## Next Steps

- Read [SETUP.md](SETUP.md) for setup instructions
- Read [README.md](../README.md) for project overview
- Read [CLAUDE.md](../CLAUDE.md) for development guidelines
