#!/usr/bin/env bash
#
# Docker Build Skill - Build and push Claude HITL worker image
#
# This script builds the Docker image with baked-in .claude configurations
# from separate git repositories and tracks deployment state.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Claude HITL Worker Image Builder ===${NC}"
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

# Detect container tool (podman or docker)
if command -v podman &> /dev/null; then
  CONTAINER_TOOL="podman"
elif command -v docker &> /dev/null; then
  CONTAINER_TOOL="docker"
else
  echo -e "${RED}✗ Error: Neither podman nor docker found${NC}"
  echo "Install podman: brew install podman"
  echo "Or install docker: brew install docker"
  exit 1
fi

echo -e "${GREEN}✓ Prerequisites validated${NC}"
echo -e "${BLUE}Container tool: ${CONTAINER_TOOL}${NC}"
echo -e "${BLUE}GitHub username: ${GITHUB_USERNAME}${NC}"
echo ""

# Create temporary directory for cloning configs
TMP_DIR=$(mktemp -d)
trap "rm -rf ${TMP_DIR}" EXIT

echo -e "${YELLOW}→ Cloning agent configs...${NC}"

# Clone master config
echo -e "  Cloning master config from ${MASTER_CONFIG_REPO}..."
if ! git clone --depth 1 "${MASTER_CONFIG_REPO}" "${TMP_DIR}/master" 2>/dev/null; then
  echo -e "${RED}✗ Error: Failed to clone ${MASTER_CONFIG_REPO}${NC}"
  echo "  Make sure the repository exists and you have access"
  exit 1
fi

# Clone project config
echo -e "  Cloning project config from ${PROJECT_CONFIG_REPO}..."
if ! git clone --depth 1 "${PROJECT_CONFIG_REPO}" "${TMP_DIR}/project" 2>/dev/null; then
  echo -e "${RED}✗ Error: Failed to clone ${PROJECT_CONFIG_REPO}${NC}"
  echo "  Make sure the repository exists and you have access"
  exit 1
fi

# Verify .claude directories exist
if [[ ! -d "${TMP_DIR}/master/.claude" ]]; then
  echo -e "${RED}✗ Error: Master config repo does not contain .claude/ directory${NC}"
  exit 1
fi

if [[ ! -d "${TMP_DIR}/project/.claude" ]]; then
  echo -e "${RED}✗ Error: Project config repo does not contain .claude/ directory${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Configs cloned successfully${NC}"
echo ""

# Capture commit hashes for deployment state tracking
MASTER_COMMIT=$(cd "${TMP_DIR}/master" && git rev-parse HEAD)
PROJECT_COMMIT=$(cd "${TMP_DIR}/project" && git rev-parse HEAD)

# Copy .claude folders into build context
echo -e "${YELLOW}→ Copying configs into build context...${NC}"
mkdir -p ./build_configs/master
mkdir -p ./build_configs/project
cp -r "${TMP_DIR}/master/.claude" ./build_configs/master/
cp -r "${TMP_DIR}/project/.claude" ./build_configs/project/
echo -e "${GREEN}✓ Configs copied${NC}"
echo ""

# Build image
IMAGE_TAG="latest"
IMAGE_NAME="ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker:${IMAGE_TAG}"

echo -e "${YELLOW}→ Building Docker image: ${IMAGE_NAME}${NC}"
${CONTAINER_TOOL} build \
  --build-arg MASTER_CONFIG_PATH="build_configs/master/.claude" \
  --build-arg PROJECT_CONFIG_PATH="build_configs/project/.claude" \
  -t "${IMAGE_NAME}" \
  .

echo -e "${GREEN}✓ Image built successfully${NC}"
echo ""

# Push image
echo -e "${YELLOW}→ Logging in to GitHub Container Registry...${NC}"
echo "${GITHUB_TOKEN}" | ${CONTAINER_TOOL} login ghcr.io -u "${GITHUB_USERNAME}" --password-stdin

echo -e "${YELLOW}→ Pushing image to registry...${NC}"
${CONTAINER_TOOL} push "${IMAGE_NAME}"

echo -e "${GREEN}✓ Image pushed successfully${NC}"
echo ""

# Capture image digest and metadata
echo -e "${YELLOW}→ Capturing deployment state for tracking...${NC}"

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

# Cleanup
echo -e "${YELLOW}→ Cleaning up...${NC}"
rm -rf ./build_configs
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# Construct full URI with digest for immutable reference
CONTAINER_IMAGE_URI="${IMAGE_NAME%:*}@${IMAGE_DIGEST}"

# Output for deployment agent to parse
echo "=== DEPLOYMENT STATE ==="
echo "MASTER_CONFIG_COMMIT=${MASTER_COMMIT}"
echo "PROJECT_CONFIG_COMMIT=${PROJECT_COMMIT}"
echo "CONTAINER_IMAGE_URI=${CONTAINER_IMAGE_URI}"
echo "IMAGE_SIZE=${IMAGE_SIZE_HUMAN}"
echo "BUILD_TIMESTAMP=${BUILD_TIMESTAMP}"
echo "BUILD_STATUS=success"
echo "========================"
echo ""

echo -e "${GREEN}✓ Container image built and pushed${NC}"
echo -e "  URI: ${CONTAINER_IMAGE_URI}"
echo -e "  Size: ${IMAGE_SIZE_HUMAN}"
