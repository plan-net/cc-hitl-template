#!/bin/bash
#
# Local Test Script for Advanced Web Research Agent
# Run this script to start all services locally without Claude Code
#
# Usage: ./scripts/local-test.sh [start|stop|restart|status]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cd "$PROJECT_ROOT"

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        log_info "Loading environment variables from .env"
        set -a
        source .env
        set +a
    else
        log_error ".env file not found. Please create it with required API keys:"
        echo ""
        echo "  EXA_API_KEY=your-exa-api-key"
        echo "  GAMMA_API_KEY=your-gamma-api-key"
        echo "  DO_SPACES_ACCESS_KEY=your-do-spaces-access-key"
        echo "  DO_SPACES_SECRET_KEY=your-do-spaces-secret-key"
        echo ""
        exit 1
    fi
}

# Activate virtual environment
activate_venv() {
    if [ -d ".venv" ]; then
        log_info "Activating virtual environment"
        source .venv/bin/activate
    else
        log_error "Virtual environment not found. Run: python3 -m venv .venv && pip install -e ."
        exit 1
    fi
}

# Check if Ray is running
is_ray_running() {
    ray status &>/dev/null
    return $?
}

# Check if Koco is running
is_koco_running() {
    pgrep -f "koco start" &>/dev/null
    return $?
}

# Start all services
start_services() {
    log_info "Starting services..."

    # Start Ray if not running
    if is_ray_running; then
        log_info "Ray is already running"
    else
        log_info "Starting Ray..."
        ray start --head
        sleep 3
    fi

    # Deploy Serve application
    log_info "Deploying Serve application..."
    serve deploy data/config/advanced_web_research.yaml
    sleep 2

    # Start Koco if not running
    if is_koco_running; then
        log_info "Koco is already running"
    else
        log_info "Starting Koco..."
        nohup .venv/bin/koco start --register http://localhost:8000/-/routes > /tmp/koco.log 2>&1 &
        sleep 3
    fi

    log_info "All services started!"
    echo ""
    echo "=========================================="
    echo "  Access the UI at: http://localhost:3370"
    echo "  Ray Dashboard:    http://localhost:8265"
    echo "=========================================="
    echo ""
}

# Stop all services
stop_services() {
    log_info "Stopping services..."

    # Stop Koco
    if is_koco_running; then
        log_info "Stopping Koco..."
        pkill -f "koco start" || true
    fi

    # Stop Serve
    log_info "Shutting down Serve..."
    serve shutdown -y 2>/dev/null || true

    # Stop Ray
    log_info "Stopping Ray..."
    ray stop --force 2>/dev/null || true

    log_info "All services stopped!"
}

# Show status of all services
show_status() {
    echo ""
    echo "=== Service Status ==="
    echo ""

    # Ray status
    if is_ray_running; then
        echo -e "Ray:   ${GREEN}RUNNING${NC}"
        ray status 2>/dev/null | head -20
    else
        echo -e "Ray:   ${RED}STOPPED${NC}"
    fi

    echo ""

    # Serve status
    if is_ray_running; then
        echo "Serve:"
        serve status 2>/dev/null || echo -e "  ${RED}NOT DEPLOYED${NC}"
    fi

    echo ""

    # Koco status
    if is_koco_running; then
        echo -e "Koco:  ${GREEN}RUNNING${NC} (http://localhost:3370)"
    else
        echo -e "Koco:  ${RED}STOPPED${NC}"
    fi

    echo ""
}

# Main
main() {
    local command="${1:-start}"

    load_env
    activate_venv

    case "$command" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_services
            ;;
        status)
            show_status
            ;;
        *)
            echo "Usage: $0 [start|stop|restart|status]"
            echo ""
            echo "Commands:"
            echo "  start   - Start all services (Ray, Serve, Koco)"
            echo "  stop    - Stop all services"
            echo "  restart - Restart all services"
            echo "  status  - Show status of all services"
            exit 1
            ;;
    esac
}

main "$@"
