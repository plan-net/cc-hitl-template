#!/usr/bin/env bash
#
# build-and-push.sh
# Build and push Claude HITL worker image to GitHub Container Registry
#
# Prerequisites:
#   - Podman or Docker installed
#   - GitHub Personal Access Token with packages:write scope
#   - GITHUB_TOKEN environment variable set
#   - GitHub username configured
#
# Usage:
#   ./build-and-push.sh [OPTIONS]
#
# Options:
#   -u, --username <name>     GitHub username (default: from git config)
#   -t, --tag <tag>          Image tag (default: latest)
#   -m, --master <repo>      Master config repo (default: cc-master-agent-config)
#   -p, --project <repo>     Project config repo (default: cc-example-agent-config)
#   --no-push                Build only, don't push to registry
#   -h, --help               Show this help message

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
GITHUB_USERNAME=$(git config user.name || echo "")
IMAGE_TAG="latest"
MASTER_REPO="cc-master-agent-config"
PROJECT_REPO="cc-example-agent-config"
PUSH_IMAGE=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -u|--username)
      GITHUB_USERNAME="$2"
      shift 2
      ;;
    -t|--tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    -m|--master)
      MASTER_REPO="$2"
      shift 2
      ;;
    -p|--project)
      PROJECT_REPO="$2"
      shift 2
      ;;
    --no-push)
      PUSH_IMAGE=false
      shift
      ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# //' | sed 's/^#//'
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Run with --help for usage information"
      exit 1
      ;;
  esac
done

# Validate prerequisites
if [[ -z "$GITHUB_USERNAME" ]]; then
  echo -e "${RED}Error: GitHub username not set${NC}"
  echo "Set it with: export GITHUB_USERNAME=your-username"
  echo "Or use: $0 --username your-username"
  exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]] && [[ "$PUSH_IMAGE" == true ]]; then
  echo -e "${RED}Error: GITHUB_TOKEN environment variable not set${NC}"
  echo "Create a Personal Access Token at: https://github.com/settings/tokens"
  echo "Token needs 'packages:write' scope"
  echo "Then set it with: export GITHUB_TOKEN=ghp_..."
  exit 1
fi

# Detect container tool (podman or docker)
if command -v podman &> /dev/null; then
  CONTAINER_TOOL="podman"
elif command -v docker &> /dev/null; then
  CONTAINER_TOOL="docker"
else
  echo -e "${RED}Error: Neither podman nor docker found${NC}"
  echo "Install podman: brew install podman"
  echo "Or install docker: brew install docker"
  exit 1
fi

echo -e "${BLUE}=== Claude HITL Worker Image Builder ===${NC}"
echo -e "${BLUE}Container tool: ${CONTAINER_TOOL}${NC}"
echo -e "${BLUE}GitHub username: ${GITHUB_USERNAME}${NC}"
echo -e "${BLUE}Image tag: ${IMAGE_TAG}${NC}"
echo ""

# Create temporary directory for cloning configs
TMP_DIR=$(mktemp -d)
trap "rm -rf ${TMP_DIR}" EXIT

echo -e "${YELLOW}→ Cloning agent configs...${NC}"

# Clone master config
echo -e "  Cloning ${MASTER_REPO}..."
if ! git clone --depth 1 "git@github.com:${GITHUB_USERNAME}/${MASTER_REPO}.git" "${TMP_DIR}/master" 2>/dev/null; then
  echo -e "${RED}Error: Failed to clone ${MASTER_REPO}${NC}"
  echo "Make sure the repository exists and you have access"
  echo "Repository URL: git@github.com:${GITHUB_USERNAME}/${MASTER_REPO}.git"
  exit 1
fi

# Clone project config
echo -e "  Cloning ${PROJECT_REPO}..."
if ! git clone --depth 1 "git@github.com:${GITHUB_USERNAME}/${PROJECT_REPO}.git" "${TMP_DIR}/project" 2>/dev/null; then
  echo -e "${RED}Error: Failed to clone ${PROJECT_REPO}${NC}"
  echo "Make sure the repository exists and you have access"
  echo "Repository URL: git@github.com:${GITHUB_USERNAME}/${PROJECT_REPO}.git"
  exit 1
fi

# Verify .claude directories exist
if [[ ! -d "${TMP_DIR}/master/.claude" ]]; then
  echo -e "${RED}Error: ${MASTER_REPO} does not contain .claude/ directory${NC}"
  exit 1
fi

if [[ ! -d "${TMP_DIR}/project/.claude" ]]; then
  echo -e "${RED}Error: ${PROJECT_REPO} does not contain .claude/ directory${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Configs cloned successfully${NC}"
echo ""

# Copy .claude folders into build context
echo -e "${YELLOW}→ Copying configs into build context...${NC}"
mkdir -p ./build_configs/master
mkdir -p ./build_configs/project
cp -r "${TMP_DIR}/master/.claude" ./build_configs/master/
cp -r "${TMP_DIR}/project/.claude" ./build_configs/project/
echo -e "${GREEN}✓ Configs copied${NC}"
echo ""

# Build image
IMAGE_NAME="ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker:${IMAGE_TAG}"

echo -e "${YELLOW}→ Building Docker image: ${IMAGE_NAME}${NC}"
${CONTAINER_TOOL} build \
  --build-arg MASTER_CONFIG_PATH="build_configs/master/.claude" \
  --build-arg PROJECT_CONFIG_PATH="build_configs/project/.claude" \
  -t "${IMAGE_NAME}" \
  .

echo -e "${GREEN}✓ Image built successfully${NC}"
echo ""

# Push image if requested
if [[ "$PUSH_IMAGE" == true ]]; then
  echo -e "${YELLOW}→ Logging in to GitHub Container Registry...${NC}"
  echo "${GITHUB_TOKEN}" | ${CONTAINER_TOOL} login ghcr.io -u "${GITHUB_USERNAME}" --password-stdin

  echo -e "${YELLOW}→ Pushing image to registry...${NC}"
  ${CONTAINER_TOOL} push "${IMAGE_NAME}"

  echo -e "${GREEN}✓ Image pushed successfully${NC}"
  echo ""
  echo -e "${GREEN}🎉 Done! Image available at:${NC}"
  echo -e "   ${BLUE}${IMAGE_NAME}${NC}"
  echo ""
  echo -e "${YELLOW}Next steps:${NC}"
  echo -e "  1. Update agent.py to use: ${IMAGE_NAME}"
  echo -e "  2. Deploy with: koco deploy -r"
  echo -e "  3. Ray will pull the image from ghcr.io"
else
  echo -e "${GREEN}✓ Build complete (not pushed)${NC}"
  echo -e "   Image: ${IMAGE_NAME}"
  echo -e ""
  echo -e "${YELLOW}To push later:${NC}"
  echo -e "   ${CONTAINER_TOOL} push ${IMAGE_NAME}"
fi

# Cleanup
echo -e "${YELLOW}→ Cleaning up...${NC}"
rm -rf ./build_configs
echo -e "${GREEN}✓ Cleanup complete${NC}"
