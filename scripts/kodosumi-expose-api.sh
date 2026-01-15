#!/bin/bash
# =============================================================================
# Kodosumi Expose API Script
# =============================================================================
# Manage Kodosumi applications via REST API instead of CLI
#
# Usage:
#   ./scripts/kodosumi-expose-api.sh <command> [options]
#
# Commands:
#   login                    - Authenticate and get session
#   list                     - List all expose items
#   get <name>               - Get specific expose config
#   create <name>            - Create new expose from template
#   delete <name>            - Delete expose item
#   boot                     - Boot all enabled applications
#   shutdown                 - Shutdown all applications
#   status                   - Get boot status
#   create-mein-neuer-agent  - Create "Mein Neuer Agent" example
#
# Requirements:
#   - curl
#   - jq (optional, for pretty output)
#   - Kodosumi running at localhost:3370
#
# =============================================================================

set -e

# Configuration
KODOSUMI_URL="${KODOSUMI_URL:-http://localhost:3370}"
KODOSUMI_USER="${KODOSUMI_USER:-admin}"
KODOSUMI_PASS="${KODOSUMI_PASS:-admin}"
COOKIE_FILE="/tmp/kodosumi_cookies_$$.txt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cleanup() {
    rm -f "$COOKIE_FILE" 2>/dev/null || true
}

trap cleanup EXIT

# Pretty print JSON if jq is available
pretty_json() {
    if command -v jq &> /dev/null; then
        jq '.'
    else
        cat
    fi
}

# =============================================================================
# API Functions
# =============================================================================

# Login and store session cookies
api_login() {
    log_info "Logging in to Kodosumi at $KODOSUMI_URL..."

    local response
    response=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
        "${KODOSUMI_URL}/login?name=${KODOSUMI_USER}&password=${KODOSUMI_PASS}" \
        -H "accept: application/json")

    if echo "$response" | grep -q "KODOSUMI_API_KEY"; then
        log_success "Login successful"
        echo "$response" | pretty_json
        return 0
    else
        log_error "Login failed: $response"
        return 1
    fi
}

# List all expose items
api_list() {
    api_login > /dev/null

    log_info "Listing all expose items..."
    curl -s -b "$COOKIE_FILE" "${KODOSUMI_URL}/expose" \
        -H "accept: application/json" | pretty_json
}

# Get specific expose config
api_get() {
    local name="$1"
    if [ -z "$name" ]; then
        log_error "Usage: $0 get <name>"
        return 1
    fi

    api_login > /dev/null

    log_info "Getting expose config for '$name'..."
    curl -s -b "$COOKIE_FILE" "${KODOSUMI_URL}/expose/${name}" \
        -H "accept: application/json" | pretty_json
}

# Delete expose item
api_delete() {
    local name="$1"
    if [ -z "$name" ]; then
        log_error "Usage: $0 delete <name>"
        return 1
    fi

    api_login > /dev/null

    log_warn "Deleting expose '$name'..."
    curl -s -b "$COOKIE_FILE" -X DELETE "${KODOSUMI_URL}/expose/${name}" \
        -H "accept: application/json" | pretty_json
}

# Boot all enabled applications
api_boot() {
    api_login > /dev/null

    log_info "Booting all enabled applications..."
    curl -s -b "$COOKIE_FILE" -X POST "${KODOSUMI_URL}/boot" \
        -H "accept: application/json"
    echo ""
    log_success "Boot completed"
}

# Shutdown all applications
api_shutdown() {
    api_login > /dev/null

    log_warn "Shutting down all applications..."
    curl -s -b "$COOKIE_FILE" -X DELETE "${KODOSUMI_URL}/boot" \
        -H "accept: application/json" | pretty_json
}

# Get boot status
api_status() {
    api_login > /dev/null

    log_info "Getting boot status..."
    curl -s -b "$COOKIE_FILE" "${KODOSUMI_URL}/boot" \
        -H "accept: application/json" | pretty_json
}

# Create expose item from JSON
api_create() {
    local json="$1"
    if [ -z "$json" ]; then
        log_error "Usage: $0 create '<json>'"
        return 1
    fi

    api_login > /dev/null

    log_info "Creating expose item..."
    curl -s -b "$COOKIE_FILE" -X POST "${KODOSUMI_URL}/expose" \
        -H "Content-Type: application/json" \
        -H "accept: application/json" \
        -d "$json" | pretty_json
}

# =============================================================================
# Template: Create "Mein Neuer Agent"
# =============================================================================

create_mein_neuer_agent() {
    # Load environment variables from .env if available
    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

    if [ -f "$PROJECT_DIR/.env" ]; then
        log_info "Loading environment from $PROJECT_DIR/.env"
        source "$PROJECT_DIR/.env"
    fi

    # Validate required variables
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        log_error "ANTHROPIC_API_KEY not set. Please set it in .env or environment."
        return 1
    fi

    if [ -z "$GITHUB_USERNAME" ]; then
        log_error "GITHUB_USERNAME not set. Please set it in .env or environment."
        return 1
    fi

    # Set defaults
    local CONTAINER_IMAGE="${CONTAINER_IMAGE_URI:-ghcr.io/${GITHUB_USERNAME}/claude-hitl-worker:latest}"
    local GITHUB_TOKEN_VAL="${GITHUB_TOKEN:-}"

    log_info "Creating 'Mein Neuer Agent' with:"
    log_info "  - Container Image: $CONTAINER_IMAGE"
    log_info "  - GitHub Username: $GITHUB_USERNAME"

    # Bootstrap configuration (Ray Serve deployment)
    local BOOTSTRAP=$(cat <<'BOOTSTRAP_EOF'
# Ray Serve Import Path
# Format: module.submodule:variable
import_path: claude_hitl_template.query:fast_app

# Runtime Environment Configuration
runtime_env:
  env_vars:
    # ==========================================================================
    # Container Configuration
    # ==========================================================================
    # Container image URI for Ray actors
    # Use YOUR OWN image from YOUR GitHub Container Registry
    # Format: ghcr.io/<GITHUB_USERNAME>/<image-name>:<tag>
    # Leave empty for non-containerized deployment (runs from filesystem)
    CONTAINER_IMAGE_URI: "__CONTAINER_IMAGE__"

    # ==========================================================================
    # Claude API Configuration (REQUIRED)
    # ==========================================================================
    # Your Anthropic API Key
    # IMPORTANT: Must be the literal key value, NOT a variable reference
    # Ray Serve YAML does NOT support ${VARIABLE} substitution
    ANTHROPIC_API_KEY: "__ANTHROPIC_API_KEY__"

    # ==========================================================================
    # GitHub Container Registry (for pulling images)
    # ==========================================================================
    # Your GitHub username (for ghcr.io authentication)
    GITHUB_USERNAME: "__GITHUB_USERNAME__"

    # GitHub Personal Access Token with read:packages scope
    # Required for pulling private container images
    GITHUB_TOKEN: "__GITHUB_TOKEN__"

    # ==========================================================================
    # Optional: Application Settings
    # ==========================================================================
    # Enable file upload functionality
    UPLOAD_FILES: "False"

    # Completion mode: "continuous" or "auto-complete"
    COMPLETION_MODE: "continuous"

# ==========================================================================
# Ray Serve Deployment Settings
# ==========================================================================
# Resource allocation per replica
ray_actor_options:
  num_cpus: 0.1
  # num_gpus: 0
  # memory: 1000000000  # 1GB in bytes

# Number of replicas (optional)
# num_replicas: 1
BOOTSTRAP_EOF
)

    # Replace placeholders with actual values
    BOOTSTRAP="${BOOTSTRAP//__CONTAINER_IMAGE__/$CONTAINER_IMAGE}"
    BOOTSTRAP="${BOOTSTRAP//__ANTHROPIC_API_KEY__/$ANTHROPIC_API_KEY}"
    BOOTSTRAP="${BOOTSTRAP//__GITHUB_USERNAME__/$GITHUB_USERNAME}"
    BOOTSTRAP="${BOOTSTRAP//__GITHUB_TOKEN__/$GITHUB_TOKEN_VAL}"

    # Meta configuration (flow metadata shown in UI)
    local META_DATA=$(cat <<'META_EOF'
# Flow Metadata Configuration
# Shown in Kodosumi Admin Panel

# Display name (shown in UI)
display: Mein Neuer Agent

# Description of what this agent does
description: |
  Ein neuer HITL Agent basierend auf dem cc-hitl-template.
  Demonstriert die Kodosumi Expose API.

# Tags for categorization and search
tags:
  - AI
  - Claude
  - HITL
  - Template

# Author information
author:
  name: Developer
  organization: Plan.Net
  contact_email: developer@example.com

# Example inputs (optional)
# example:
#   - name: sample_input
#     mime_type: application/json
#     url: https://example.com/sample.json
META_EOF
)

    # Escape special characters for JSON
    BOOTSTRAP_ESCAPED=$(echo "$BOOTSTRAP" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
    META_ESCAPED=$(echo "$META_DATA" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

    # Build JSON payload
    local JSON_PAYLOAD=$(cat <<EOF
{
    "name": "mein-neuer-agent",
    "display": "Mein Neuer Agent",
    "enabled": true,
    "network": null,
    "bootstrap": $BOOTSTRAP_ESCAPED,
    "meta": [
        {
            "url": "/mein-neuer-agent/",
            "data": $META_ESCAPED,
            "enabled": true
        }
    ]
}
EOF
)

    # Login and create
    api_login > /dev/null

    log_info "Creating expose 'mein-neuer-agent'..."
    local response
    response=$(curl -s -b "$COOKIE_FILE" -X POST "${KODOSUMI_URL}/expose" \
        -H "Content-Type: application/json" \
        -H "accept: application/json" \
        -d "$JSON_PAYLOAD")

    echo "$response" | pretty_json

    if echo "$response" | grep -q '"name"'; then
        log_success "Expose 'mein-neuer-agent' created successfully!"
        log_info ""
        log_info "Next steps:"
        log_info "  1. Boot the application: $0 boot"
        log_info "  2. Access in browser: ${KODOSUMI_URL}/admin/expose"
        log_info "  3. Test endpoint: curl ${KODOSUMI_URL}/mein-neuer-agent/"
    else
        log_error "Failed to create expose"
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================

show_help() {
    cat <<EOF
Kodosumi Expose API Script

Usage: $0 <command> [options]

Commands:
  login                     Authenticate and get session
  list                      List all expose items
  get <name>                Get specific expose config
  create '<json>'           Create expose from JSON
  delete <name>             Delete expose item
  boot                      Boot all enabled applications
  shutdown                  Shutdown all applications
  status                    Get boot status
  create-mein-neuer-agent   Create example "Mein Neuer Agent"

Environment Variables:
  KODOSUMI_URL    Kodosumi URL (default: http://localhost:3370)
  KODOSUMI_USER   Username (default: admin)
  KODOSUMI_PASS   Password (default: admin)

Examples:
  $0 login
  $0 list
  $0 get claude
  $0 create-mein-neuer-agent
  $0 boot
  $0 status
  $0 delete mein-neuer-agent

EOF
}

main() {
    local command="${1:-}"
    shift || true

    case "$command" in
        login)
            api_login
            ;;
        list)
            api_list
            ;;
        get)
            api_get "$@"
            ;;
        create)
            api_create "$@"
            ;;
        delete)
            api_delete "$@"
            ;;
        boot)
            api_boot
            ;;
        shutdown)
            api_shutdown
            ;;
        status)
            api_status
            ;;
        create-mein-neuer-agent)
            create_mein_neuer_agent
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
