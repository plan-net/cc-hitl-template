# Template Repository Changes for Immutable Container Dependencies

**Repository**: `cc-hitl-template`
**Related Spec**: `specs/immutable-container-dependencies.md`
**Date**: 2025-11-06

---

## Overview

This document outlines the specific changes needed in the `cc-hitl-template` repository to support the immutable container dependencies system. These changes enable automatic dependency installation from config repositories while maintaining container immutability.

---

## Changes Required

### 1. Dockerfile Enhancements

**File**: `Dockerfile`

**Current State**:
- Hardcoded Python packages (`claude-agent-sdk`, `kodosumi`, etc.)
- Node.js 18 and Claude CLI installed
- No dependency manifest generation

**Required Changes**:

```dockerfile
# ... existing base image and Node.js setup (lines 1-48) ...

# NEW: Build args for config paths (if not already present)
ARG MASTER_CONFIG_PATH=template_user/.claude
ARG PROJECT_CONFIG_PATH=project/.claude

# NEW: Copy aggregated dependencies from build_configs/
COPY build_configs/dependencies/system-packages.txt /tmp/system-packages.txt
COPY build_configs/dependencies/requirements.txt /tmp/requirements.txt
COPY build_configs/dependencies/package.json /tmp/package.json

# NEW: Install system packages (if any declared)
RUN if [ -s /tmp/system-packages.txt ]; then \
      apt-get update && \
      xargs -a /tmp/system-packages.txt apt-get install -y && \
      apt-get clean && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "No system packages to install"; \
    fi

# UPDATED: Install base Python dependencies + config repo dependencies
RUN pip install --no-cache-dir \
    claude-agent-sdk>=0.1.6 \
    kodosumi>=1.0.0 \
    python-dotenv>=1.1.0 \
    pytest>=8.4.1

# NEW: Install additional Python dependencies from config repos
RUN if [ -s /tmp/requirements.txt ]; then \
      pip install --no-cache-dir -r /tmp/requirements.txt; \
    else \
      echo "No additional Python packages to install"; \
    fi

# NEW: Install Node.js dependencies globally from config repos
RUN if [ -s /tmp/package.json ] && [ "$(jq '.dependencies | length' /tmp/package.json)" -gt 0 ]; then \
      cd /tmp && \
      for pkg in $(jq -r '.dependencies | to_entries[] | "\(.key)@\(.value)"' package.json); do \
        npm install -g "$pkg"; \
      done; \
    else \
      echo "No Node.js packages to install"; \
    fi

# ... existing config and plugin copy (lines 59-77) ...

# NEW: Copy dependency manifest for runtime awareness
COPY build_configs/.dependency-manifest.json /app/.dependency-manifest.json

# ... rest of Dockerfile unchanged ...
```

**Key Points**:
- Conditional installation (only if files exist and have content)
- Base packages (claude-agent-sdk, etc.) always installed
- Config repo dependencies installed on top
- Manifest copied for runtime introspection

---

### 2. Update CLAUDE.md

**File**: `CLAUDE.md`

**Location**: After "Quick Troubleshooting" section, before final line

**New Section to Add**:

```markdown
## Immutable Container Environment

### Understanding Container Immutability

**CRITICAL**: Containerized agents run in immutable Docker environments.

**What this means**:
- ✗ **Cannot install** packages via pip, npm, apt at runtime
- ✗ **No write access** to system directories or package managers
- ✓ **Can use** any packages baked into the container at build time
- ✓ **Can check** available packages via `/app/.dependency-manifest.json`

**All runtime dependencies must be declared in config repositories before building the container.**

### Dependency Manifest

Every container includes `.dependency-manifest.json` listing installed packages:

```bash
# Check what's available in your container
cat /app/.dependency-manifest.json | jq '.'

# List installed Python packages
pip list

# List installed Node.js packages
npm list -g --depth=0
```

**Example manifest**:
```json
{
  "timestamp": "2025-11-06T10:30:00Z",
  "source": "Config repositories (master + project)",
  "python_packages": ["beautifulsoup4>=4.12.0", "lxml>=4.9.0"],
  "nodejs_packages": ["docx", "puppeteer"],
  "system_packages": ["chromium", "chromium-driver"]
}
```

### Working with Missing Dependencies

**If a skill/task requires a package not in the manifest**:

1. **DO NOT** attempt installation (will fail)
2. **Check alternatives** using available packages
3. **Communicate clearly** to the user about the limitation
4. **Suggest addition** for future container builds

**Communication Pattern**:
```markdown
⚠️ **Dependency Limitation**

**Task**: Generate Word document report

**Missing Package**: `docx` (Node.js package for .docx generation)

**Current Approach**: Generating Markdown report instead

**To Add This Capability**:
1. Add `"docx": "^8.5.0"` to config repo's `dependencies/package.json`
2. Rebuild container: Run `/cc-deploy` (will detect dependency change)
3. Next execution will have Word export capability

**Would you like me to proceed with the Markdown report?**
```

### Best Practices for Agents

1. **Check Before Using**: Verify packages exist before importing
   ```python
   try:
       import beautifulsoup4
       has_bs4 = True
   except ImportError:
       has_bs4 = False
   ```

2. **Graceful Degradation**: Offer alternatives when deps missing
   ```python
   if has_docx:
       generate_word_report()
   else:
       generate_markdown_report()
       suggest_adding_docx_dependency()
   ```

3. **Clear Communication**: Explain what's possible vs. what's not

4. **Suggest Improvements**: Help users understand how to add capabilities

### For Template Users

**Adding new dependencies**:

See: `specs/immutable-container-dependencies.md` for complete system documentation

**Quick steps**:
1. Edit config repo's `dependencies/` files (requirements.txt, package.json, etc.)
2. Commit and push changes
3. Run `/cc-deploy` to rebuild container with new dependencies
4. Test with new capabilities available

---
```

**Where to add**: Insert after line 651 (after "For comprehensive solutions" link, before final "This is a Claude Code first template" line)

---

### 3. Add Kodosumi Helper Function

**File**: `claude_hitl_template/query.py`

**Location**: After existing imports, before `app = ServeAPI()`

**New Function**:

```python
async def send_dependency_suggestion(
    tracer: Tracer,
    task: str,
    missing_packages: list[dict],
    current_approach: str,
    ask_user: bool = True
) -> dict | None:
    """
    Send structured dependency improvement suggestion to user via Kodosumi.

    Args:
        tracer: Kodosumi tracer for sending messages
        task: Brief description of what you're trying to accomplish
        missing_packages: List of dicts with keys: name, type, purpose
        current_approach: What you'll do instead without these packages
        ask_user: If True, ask user if they want to proceed with workaround

    Returns:
        User response if ask_user=True, else None

    Example:
        response = await send_dependency_suggestion(
            tracer=tracer,
            task="Generate Word document report",
            missing_packages=[
                {
                    "name": "docx",
                    "type": "nodejs",
                    "purpose": "Generate .docx files with formatting"
                }
            ],
            current_approach="Generate Markdown report instead",
            ask_user=True
        )
    """
    # Build package list
    pkg_list = "\n".join([
        f"- **{pkg['name']}** ({pkg['type']}): {pkg['purpose']}"
        for pkg in missing_packages
    ])

    # Create dependency addition instructions
    instructions = []
    for pkg in missing_packages:
        if pkg['type'] == 'python':
            instructions.append(f"   - Add `{pkg['name']}` to `dependencies/requirements.txt`")
        elif pkg['type'] == 'nodejs':
            instructions.append(f"   - Add `\"{pkg['name']}\": \"^X.Y.Z\"` to `dependencies/package.json`")
        elif pkg['type'] == 'system':
            instructions.append(f"   - Add `{pkg['name']}` to `dependencies/system-packages.txt`")

    instruction_text = "\n".join(instructions)

    message = f"""
## ⚠️ Dependency Limitation

**Task**: {task}

**Missing Packages**:
{pkg_list}

**To Add These Packages**:
1. Edit your config repository's `dependencies/` directory:
{instruction_text}
2. Commit and push changes
3. Run `/cc-deploy` to rebuild container
4. Next execution will have these capabilities

**Current Approach**: {current_approach}

---
*This is an automated suggestion to help improve future capabilities.*
    """

    await tracer.markdown(message.strip())

    if ask_user:
        # Ask if user wants to proceed with workaround
        response = await tracer.lease(
            "dependency-workaround-approval",
            F.Model(
                F.Markdown(f"### Proceed with {current_approach}?"),
                F.Radio(
                    label="Your choice",
                    name="proceed",
                    options=[
                        {"label": "Yes, use workaround", "value": "yes"},
                        {"label": "No, I'll add dependencies first", "value": "no"}
                    ]
                ),
                F.Submit("Continue")
            )
        )
        return response
    return None
```

**Usage in agent.py** (for agents to call):

```python
# In ClaudeSessionActor or query.py orchestration
if not has_required_package:
    response = await send_dependency_suggestion(
        tracer=tracer,
        task="Generate Word document",
        missing_packages=[{"name": "docx", "type": "nodejs", "purpose": "Create .docx files"}],
        current_approach="Generate Markdown report",
        ask_user=True
    )

    if response.get("proceed") == "no":
        await tracer.markdown("Please add the dependencies and rebuild, then try again.")
        return
```

---

### 4. Documentation Updates

**File**: `docs/DEPENDENCY-MANAGEMENT.md` (NEW)

**Content**: Create comprehensive guide for users on managing dependencies

**Sections**:
1. Overview of immutable containers
2. How to add Python packages
3. How to add Node.js packages
4. How to add system packages
5. Understanding the dependency manifest
6. Troubleshooting common issues
7. Version conflict resolution
8. Examples for common use cases

**File**: `README.md`

**Updates**:
- Add link to `specs/immutable-container-dependencies.md` in Architecture section
- Add link to `docs/DEPENDENCY-MANAGEMENT.md` in Documentation section
- Mention immutable container pattern in Features section

---

### 5. Build Configuration Structure

**New Directory**: `build_configs/` (created by docker-build skill, gitignored)

**Expected contents after build**:
```
build_configs/
├── .dependency-manifest.json      # Runtime manifest
├── dependencies/
│   ├── requirements.txt           # Merged Python packages
│   ├── package.json               # Merged Node.js packages
│   └── system-packages.txt        # Merged system packages
└── plugins/                        # Copied marketplace plugins
    ├── cc-marketplace-developers/
    └── cc-marketplace-agents/
```

**Update**: `.gitignore`

```gitignore
# Existing entries...

# Build artifacts
build_configs/
.dependency-manifest.json
```

---

## Testing Plan

### Local Testing

1. **Empty dependencies** (baseline):
   ```bash
   # Create empty dependency files in config repos
   # Build and verify container works with just base packages
   ```

2. **Python packages**:
   ```bash
   # Add beautifulsoup4 to requirements.txt
   # Build and verify: pip list | grep beautifulsoup4
   ```

3. **Node.js packages**:
   ```bash
   # Add docx to package.json
   # Build and verify: npm list -g | grep docx
   ```

4. **System packages**:
   ```bash
   # Add chromium to system-packages.txt
   # Build and verify: which chromium
   ```

5. **Dependency manifest**:
   ```bash
   # Verify /app/.dependency-manifest.json exists and is accurate
   # Check all declared packages are listed
   ```

### Integration Testing

1. Enable page-identifier plugin
2. Add its dependencies to master config
3. Build container
4. Run page-identifier skill
5. Verify docx generation works
6. Remove docx from dependencies
7. Rebuild and verify graceful degradation

---

## Migration Path

### For Existing Deployments

1. **Create dependency directories in config repos**:
   ```bash
   cd cc-master-agent-config
   mkdir -p dependencies
   touch dependencies/{requirements.txt,package.json,system-packages.txt}
   git add dependencies/
   git commit -m "Initialize dependencies structure"
   ```

2. **Document current implicit dependencies**:
   - Review SKILL.md files in enabled plugins
   - Add their requirements to config repo dependencies/
   - Add README.md documenting each plugin's needs

3. **Update docker-build skill** (in cc-marketplace-developers)

4. **Update Dockerfile** in template

5. **Rebuild and test**:
   ```bash
   /cc-deploy
   # Verify all skills still work
   ```

6. **Add dependency checking to agents**:
   - Update CLAUDE.md in master config
   - Add send_dependency_suggestion helper
   - Test with intentionally missing dependency

---

## Rollout Checklist

### Template Repo (cc-hitl-template)

- [ ] Update Dockerfile with dependency installation layers
- [ ] Add send_dependency_suggestion() to query.py
- [ ] Update CLAUDE.md with immutable container section
- [ ] Create docs/DEPENDENCY-MANAGEMENT.md
- [ ] Update README.md with links
- [ ] Update .gitignore for build_configs/
- [ ] Commit and push changes
- [ ] Tag as v1.1.0 (or appropriate version)

### Config Repos (cc-master-agent-config, cc-example-agent-config)

- [ ] Create dependencies/ directory structure
- [ ] Add initial dependency files (may be empty)
- [ ] Document page-identifier requirements (if enabled)
- [ ] Update .claude/CLAUDE.md with runtime instructions
- [ ] Commit and push

### Build System (cc-marketplace-developers)

- [ ] Update docker-build skill's build.sh
- [ ] Test dependency merging logic
- [ ] Update SKILL.md documentation

### Testing

- [ ] Build with empty dependencies
- [ ] Build with sample Python packages
- [ ] Build with sample Node.js packages
- [ ] Verify manifest generation
- [ ] Test page-identifier with docx
- [ ] Test graceful degradation

### Documentation

- [ ] Share specs/immutable-container-dependencies.md with all repos
- [ ] Update cross-repo README files
- [ ] Create tutorial video (optional)

---

## Success Criteria

1. ✅ Container builds successfully with dependencies from config repos
2. ✅ Dependency manifest accurately reflects installed packages
3. ✅ Agents can introspect available packages
4. ✅ Clear user feedback when dependencies missing
5. ✅ No runtime installation attempts
6. ✅ Existing skills continue to work
7. ✅ New dependencies can be added in <5 minutes

---

## Open Questions

1. **Version conflict resolution**: How to handle when master and project specify different versions?
   - **Proposed**: Project wins (last merged)
   - **Alternative**: Build fails with clear error

2. **Dependency validation**: Should build fail if declared dep fails to install?
   - **Proposed**: Yes, fail fast with clear error
   - **Rationale**: Better than runtime failures

3. **Optional dependencies**: Support for "nice to have" packages?
   - **Proposed**: Phase 2 feature
   - **Workaround**: Agents check availability and degrade gracefully

---

## Timeline

- **Week 1**: Template repo changes (Dockerfile, query.py, CLAUDE.md)
- **Week 2**: Config repo setup (dependencies/ directories)
- **Week 3**: Build system updates (docker-build skill)
- **Week 4**: Testing, documentation, rollout

---

## References

- Main spec: `specs/immutable-container-dependencies.md`
- Docker multi-stage builds: https://docs.docker.com/build/building/multi-stage/
- pip requirements format: https://pip.pypa.io/en/stable/reference/requirements-file-format/
- npm package.json: https://docs.npmjs.com/cli/v10/configuring-npm/package-json

---

**Last Updated**: 2025-11-06
**Status**: Ready for Implementation
