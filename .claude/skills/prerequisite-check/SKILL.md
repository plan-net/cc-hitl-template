---
name: prerequisite-check
description: Check and validate all required prerequisites for Claude + Kodosumi HITL setup
---

# Prerequisite Check Skill

Verifies all required software and tools are installed before proceeding with setup.

## When to Use

- At the beginning of `/cc-setup` to validate environment
- After user installs missing prerequisites to re-verify
- When troubleshooting installation issues

## What It Checks

### All Platforms
1. **Python 3.12+** - Required for Ray and Kodosumi
2. **Git** - Required for cloning repositories
3. **Node.js 18+** - Required for Claude CLI
4. **Claude Code CLI** - Required for Claude SDK

### macOS Specific
5. **Homebrew** - Package manager for installing dependencies
6. **Podman** - For building Docker images on macOS
7. **OrbStack** - For Linux VM with Ray cluster

### Linux Specific
5. **Docker** - For building and running containers

## Execution

```bash
bash .claude/skills/prerequisite-check/scripts/check.sh
```

## Output Format

The script returns a structured report with pass/fail status for each prerequisite:

```
=== PREREQUISITE CHECK ===
[✓] Python 3.12+: 3.12.9 installed
[✓] Git: 2.45.0 installed
[✓] Node.js 18+: 18.20.0 installed
[✓] Claude CLI: 1.0.0 installed
[✓] Homebrew: 4.2.0 installed (macOS)
[✗] Podman: NOT FOUND
[✓] OrbStack: 1.5.0 installed (macOS)

=== SUMMARY ===
Status: INCOMPLETE
Missing: Podman
Install: brew install podman
```

## Return Values

- **Exit Code 0**: All prerequisites met
- **Exit Code 1**: Some prerequisites missing
- **Exit Code 2**: Critical error (wrong OS, etc.)

## Usage in Setup Agent

```bash
# Run prerequisite check
if bash .claude/skills/prerequisite-check/scripts/check.sh; then
    echo "All prerequisites met, continuing setup..."
else
    echo "Missing prerequisites, guiding user through installation..."
    # Parse output and guide user
fi
```

## Example Integration

```bash
# Save output to variable
PREREQ_OUTPUT=$(bash .claude/skills/prerequisite-check/scripts/check.sh)
PREREQ_STATUS=$?

if [ $PREREQ_STATUS -eq 0 ]; then
    echo "✅ All prerequisites verified"
elif [ $PREREQ_STATUS -eq 1 ]; then
    echo "⚠️ Missing prerequisites:"
    echo "$PREREQ_OUTPUT" | grep "\[✗\]"
    # Guide user through installation
else
    echo "❌ Critical error during check"
    echo "$PREREQ_OUTPUT"
    exit 1
fi
```

## Installation Guidance

The skill provides installation commands for missing prerequisites:

**macOS**:
```bash
brew install python@3.12 podman orbstack node@18
sudo npm install -g @anthropic-ai/claude-code
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git
sudo apt install -y docker.io
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g @anthropic-ai/claude-code
```

## Notes

- Script is OS-aware and checks platform-specific requirements
- Validates minimum versions (Python 3.12+, Node.js 18+)
- Checks executable availability in PATH
- Provides actionable installation commands
- Safe to run multiple times (idempotent)
