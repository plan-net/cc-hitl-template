# Claude + Kodosumi HITL Template

# Start full service stack (Ray + Kodosumi deployment + spooler + admin panel)
start:
    source .venv/bin/activate && ray start --head --disable-usage-stats
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
