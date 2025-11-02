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
