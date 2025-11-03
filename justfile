# Claude + Kodosumi HITL Template

# Build worker image (auto-detects docker/podman)
build-worker:
    @echo "Building Claude HITL worker image..."
    @if command -v docker &> /dev/null; then \
        docker build -t claude-hitl-worker:latest .; \
    elif command -v podman &> /dev/null; then \
        podman build -t claude-hitl-worker:latest .; \
    else \
        echo "Error: Neither docker nor podman found"; \
        exit 1; \
    fi

# Start full service stack (Ray + Kodosumi deployment + spooler + admin panel)
# For hybrid setup: This connects to Ray cluster in OrbStack via RAY_ADDRESS env var
start:
    source .venv/bin/activate && ray start --head --disable-usage-stats || echo "Ray already running or connecting to remote"
    @sleep 2
    source .venv/bin/activate && koco deploy -r
    @sleep 5
    source .venv/bin/activate && koco spool &
    @sleep 5
    source .venv/bin/activate && koco serve --register http://localhost:8001/-/routes

# Stop all services
stop:
    source .venv/bin/activate && ray stop
    @pkill -f koco || true

# Run basic tests
test:
    source .venv/bin/activate && pytest tests/ -v

# Show service status
status:
    @echo "Ray cluster status:"
    @source .venv/bin/activate && ray status || echo "Ray not running"
    @echo "\nKodosumi processes:"
    @ps aux | grep koco | grep -v grep || echo "No koco processes found"

# Clean up temporary files and caches
clean:
    rm -rf __pycache__
    rm -rf claude_hitl_template/__pycache__
    rm -rf .pytest_cache
    rm -rf *.egg-info
    find . -name "*.pyc" -delete

# ==============================================================================
# OrbStack VM Commands (macOS Hybrid Setup)
# ==============================================================================
# These commands manage the Ray cluster running in an OrbStack Linux VM.
# All commands run FROM macOS and control the VM via `orb shell`.
# See docs/DAILY_WORKFLOW.md for usage guide.

# Start Ray cluster in OrbStack VM
orb-start:
    @echo "Starting Ray cluster in OrbStack VM..."
    @orb shell ray-cluster "cd ~/cc-hitl-template && source .venv/bin/activate && ray start --head --disable-usage-stats --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265"
    @echo "✓ Ray cluster started"
    @echo "  Dashboard: http://localhost:8265"

# Stop Ray cluster in OrbStack VM
orb-stop:
    @echo "Stopping Ray cluster..."
    @-orb shell ray-cluster "ray stop" 2>/dev/null || echo "Ray not running"
    @echo "✓ Ray cluster stopped"

# Check OrbStack VM and Ray status
orb-status:
    @echo "=== OrbStack VM Status ==="
    @orb list | grep ray-cluster || echo "VM not running"
    @echo ""
    @echo "=== Ray Cluster Status ==="
    @orb shell ray-cluster "ray status" 2>/dev/null || echo "Ray not running"

# SSH into OrbStack VM
orb-shell:
    @echo "Connecting to OrbStack VM..."
    orb shell ray-cluster

# Deploy application to OrbStack VM
orb-deploy:
    @echo "Syncing code to VM..."
    @rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
        ./ ray-cluster.orb.local:~/cc-hitl-template/
    @echo "Deploying to Ray cluster..."
    @orb shell ray-cluster "cd ~/cc-hitl-template && source .venv/bin/activate && source .env && export ANTHROPIC_API_KEY && koco deploy -r"
    @echo "✓ Deployed"

# Start Kodosumi services in OrbStack VM (spooler + admin panel)
orb-services:
    @echo "Starting Kodosumi services in VM..."
    @orb shell ray-cluster "cd ~/cc-hitl-template && source .venv/bin/activate && source .env && export ANTHROPIC_API_KEY && nohup koco spool > /tmp/koco-spool.log 2>&1 & nohup koco serve --register http://localhost:8001/-/routes > /tmp/koco-serve.log 2>&1 &"
    @sleep 3
    @echo "✓ Services started"
    @echo "  Admin panel: http://localhost:3370"
    @echo "  Spooler logs: /tmp/koco-spool.log"
    @echo "  Server logs: /tmp/koco-serve.log"

# View Kodosumi logs from OrbStack VM
orb-logs:
    @echo "Showing Kodosumi logs (Ctrl+C to exit)..."
    @orb shell ray-cluster "tail -f /tmp/koco-*.log"

# Restart Ray cluster in OrbStack VM
orb-restart: orb-stop
    @sleep 2
    @just orb-start

# Complete daily startup: start Ray + deploy + start services
orb-up: orb-start
    @sleep 3
    @just orb-deploy
    @sleep 2
    @just orb-services
    @echo ""
    @echo "===================================="
    @echo "✓ Everything is running!"
    @echo "===================================="
    @echo "  Ray Dashboard: http://localhost:8265"
    @echo "  Admin Panel: http://localhost:3370"
    @echo ""

# Complete shutdown: stop services + stop Ray
orb-down: orb-stop
    @echo "✓ Everything stopped"
