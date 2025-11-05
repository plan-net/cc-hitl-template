# Claude + Kodosumi HITL Template
# Simplified VM-only setup - Everything runs in OrbStack VM

# Start all services in OrbStack VM
start:
	@echo "Starting ray-cluster VM..."
	@orb start ray-cluster
	@sleep 2
	@echo "Starting Ray cluster in VM..."
	@orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray start --head --disable-usage-stats --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265"
	@sleep 2
	@echo "Fixing /tmp/ray permissions for containers..."
	@orb -m ray-cluster bash -c "sudo chown -R 1000:1000 /tmp/ray && sudo chmod -R 777 /tmp/ray"
	@echo "Deploying application..."
	@orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && koco deploy -r"
	@sleep 2
	@echo "Starting Kodosumi services..."
	@orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && nohup koco spool > /tmp/koco-spool.log 2>&1 &"
	@orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && source .env && nohup koco serve --register http://localhost:8001/-/routes > /tmp/koco-serve.log 2>&1 &"
	@sleep 3
	@echo ""
	@echo "===================================="
	@echo "✓ Everything is running!"
	@echo "===================================="
	@echo "  Ray Dashboard: http://localhost:8265"
	@echo "  Admin Panel: http://localhost:3370"
	@echo ""
	@echo "Logs are in the VM at /tmp/koco-*.log"
	@echo "To view: orb -m ray-cluster bash -c \"tail -f /tmp/koco-serve.log\""
	@echo ""

# Stop all services and VM
stop:
	@echo "Stopping Kodosumi services..."
	@-orb -m ray-cluster bash -c "pkill -f koco" 2>/dev/null || true
	@echo "Stopping Ray cluster..."
	@-orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && ray stop" 2>/dev/null || true
	@echo "Stopping ray-cluster VM..."
	@orb stop ray-cluster
	@echo "✓ Everything stopped"
