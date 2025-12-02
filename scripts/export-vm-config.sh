#!/bin/bash
# Export OrbStack VM configuration for sharing with coworkers
# Usage: bash scripts/export-vm-config.sh > vm-config-export.txt

set -e

echo "==================================="
echo "OrbStack VM Configuration Export"
echo "Generated: $(date)"
echo "==================================="
echo ""

echo "--- OrbStack VM Info ---"
orb list --format json | jq '.'
echo ""

echo "--- Running in VM ---"
orb -m ray-cluster bash << 'EOF'
echo "=== OS Information ==="
cat /etc/os-release
echo ""

echo "=== Architecture ==="
uname -m
echo ""

echo "=== Python Version ==="
python3 --version
which python3
echo ""

echo "=== Virtual Environment ==="
if [ -d ~/.venv ]; then
    echo "venv location: ~/.venv"
    source ~/.venv/bin/activate
    echo "Python in venv: $(which python)"
    echo "Pip in venv: $(which pip)"
    echo ""
    echo "=== Installed Python Packages ==="
    pip list
else
    echo "No venv found at ~/.venv"
fi
echo ""

echo "=== Container Runtime ==="
if command -v docker &> /dev/null; then
    echo "Container runtime: Docker"
    docker --version
    docker info 2>/dev/null | grep -A 10 "Server Version"
elif command -v podman &> /dev/null; then
    echo "Container runtime: Podman"
    podman --version
    echo ""
    echo "Podman system info:"
    podman system info | grep -A 20 "security"
else
    echo "No container runtime found"
fi
echo ""

echo "=== User Namespace Configuration (Podman) ==="
if [ -f /etc/subuid ]; then
    echo "/etc/subuid:"
    cat /etc/subuid | grep $(whoami) || echo "No entries for $(whoami)"
fi
if [ -f /etc/subgid ]; then
    echo "/etc/subgid:"
    cat /etc/subgid | grep $(whoami) || echo "No entries for $(whoami)"
fi
echo ""

echo "=== Node.js Version ==="
if command -v node &> /dev/null; then
    node --version
    which node
else
    echo "Node.js not installed"
fi
echo ""

echo "=== Ray Installation ==="
if [ -f ~/.venv/bin/activate ]; then
    source ~/.venv/bin/activate
    if command -v ray &> /dev/null; then
        ray --version
        which ray
    else
        echo "Ray not found in venv"
    fi
else
    echo "No venv to check for Ray"
fi
echo ""

echo "=== Directory Structure ==="
echo "Home directory: $(pwd)"
ls -la ~/
echo ""
echo "Project directory:"
ls -la ~/dev/cc-hitl-template/ 2>/dev/null || echo "Project not found at ~/dev/cc-hitl-template/"
echo ""

echo "=== /tmp/ray Permissions ==="
ls -la /tmp/ray 2>/dev/null || echo "/tmp/ray does not exist"
echo ""

echo "=== Running Processes ==="
ps aux | grep -E "ray|koco|python" | grep -v grep || echo "No Ray/Koco processes running"
echo ""

echo "=== Network Listeners ==="
netstat -tlnp 2>/dev/null | grep -E "6379|8265|8001|3370" || ss -tlnp | grep -E "6379|8265|8001|3370" || echo "No listeners on expected ports"
echo ""

echo "=== Environment Variables ==="
echo "Current user: $(whoami)"
echo "Home: $HOME"
echo "PATH: $PATH"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}... (truncated)"
EOF

echo ""
echo "==================================="
echo "Export complete!"
echo "==================================="
