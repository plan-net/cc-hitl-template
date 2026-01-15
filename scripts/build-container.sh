#!/bin/bash
# =============================================================================
# Container Build Script with Semantic Versioning
# =============================================================================
# Builds, tags, and pushes container images with proper versioning.
#
# Usage:
#   ./scripts/build-container.sh <version>
#   ./scripts/build-container.sh v1.0.1
#   ./scripts/build-container.sh v1.0.1 --no-push   # Build only, don't push
#
# Prerequisites:
#   - .env file with GITHUB_USERNAME
#   - Logged into ghcr.io (podman login ghcr.io)
#
# Output:
#   - Image tagged with version: ghcr.io/<user>/claude-hitl-worker:v1.0.1
#   - Image tagged as latest: ghcr.io/<user>/claude-hitl-worker:latest
#   - .image-info.json updated with version, digest, timestamp
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# =============================================================================
# Parse Arguments
# =============================================================================

VERSION="${1:-}"
NO_PUSH="${2:-}"

if [ -z "$VERSION" ]; then
    log_error "Usage: $0 <version> [--no-push]"
    log_error "Example: $0 v1.0.1"
    exit 1
fi

# Validate version format (v followed by semver)
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log_warn "Version '$VERSION' doesn't match vX.Y.Z format"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# =============================================================================
# Load Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if [ -f ".env" ]; then
    source .env
else
    log_error ".env file not found"
    exit 1
fi

if [ -z "$GITHUB_USERNAME" ]; then
    log_error "GITHUB_USERNAME not set in .env"
    exit 1
fi

IMAGE_NAME="ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker"
IMAGE_VERSION="${IMAGE_NAME}:${VERSION}"
IMAGE_LATEST="${IMAGE_NAME}:latest"

log_info "Building container image"
log_info "  Version: $VERSION"
log_info "  Image: $IMAGE_VERSION"
log_info "  User: $GITHUB_USERNAME"

# =============================================================================
# Create Image Info JSON (baked into image)
# =============================================================================

BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SEMVER="${VERSION#v}"  # Remove 'v' prefix for semantic version

# Get git information (try git commands first, fallback to existing .image-info.json)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "")
GIT_COMMIT_FULL=$(git rev-parse HEAD 2>/dev/null || echo "")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
GIT_DIRTY=$(git diff --quiet 2>/dev/null && echo "false" || echo "true")

# If git info not available, try to read from existing .image-info.json
# This allows syncing .image-info.json from a machine with .git to one without
if [ -z "$GIT_COMMIT" ] || [ "$GIT_COMMIT" = "unknown" ]; then
    if [ -f "$PROJECT_DIR/.image-info.json" ]; then
        log_info "Git not available, reading from existing .image-info.json"
        # Use Python to parse JSON (always available, unlike jq)
        EXISTING_COMMIT=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.image-info.json')); print(d.get('git',{}).get('commit','unknown'))" 2>/dev/null || echo "unknown")
        EXISTING_COMMIT_FULL=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.image-info.json')); print(d.get('git',{}).get('commit_full','unknown'))" 2>/dev/null || echo "unknown")
        EXISTING_BRANCH=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.image-info.json')); print(d.get('git',{}).get('branch','unknown'))" 2>/dev/null || echo "unknown")
        EXISTING_DIRTY=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.image-info.json')); print(str(d.get('git',{}).get('dirty',True)).lower())" 2>/dev/null || echo "true")

        # Use existing values if they're valid
        if [ "$EXISTING_COMMIT" != "unknown" ] && [ "$EXISTING_COMMIT" != "" ]; then
            GIT_COMMIT="$EXISTING_COMMIT"
            GIT_COMMIT_FULL="$EXISTING_COMMIT_FULL"
            GIT_BRANCH="$EXISTING_BRANCH"
            GIT_DIRTY="$EXISTING_DIRTY"
            log_info "  Using existing git info: $GIT_COMMIT ($GIT_BRANCH)"
        fi
    fi
fi

# Final fallback to "unknown"
GIT_COMMIT="${GIT_COMMIT:-unknown}"
GIT_COMMIT_FULL="${GIT_COMMIT_FULL:-unknown}"
GIT_BRANCH="${GIT_BRANCH:-unknown}"
GIT_DIRTY="${GIT_DIRTY:-true}"

log_info "Creating .image-info.json"
log_info "  Git commit: $GIT_COMMIT ($GIT_BRANCH)"

cat > "$PROJECT_DIR/.image-info.json" << EOF
{
    "version": "${SEMVER}",
    "tag": "${VERSION}",
    "build_timestamp": "${BUILD_TIMESTAMP}",
    "github_username": "${GITHUB_USERNAME}",
    "image_name": "${IMAGE_NAME}",
    "digest": "",
    "git": {
        "commit": "${GIT_COMMIT}",
        "commit_full": "${GIT_COMMIT_FULL}",
        "branch": "${GIT_BRANCH}",
        "dirty": ${GIT_DIRTY}
    }
}
EOF

log_success "Created .image-info.json"

# =============================================================================
# Prepare Build Configs (if not exists)
# =============================================================================

mkdir -p build_configs/dependencies build_configs/plugins

if [ ! -f "build_configs/dependencies/system-packages.txt" ]; then
    touch build_configs/dependencies/system-packages.txt
fi

if [ ! -f "build_configs/dependencies/requirements.txt" ]; then
    touch build_configs/dependencies/requirements.txt
fi

if [ ! -f "build_configs/dependencies/package.json" ]; then
    echo '{}' > build_configs/dependencies/package.json
fi

if [ ! -f "build_configs/.dependency-manifest.json" ]; then
    echo '{"timestamp":"'$BUILD_TIMESTAMP'","source":"build-script","python_packages":[],"nodejs_packages":[],"system_packages":[]}' > build_configs/.dependency-manifest.json
fi

# =============================================================================
# Build Image
# =============================================================================

log_info "Building image (this may take a few minutes)..."

podman build \
    -t "$IMAGE_VERSION" \
    -t "$IMAGE_LATEST" \
    "$PROJECT_DIR"

log_success "Image built: $IMAGE_VERSION"

# =============================================================================
# Push Image (unless --no-push)
# =============================================================================

if [ "$NO_PUSH" = "--no-push" ]; then
    log_warn "Skipping push (--no-push specified)"
else
    log_info "Pushing $IMAGE_VERSION..."
    podman push "$IMAGE_VERSION"
    log_success "Pushed $IMAGE_VERSION"

    log_info "Pushing $IMAGE_LATEST..."
    podman push "$IMAGE_LATEST"
    log_success "Pushed $IMAGE_LATEST"
fi

# =============================================================================
# Get and Store Digest
# =============================================================================

log_info "Getting image digest..."

DIGEST=$(podman inspect "$IMAGE_VERSION" --format '{{.Digest}}' 2>/dev/null || echo "")

if [ -z "$DIGEST" ]; then
    # Try to get from registry if local doesn't have it
    DIGEST=$(podman inspect "$IMAGE_VERSION" --format '{{index .RepoDigests 0}}' 2>/dev/null | grep -o 'sha256:[a-f0-9]*' || echo "")
fi

if [ -n "$DIGEST" ]; then
    log_success "Digest: $DIGEST"

    # Update .image-info.json with digest
    cat > "$PROJECT_DIR/.image-info.json" << EOF
{
    "version": "${SEMVER}",
    "tag": "${VERSION}",
    "build_timestamp": "${BUILD_TIMESTAMP}",
    "github_username": "${GITHUB_USERNAME}",
    "image_name": "${IMAGE_NAME}",
    "digest": "${DIGEST}",
    "git": {
        "commit": "${GIT_COMMIT}",
        "commit_full": "${GIT_COMMIT_FULL}",
        "branch": "${GIT_BRANCH}",
        "dirty": ${GIT_DIRTY}
    }
}
EOF
    log_success "Updated .image-info.json with digest"
else
    log_warn "Could not determine digest"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=============================================="
log_success "Build Complete!"
echo "=============================================="
echo ""
echo "Image Tags:"
echo "  - $IMAGE_VERSION"
echo "  - $IMAGE_LATEST"
echo ""
if [ -n "$DIGEST" ]; then
echo "Digest:"
echo "  - $DIGEST"
echo ""
fi
echo "To use in Expose config:"
echo "  CONTAINER_IMAGE_URI: \"$IMAGE_VERSION\""
echo ""
echo "Or with digest (immutable):"
echo "  CONTAINER_IMAGE_URI: \"${IMAGE_NAME}@${DIGEST}\""
echo ""
