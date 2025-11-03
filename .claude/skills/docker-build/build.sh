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
echo -e "${YELLOW}→ Capturing deployment state for tracking...${NC}"

MASTER_COMMIT=$(git ls-remote "${MASTER_CONFIG_REPO}" HEAD | cut -f1)
PROJECT_COMMIT=$(git ls-remote "${PROJECT_CONFIG_REPO}" HEAD | cut -f1)

# Detect container tool
if command -v podman &> /dev/null; then
  CONTAINER_TOOL="podman"
elif command -v docker &> /dev/null; then
  CONTAINER_TOOL="docker"
else
  echo -e "${RED}✗ Error: Neither podman nor docker found${NC}"
  exit 1
fi

# Capture image digest and metadata
IMAGE_NAME="ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker:latest"

# Get image digest (SHA256)
IMAGE_DIGEST=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{index .Digest}}' 2>/dev/null || echo "")
if [ -z "${IMAGE_DIGEST}" ]; then
  # Fallback: try getting from RepoDigests after push
  IMAGE_DIGEST=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{index .RepoDigests 0}}' 2>/dev/null | cut -d@ -f2 || echo "unknown")
fi

# Get image size
IMAGE_SIZE=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{.Size}}' 2>/dev/null || echo "0")
# Convert bytes to human-readable format
if [ "${IMAGE_SIZE}" != "0" ] && [ "${IMAGE_SIZE}" != "" ]; then
  IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
  IMAGE_SIZE_HUMAN="${IMAGE_SIZE_MB}MB"
else
  IMAGE_SIZE_HUMAN="unknown"
fi

# Capture build timestamp
BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo -e "${GREEN}✓ Deployment state captured${NC}"
echo ""

# Output for deployment agent to parse
echo "=== DEPLOYMENT STATE ==="
echo "MASTER_CONFIG_COMMIT=${MASTER_COMMIT}"
echo "PROJECT_CONFIG_COMMIT=${PROJECT_COMMIT}"
echo "DOCKER_IMAGE_TAG=${IMAGE_NAME}"
echo "DOCKER_IMAGE_DIGEST=${IMAGE_DIGEST}"
echo "IMAGE_SIZE=${IMAGE_SIZE_HUMAN}"
echo "BUILD_TIMESTAMP=${BUILD_TIMESTAMP}"
echo "BUILD_STATUS=success"
echo "========================"
echo ""

echo -e "${GREEN}✓ Docker build skill completed${NC}"
echo ""
echo -e "${BLUE}Image Details:${NC}"
echo -e "  Tag: ${IMAGE_NAME}"
echo -e "  Digest: ${IMAGE_DIGEST}"
echo -e "  Size: ${IMAGE_SIZE_HUMAN}"
echo -e "  Built: ${BUILD_TIMESTAMP}"
