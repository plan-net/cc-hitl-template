# Immutable Container Dependencies System

**Version:** 1.0.0
**Date:** 2025-11-06
**Status:** Specification
**Cross-Repo Impact:** cc-hitl-template, cc-marketplace-agents, cc-marketplace-developers, cc-master-agent-config, cc-example-agent-config

---

## Executive Summary

This specification defines a comprehensive system for managing plugin dependencies in immutable Docker containers for Claude HITL deployments. The system ensures all required packages (Python, Node.js, system) are baked into container images at build time, preventing runtime installation attempts while providing clear feedback mechanisms for dependency improvements.

## Problem Statement

### Current Issues

1. **Runtime Dependency Failures**: Containerized agents attempt to install packages (npm, pip) at runtime and fail due to missing write permissions or network restrictions
2. **No Dependency Discovery**: No mechanism for plugins to declare their runtime requirements
3. **Manual Dependency Management**: Container dependencies must be manually tracked and updated in Dockerfile
4. **Poor User Feedback**: Agents silently fail or produce confusing errors when dependencies are missing
5. **Inconsistent Behavior**: Different plugins have different approaches to handling missing dependencies

### Design Goals

1. **Immutable Containers**: All dependencies baked at build time; no runtime installations
2. **Declarative Dependencies**: Plugins declare requirements in manifest files
3. **Automatic Aggregation**: Build system automatically collects and installs all plugin dependencies
4. **Clear Agent Awareness**: Agents understand their immutable environment and communicate limitations clearly
5. **Improvement Feedback Loop**: Agents can suggest missing dependencies via structured messages to Kodosumi admin
6. **Universal Pattern**: Works for any combination of master + project configs and plugins

---

## Architecture Overview

### Dependency Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Plugin Marketplaces (cc-marketplace-*)                          │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Plugin: page-identifier                                   │   │
│ │ ├── skills/page-identifier/                              │   │
│ │ │   ├── SKILL.md           ← Documents required deps     │   │
│ │ │   └── scripts/                                         │   │
│ │ └── ...                                                   │   │
│ │                                                           │   │
│ │ NOTE: Plugins do NOT contain dependency manifests        │   │
│ │       (preserves Claude plugin spec compliance)          │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Config Repositories (cc-*-agent-config)                         │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ .claude/                                                  │   │
│ │ ├── settings.json        ← Enabled plugins list          │   │
│ │ └── CLAUDE.md            ← Agent instructions            │   │
│ │                                                           │   │
│ │ dependencies/            ← Declared dependencies         │   │
│ │ ├── requirements.txt     ← Python packages               │   │
│ │ ├── package.json         ← Node.js packages              │   │
│ │ ├── system-packages.txt  ← APT packages                  │   │
│ │ └── README.md            ← Documents deps per plugin     │   │
│ │                                                           │   │
│ │ Config maintainer declares deps when enabling plugins    │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Build Process (docker-build skill)                              │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ 1. Clone config repos                                     │   │
│ │ 2. Copy dependencies/ from master config                 │   │
│ │ 3. Merge dependencies/ from project config               │   │
│ │ 4. Generate final manifests in build_configs/            │   │
│ │ 5. Docker build with dependency installation layers       │   │
│ │                                                           │   │
│ │ No plugin scanning - config repos own dependency specs   │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Docker Image (immutable)                                        │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ /app/                                                     │   │
│ │ ├── template_user/.claude/  ← Master config              │   │
│ │ ├── .claude/                ← Project config             │   │
│ │ ├── plugins/                ← Baked plugins              │   │
│ │ └── .dependency-manifest.json ← Installed packages list  │   │
│ │                                                           │   │
│ │ All dependencies installed:                               │   │
│ │ ✓ Python packages (pip)                                   │   │
│ │ ✓ Node.js packages (npm -g)                               │   │
│ │ ✓ System packages (apt)                                   │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Runtime (Ray Containerized Actor)                               │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Agent reads .dependency-manifest.json                     │   │
│ │ Agent understands immutable environment                   │   │
│ │ Agent works with available tools/packages                 │   │
│ │ Agent sends improvement suggestions to Kodosumi           │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Plugin Documentation (SKILL.md)

**Location**: `{plugin_root}/skills/{skill_name}/SKILL.md`

**Purpose**: Document runtime requirements in skill frontmatter

**Example**:
```markdown
---
title: Page Identifier
description: Identify and analyze web pages from a domain
version: 1.0.0
dependencies:
  python:
    - beautifulsoup4>=4.12.0
    - lxml>=4.9.0
  nodejs:
    - docx: ^8.5.0
    - puppeteer: ^21.0.0
  system:
    - chromium
    - chromium-driver
---

# Page Identifier Skill

This skill identifies and analyzes web pages...

## Requirements

This skill requires the following dependencies to be installed in the container:
- Python: beautifulsoup4, lxml (for HTML parsing)
- Node.js: docx (for Word document generation), puppeteer (for browser automation)
- System: chromium, chromium-driver (for headless browsing)

Ensure these are declared in your config repository's `dependencies/` directory.
```

**Note**: The frontmatter is for documentation only. Config repositories are responsible for declaring actual dependencies.

### 2. Config Repository Dependencies

**Location**: `{config_repo}/dependencies/`

**Structure**:
```
cc-master-agent-config/
├── .claude/
│   ├── settings.json
│   └── CLAUDE.md
└── dependencies/
    ├── requirements.txt      # Python packages (pip format)
    ├── package.json          # Node.js packages (npm format)
    ├── system-packages.txt   # APT packages (one per line)
    └── README.md             # Documentation

cc-example-agent-config/
├── .claude/
│   ├── settings.json
│   └── CLAUDE.md
└── dependencies/
    ├── requirements.txt      # Additional/override Python packages
    ├── package.json          # Additional/override Node.js packages
    └── system-packages.txt   # Additional APT packages
```

**Purpose**:
- **Manual overrides**: Config-specific dependencies not tied to plugins
- **Version pinning**: Lock specific versions for stability
- **Aggregation base**: Starting point for build system to merge plugin deps

**Example** (`dependencies/README.md`):
```markdown
# Master Agent Config Dependencies

This directory contains all runtime dependencies for enabled plugins.

## Plugin: page-identifier
Enabled in: `.claude/settings.json`

**Python**:
- beautifulsoup4>=4.12.0 (HTML parsing)
- lxml>=4.9.0 (XML/HTML processing)

**Node.js**:
- docx@^8.5.0 (Word document generation)
- puppeteer@^21.0.0 (browser automation)

**System**:
- chromium (headless browser)
- chromium-driver (browser driver)

## Plugin: master-core
No additional dependencies

## Base Requirements
- Python: claude-agent-sdk, kodosumi, ray (installed in Dockerfile)
- Node.js: @anthropic-ai/claude-code (installed in Dockerfile)
```

**Example** (`dependencies/package.json`):
```json
{
  "name": "cc-master-agent-runtime",
  "version": "1.0.0",
  "description": "Runtime dependencies for master agent config",
  "dependencies": {
    "docx": "^8.5.0",
    "puppeteer": "^21.0.0"
  }
}
```

**Example** (`dependencies/requirements.txt`):
```
# page-identifier plugin
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Add other plugin dependencies below
```

### 3. Build System Enhancements

**Location**: `claude-agent-sdk` plugin → `docker-build` skill → `scripts/build.sh`

**New Steps**:

```bash
#!/bin/bash
# Enhanced build.sh with dependency merging

# ... existing clone logic ...

# NEW: Merge dependencies from config repos
echo "Merging dependencies from config repositories..."

# 1. Create build directory for dependencies
mkdir -p build_configs/dependencies

# 2. Start with master config dependencies (if they exist)
if [ -d "$MASTER_CONFIG_DIR/dependencies" ]; then
  echo "  Copying master config dependencies..."
  cp "$MASTER_CONFIG_DIR/dependencies/requirements.txt" build_configs/dependencies/requirements.txt 2>/dev/null || touch build_configs/dependencies/requirements.txt
  cp "$MASTER_CONFIG_DIR/dependencies/package.json" build_configs/dependencies/package.json 2>/dev/null || echo '{"name":"runtime","version":"1.0.0","dependencies":{}}' > build_configs/dependencies/package.json
  cp "$MASTER_CONFIG_DIR/dependencies/system-packages.txt" build_configs/dependencies/system-packages.txt 2>/dev/null || touch build_configs/dependencies/system-packages.txt
else
  echo "  No master config dependencies/ directory found, using empty manifests"
  touch build_configs/dependencies/requirements.txt
  echo '{"name":"runtime","version":"1.0.0","dependencies":{}}' > build_configs/dependencies/package.json
  touch build_configs/dependencies/system-packages.txt
fi

# 3. Merge project config dependencies (if they exist)
if [ -d "$PROJECT_CONFIG_DIR/dependencies" ]; then
  echo "  Merging project config dependencies..."

  # Append Python packages
  if [ -f "$PROJECT_CONFIG_DIR/dependencies/requirements.txt" ]; then
    cat "$PROJECT_CONFIG_DIR/dependencies/requirements.txt" >> build_configs/dependencies/requirements.txt
  fi

  # Merge Node.js packages (project overrides master)
  if [ -f "$PROJECT_CONFIG_DIR/dependencies/package.json" ]; then
    jq -s '.[0].dependencies + .[1].dependencies | {name: "runtime", version: "1.0.0", dependencies: .}' \
      build_configs/dependencies/package.json \
      "$PROJECT_CONFIG_DIR/dependencies/package.json" > /tmp/merged-package.json
    mv /tmp/merged-package.json build_configs/dependencies/package.json
  fi

  # Append system packages
  if [ -f "$PROJECT_CONFIG_DIR/dependencies/system-packages.txt" ]; then
    cat "$PROJECT_CONFIG_DIR/dependencies/system-packages.txt" >> build_configs/dependencies/system-packages.txt
  fi
fi

# 4. Deduplicate and sort (keep latest version if duplicates)
sort -u build_configs/dependencies/requirements.txt -o build_configs/dependencies/requirements.txt
sort -u build_configs/dependencies/system-packages.txt -o build_configs/dependencies/system-packages.txt

# 5. Generate dependency manifest for runtime awareness
cat > build_configs/.dependency-manifest.json <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source": "Config repositories (master + project)",
  "python_packages": $(cat build_configs/dependencies/requirements.txt | jq -R -s -c 'split("\n") | map(select(length > 0 and (startswith("#") | not)))'),
  "nodejs_packages": $(jq -c '.dependencies | keys' build_configs/dependencies/package.json),
  "system_packages": $(cat build_configs/dependencies/system-packages.txt | jq -R -s -c 'split("\n") | map(select(length > 0))')
}
EOF

echo "  Dependencies merged successfully"
echo "  Python packages: $(cat build_configs/dependencies/requirements.txt | grep -v '^#' | grep -v '^$' | wc -l)"
echo "  Node.js packages: $(jq '.dependencies | keys | length' build_configs/dependencies/package.json)"
echo "  System packages: $(cat build_configs/dependencies/system-packages.txt | grep -v '^$' | wc -l)"

# ... continue with docker build ...
```

### 4. Dockerfile Enhancements

**Location**: `cc-hitl-template/Dockerfile`

**Changes**:

```dockerfile
# ... existing base image and Node.js setup ...

# NEW: Copy aggregated dependencies
COPY build_configs/dependencies/system-packages.txt /tmp/system-packages.txt
COPY build_configs/dependencies/requirements.txt /tmp/requirements.txt
COPY build_configs/dependencies/package.json /tmp/package.json

# NEW: Install system packages
RUN if [ -s /tmp/system-packages.txt ]; then \
      apt-get update && \
      xargs -a /tmp/system-packages.txt apt-get install -y && \
      apt-get clean && rm -rf /var/lib/apt/lists/*; \
    fi

# UPDATED: Install Python dependencies from aggregated manifest
RUN if [ -s /tmp/requirements.txt ]; then \
      pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi

# NEW: Install Node.js dependencies globally
RUN if [ -s /tmp/package.json ]; then \
      cd /tmp && npm install -g $(jq -r '.dependencies | keys[]' package.json); \
    fi

# ... existing config and plugin copy ...

# NEW: Copy dependency manifest for runtime awareness
COPY build_configs/.dependency-manifest.json /app/.dependency-manifest.json

# ... rest of Dockerfile ...
```

### 5. Agent Runtime Awareness

**Location**: `cc-master-agent-config/.claude/CLAUDE.md`

**New Section**:

```markdown
## Immutable Container Environment

### Critical Understanding

You are running in an **immutable Docker container**. This has important implications:

1. **No Runtime Installations**
   - You CANNOT install packages via pip, npm, apt, or any package manager
   - All required dependencies are baked into the container at build time
   - Attempting installations will fail with permission errors or missing network

2. **Available Dependencies**
   - All installed packages are listed in `/app/.dependency-manifest.json`
   - You can read this file to check what's available
   - Use only tools and libraries present in the manifest

3. **Working with Limitations**
   - If a task requires a missing package, explain the limitation clearly
   - Suggest alternative approaches using available tools
   - If no workaround exists, use the Improvement Suggestion pattern below

### Improvement Suggestion Pattern

When you identify that a task could be better accomplished with additional dependencies:

```python
# DO NOT attempt installation - instead, send structured feedback

await tracer.markdown("""
## 🔧 Dependency Improvement Suggestion

**Task**: {brief description of what you're trying to do}

**Missing Dependencies**:
- `package-name` (type: python/nodejs/system)
  - Purpose: {why this is needed}
  - Alternative: {current workaround if any}
  - Impact: {what would improve with this package}

**To Add This Dependency**:
1. Add to `dependencies.json` in the relevant plugin
2. Or add to `dependencies/` in the config repository
3. Rebuild the container image
4. Redeploy with `/cc-deploy`

**Current Workaround**: {explain what you'll do instead}
""")
```

**Example**:
```markdown
## 🔧 Dependency Improvement Suggestion

**Task**: Generate Word document report for page analysis

**Missing Dependencies**:
- `docx` (type: nodejs)
  - Purpose: Generate professional .docx reports with formatting
  - Alternative: Currently generating markdown reports only
  - Impact: Users need Word format for business workflows

**To Add This Dependency**:
1. Add `"docx": "^8.5.0"` to `plugins/page-identifier/dependencies.json`
2. Rebuild container: `/cc-deploy` will detect the change
3. Next execution will have Word export capability

**Current Workaround**: Generating detailed markdown report instead
```

### Checking Available Dependencies

```bash
# List all installed Python packages
pip list

# List all global npm packages
npm list -g --depth=0

# Check if specific package exists
python -c "import package_name" && echo "Available" || echo "Not installed"
node -e "require('package-name')" && echo "Available" || echo "Not installed"

# Read dependency manifest
cat /app/.dependency-manifest.json | jq '.python_packages'
```

### Best Practices

1. **Check Before Using**: Verify packages exist before attempting to import
2. **Graceful Degradation**: Provide fallback approaches when dependencies missing
3. **Clear Communication**: Explain limitations and workarounds to users
4. **Suggest Improvements**: Use the pattern above to recommend additions
5. **Document Assumptions**: Note which dependencies your skills require in SKILL.md
```

### 6. Kodosumi Message Enhancement

**Location**: `cc-hitl-template/claude_hitl_template/query.py`

**New Helper**:

```python
async def send_improvement_suggestion(
    tracer: Tracer,
    task: str,
    missing_deps: list[dict],
    workaround: str
) -> None:
    """
    Send structured improvement suggestion to Kodosumi admin panel.

    Args:
        tracer: Kodosumi tracer
        task: Brief description of the task
        missing_deps: List of {name, type, purpose, impact}
        workaround: Current approach without the dependency
    """

    deps_markdown = "\n".join([
        f"- `{dep['name']}` (type: {dep['type']})\n"
        f"  - Purpose: {dep['purpose']}\n"
        f"  - Impact: {dep['impact']}"
        for dep in missing_deps
    ])

    await tracer.markdown(f"""
## 🔧 Dependency Improvement Suggestion

**Task**: {task}

**Missing Dependencies**:
{deps_markdown}

**To Add These Dependencies**:
1. Update relevant `dependencies.json` or config repo `dependencies/`
2. Rebuild container: `/cc-deploy` will detect changes
3. Redeploy to get new capabilities

**Current Workaround**: {workaround}

---
*This is an automated suggestion generated by the Claude agent to improve future capabilities.*
    """)
```

---

## Implementation Plan

### Phase 1: Plugin Documentation (cc-marketplace-*)

**Repositories**: `cc-marketplace-agents`, `cc-marketplace-developers`

**Tasks**:
1. Document dependencies in SKILL.md frontmatter (documentation only)
2. Add "Requirements" section to each SKILL.md explaining what needs to be installed
3. Update marketplace README to explain dependency documentation pattern
4. No schema validation needed (dependencies live in config repos, not plugins)

**Deliverables**:
- [ ] Updated SKILL.md files with dependency documentation
- [ ] `docs/PLUGIN-GUIDELINES.md` explaining dependency documentation
- [ ] Updated marketplace `README.md`

### Phase 2: Config Repositories (cc-*-agent-config)

**Repositories**: `cc-master-agent-config`, `cc-example-agent-config`

**Tasks**:
1. Create `dependencies/` directory structure
2. Add initial dependency files (may be empty)
3. Update `.claude/CLAUDE.md` with immutable environment documentation
4. Add dependency management documentation to README

**Deliverables**:
- [ ] `dependencies/requirements.txt`
- [ ] `dependencies/package.json`
- [ ] `dependencies/system-packages.txt`
- [ ] `dependencies/README.md`
- [ ] Updated `.claude/CLAUDE.md` with immutable container section
- [ ] Updated repo README with dependency guidelines

### Phase 3: Build System (docker-build skill)

**Repository**: `cc-marketplace-developers` → `plugins/claude-agent-sdk/skills/docker-build`

**Tasks**:
1. Enhance `scripts/build.sh` with dependency aggregation logic
2. Add dependency manifest generation
3. Add validation and conflict detection
4. Update skill documentation
5. Add tests for aggregation logic

**Deliverables**:
- [ ] Updated `scripts/build.sh` with aggregation
- [ ] `scripts/aggregate-dependencies.sh` (helper script)
- [ ] `scripts/validate-dependencies.sh` (validation script)
- [ ] Updated `SKILL.md` with dependency flow documentation
- [ ] Test fixtures for aggregation

### Phase 4: Template (cc-hitl-template)

**Repository**: `cc-hitl-template`

**Tasks**:
1. Update `Dockerfile` with dependency installation layers
2. Add `send_improvement_suggestion()` helper to `query.py`
3. Update `CLAUDE.md` with immutable environment reference
4. Add dependency checking examples to docs
5. Update deployment agent to detect dependency changes

**Deliverables**:
- [ ] Updated `Dockerfile`
- [ ] Enhanced `claude_hitl_template/query.py`
- [ ] Updated `CLAUDE.md`
- [ ] New `docs/DEPENDENCY-MANAGEMENT.md`
- [ ] Updated deployment agent logic
- [ ] This spec document in `specs/`

### Phase 5: Testing & Documentation

**All Repositories**

**Tasks**:
1. End-to-end test with page-identifier requiring docx
2. Test conflict resolution (duplicate deps with different versions)
3. Test optional dependencies
4. Document common patterns
5. Create troubleshooting guide

**Deliverables**:
- [ ] E2E test scenario documentation
- [ ] Conflict resolution examples
- [ ] Common patterns guide
- [ ] Troubleshooting guide
- [ ] Video walkthrough (optional)

---

## Rollout Strategy

### Stage 1: Pilot (Week 1)

- Implement in cc-marketplace-agents (page-identifier only)
- Implement in cc-master-agent-config
- Update docker-build skill
- Test with single plugin

### Stage 2: Expand (Week 2)

- Add dependencies.json to all existing plugins
- Update cc-example-agent-config
- Full end-to-end testing

### Stage 3: Deploy (Week 3)

- Update production deployments
- Monitor for issues
- Gather feedback

### Stage 4: Document & Refine (Week 4)

- Complete documentation
- Address edge cases
- Create tutorials

---

## Edge Cases & Considerations

### Version Conflicts

**Scenario**: Plugin A requires `requests>=2.28.0`, Plugin B requires `requests<2.27.0`

**Resolution**:
1. Build system detects conflict during aggregation
2. Logs warning with conflict details
3. Build fails with clear error message
4. User must resolve by:
   - Updating plugin requirements
   - Disabling conflicting plugin
   - Overriding in config repo `dependencies/`

### Optional Dependencies

**Scenario**: Plugin works with or without a package (degraded functionality)

**Solution**:
- Mark as optional in `dependencies.json`
- Plugin must gracefully detect presence at runtime
- Document fallback behavior in SKILL.md

### Large Binary Dependencies

**Scenario**: Chromium, Playwright, heavy ML models

**Solution**:
- Document size impact in dependencies.json
- Consider multi-stage builds to minimize final image
- Optionally create specialized base images for heavy deps

### Rapid Development

**Scenario**: Developer frequently adding/removing packages during development

**Solution**:
- Use local `dependencies/` overrides in config repo
- Quick rebuild workflow: edit → `/cc-deploy` → test
- Don't commit to dependencies.json until stabilized

---

## Success Metrics

1. **Zero Runtime Installation Attempts**: Agents never try pip/npm install
2. **Clear Error Messages**: 100% of dependency errors include improvement suggestions
3. **Build Time**: Dependency aggregation adds <30s to build time
4. **Image Size**: Incremental growth proportional to actual dependencies (<500MB for typical plugin set)
5. **Developer Experience**: Adding new plugin dependencies takes <5 minutes

---

## Future Enhancements

1. **Dependency Caching**: Cache pip/npm downloads between builds
2. **Version Pinning Tools**: Automated dependency lock file generation
3. **Security Scanning**: Integrate Snyk or similar for vulnerability detection
4. **Dependency Analysis**: Dashboard showing which plugins contribute which deps
5. **Smart Suggestions**: Agent AI analyzes task and suggests specific missing packages

---

## References

- Docker Multi-stage Builds: https://docs.docker.com/build/building/multi-stage/
- pip requirements.txt format: https://pip.pypa.io/en/stable/reference/requirements-file-format/
- npm package.json: https://docs.npmjs.com/cli/v10/configuring-npm/package-json
- Claude Agent SDK: https://github.com/anthropics/claude-agent-sdk (internal)
- Kodosumi Documentation: (internal)

---

## Approval & Sign-off

- [ ] Architecture Review
- [ ] Security Review
- [ ] DevOps Review
- [ ] Documentation Review
- [ ] Implementation Approved

**Document Owner**: Claude HITL Template Team
**Last Updated**: 2025-11-06
