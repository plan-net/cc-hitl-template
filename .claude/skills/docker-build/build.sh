#!/usr/bin/env bash
#
# Docker Build Skill - Build and push Claude HITL worker image
#
# This script wraps build-and-push.sh and captures commit hashes
# for deployment state tracking.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Docker Build Skill ===${NC}"
echo ""

# Check prerequisites
if [ ! -f .env ]; then
    echo -e "${RED}✗ Error: .env file not found${NC}"
    echo "  Copy .env.example to .env and configure your secrets"
    exit 1
fi

# Source environment
source .env

# Validate required variables
REQUIRED_VARS=("GITHUB_TOKEN" "GITHUB_USERNAME" "MASTER_CONFIG_REPO" "PROJECT_CONFIG_REPO" "ANTHROPIC_API_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo -e "${RED}✗ Error: $var not set in .env${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Prerequisites validated${NC}"
echo ""

# Execute main build script
echo -e "${YELLOW}→ Running build-and-push.sh...${NC}"
echo ""

if ! ./build-and-push.sh; then
    echo ""
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Build completed successfully${NC}"
echo ""

# Capture commit hashes from the cloned repos
# build-and-push.sh clones to /tmp, we need to get commits before cleanup
# Since build-and-push.sh cleans up, we need to fetch fresh
echo -e "${YELLOW}→ Capturing commit hashes for state tracking...${NC}"

MASTER_COMMIT=$(git ls-remote "${MASTER_CONFIG_REPO}" HEAD | cut -f1)
PROJECT_COMMIT=$(git ls-remote "${PROJECT_CONFIG_REPO}" HEAD | cut -f1)

echo -e "${GREEN}✓ Commit hashes captured${NC}"
echo ""

# Output for deployment agent to parse
echo "=== DEPLOYMENT STATE ==="
echo "MASTER_CONFIG_COMMIT=${MASTER_COMMIT}"
echo "PROJECT_CONFIG_COMMIT=${PROJECT_COMMIT}"
echo "DOCKER_IMAGE_TAG=ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker:latest"
echo "========================"
echo ""

echo -e "${GREEN}✓ Docker build skill completed${NC}"
