#!/usr/bin/env bash
#
# prerequisite-check.sh
# Check all required prerequisites for Claude + Kodosumi HITL setup
#
# Returns:
#   0 - All prerequisites met
#   1 - Some prerequisites missing
#   2 - Critical error

set -uo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
OS=$(uname -s)
if [ "$OS" = "Darwin" ]; then
    PLATFORM="macOS"
elif [ "$OS" = "Linux" ]; then
    PLATFORM="Linux"
else
    echo -e "${RED}Unsupported operating system: $OS${NC}"
    exit 2
fi

# Track status
ALL_MET=true
MISSING=()

echo "=== PREREQUISITE CHECK ==="
echo "Platform: $PLATFORM"
echo ""

# Check Python 3.12+
if command -v python3.12 &> /dev/null; then
    PYTHON_VERSION=$(python3.12 --version | cut -d' ' -f2)
    echo -e "[${GREEN}✓${NC}] Python 3.12+: $PYTHON_VERSION installed"
else
    echo -e "[${RED}✗${NC}] Python 3.12+: NOT FOUND"
    MISSING+=("Python 3.12+")
    ALL_MET=false
fi

# Check Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "[${GREEN}✓${NC}] Git: $GIT_VERSION installed"
else
    echo -e "[${RED}✗${NC}] Git: NOT FOUND"
    MISSING+=("Git")
    ALL_MET=false
fi

# Check Node.js 18+
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d'.' -f1)

    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo -e "[${GREEN}✓${NC}] Node.js 18+: $NODE_VERSION installed"
    else
        echo -e "[${RED}✗${NC}] Node.js 18+: $NODE_VERSION installed (too old, need 18+)"
        MISSING+=("Node.js 18+")
        ALL_MET=false
    fi
else
    echo -e "[${RED}✗${NC}] Node.js 18+: NOT FOUND"
    MISSING+=("Node.js 18+")
    ALL_MET=false
fi

# Check Claude CLI
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>&1 | head -n1 || echo "unknown")
    echo -e "[${GREEN}✓${NC}] Claude CLI: $CLAUDE_VERSION installed"
else
    echo -e "[${RED}✗${NC}] Claude CLI: NOT FOUND"
    MISSING+=("Claude CLI")
    ALL_MET=false
fi

# Platform-specific checks
if [ "$PLATFORM" = "macOS" ]; then
    # Check Homebrew
    if command -v brew &> /dev/null; then
        BREW_VERSION=$(brew --version | head -n1 | cut -d' ' -f2)
        echo -e "[${GREEN}✓${NC}] Homebrew: $BREW_VERSION installed"
    else
        echo -e "[${RED}✗${NC}] Homebrew: NOT FOUND"
        MISSING+=("Homebrew")
        ALL_MET=false
    fi

    # Check Podman
    if command -v podman &> /dev/null; then
        PODMAN_VERSION=$(podman --version | cut -d' ' -f3)
        echo -e "[${GREEN}✓${NC}] Podman: $PODMAN_VERSION installed"
    else
        echo -e "[${RED}✗${NC}] Podman: NOT FOUND"
        MISSING+=("Podman")
        ALL_MET=false
    fi

    # Check OrbStack
    if command -v orb &> /dev/null; then
        ORB_VERSION=$(orb version 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1 || echo "unknown")
        echo -e "[${GREEN}✓${NC}] OrbStack: $ORB_VERSION installed"
    else
        echo -e "[${RED}✗${NC}] OrbStack: NOT FOUND"
        MISSING+=("OrbStack")
        ALL_MET=false
    fi

elif [ "$PLATFORM" = "Linux" ]; then
    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        echo -e "[${GREEN}✓${NC}] Docker: $DOCKER_VERSION installed"

        # Check if user can run docker without sudo
        if docker ps &> /dev/null; then
            echo -e "[${GREEN}✓${NC}] Docker: User has permissions"
        else
            echo -e "[${YELLOW}⚠${NC}] Docker: User needs to be in docker group"
            echo "    Run: sudo usermod -aG docker \$USER"
            echo "    Then logout and login again"
        fi
    else
        echo -e "[${RED}✗${NC}] Docker: NOT FOUND"
        MISSING+=("Docker")
        ALL_MET=false
    fi
fi

echo ""
echo "=== SUMMARY ==="

if [ "$ALL_MET" = true ]; then
    echo -e "Status: ${GREEN}COMPLETE${NC}"
    echo "All prerequisites are installed and ready!"
    exit 0
else
    echo -e "Status: ${RED}INCOMPLETE${NC}"
    echo ""
    echo "Missing prerequisites:"
    for item in "${MISSING[@]}"; do
        echo "  - $item"
    done
    echo ""
    echo "=== INSTALLATION GUIDE ==="

    if [ "$PLATFORM" = "macOS" ]; then
        echo ""
        echo "To install missing prerequisites on macOS:"
        echo ""

        # Check what's missing and provide specific commands
        for item in "${MISSING[@]}"; do
            case $item in
                "Homebrew")
                    echo "# Install Homebrew (package manager):"
                    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                    echo ""
                    ;;
                "Python 3.12+")
                    echo "# Install Python 3.12:"
                    echo "brew install python@3.12"
                    echo ""
                    ;;
                "Podman")
                    echo "# Install Podman (container engine):"
                    echo "brew install podman"
                    echo ""
                    ;;
                "OrbStack")
                    echo "# Install OrbStack (Linux VM):"
                    echo "brew install orbstack"
                    echo ""
                    ;;
                "Node.js 18+")
                    echo "# Install Node.js 18:"
                    echo "brew install node@18"
                    echo ""
                    ;;
                "Claude CLI")
                    echo "# Install Claude Code CLI:"
                    echo "sudo npm install -g @anthropic-ai/claude-code"
                    echo ""
                    ;;
                "Git")
                    echo "# Install Git:"
                    echo "brew install git"
                    echo ""
                    ;;
            esac
        done

    elif [ "$PLATFORM" = "Linux" ]; then
        echo ""
        echo "To install missing prerequisites on Linux (Ubuntu/Debian):"
        echo ""

        for item in "${MISSING[@]}"; do
            case $item in
                "Python 3.12+")
                    echo "# Install Python 3.12:"
                    echo "sudo apt update"
                    echo "sudo apt install -y python3.12 python3.12-venv python3-pip"
                    echo ""
                    ;;
                "Docker")
                    echo "# Install Docker:"
                    echo "sudo apt update"
                    echo "sudo apt install -y docker.io"
                    echo "sudo usermod -aG docker \$USER"
                    echo "# Logout and login again for group changes to take effect"
                    echo ""
                    ;;
                "Node.js 18+")
                    echo "# Install Node.js 18:"
                    echo "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
                    echo "sudo apt install -y nodejs"
                    echo ""
                    ;;
                "Claude CLI")
                    echo "# Install Claude Code CLI:"
                    echo "sudo npm install -g @anthropic-ai/claude-code"
                    echo ""
                    ;;
                "Git")
                    echo "# Install Git:"
                    echo "sudo apt update"
                    echo "sudo apt install -y git"
                    echo ""
                    ;;
            esac
        done
    fi

    echo "After installing missing prerequisites, run this check again."
    exit 1
fi
