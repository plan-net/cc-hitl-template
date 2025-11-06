# Dependency Management Guide

This guide explains how to manage runtime dependencies for your Claude HITL deployments using the immutable container dependency system.

---

## Table of Contents

- [Overview](#overview)
- [Understanding Immutable Containers](#understanding-immutable-containers)
- [Where Dependencies Live](#where-dependencies-live)
- [Adding Dependencies](#adding-dependencies)
- [The Dependency Manifest](#the-dependency-manifest)
- [Common Scenarios](#common-scenarios)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

The Claude HITL template uses **immutable Docker containers** where all dependencies must be declared before build time. This ensures:

- **Reproducibility**: Same container always has same packages
- **Security**: No runtime installations = smaller attack surface
- **Performance**: All packages pre-installed, no download delays
- **Clarity**: Explicit dependency declarations in config repos

**Key Principle**: If you need a package at runtime, declare it in your config repository's `dependencies/` directory.

---

## Understanding Immutable Containers

### What Can Agents Do?

✅ **Can**:
- Use any package baked into the container image
- Read `/app/.dependency-manifest.json` to check available packages
- Execute with pre-installed Python/Node.js/system tools
- Work with files in `/app/` directory

✗ **Cannot**:
- Install packages via `pip install`, `npm install`, `apt install`
- Write to system directories (`/usr/lib`, `/usr/bin`, etc.)
- Modify the container filesystem (read-only except `/app/` and `/tmp/`)

### Why Immutable?

1. **Security**: Prevents malicious package installations
2. **Reliability**: No dependency drift between runs
3. **Performance**: No installation overhead at runtime
4. **Auditability**: All dependencies explicitly declared

---

## Where Dependencies Live

Dependencies are declared in **config repositories**, not in plugins or the template:

```
cc-master-agent-config/              # Organization/team-level config
└── dependencies/
    ├── requirements.txt             # Python packages
    ├── package.json                 # Node.js packages
    ├── system-packages.txt          # APT packages
    └── README.md                    # Documentation

cc-example-agent-config/             # Project-specific config
└── dependencies/
    ├── requirements.txt             # Additional Python packages
    ├── package.json                 # Additional Node.js packages
    └── system-packages.txt          # Additional APT packages
```

**Merge Behavior**:
- Master config dependencies are installed first
- Project config dependencies are merged on top
- Project can override master package versions
- Both configs' packages are available at runtime

---

## Adding Dependencies

### Python Packages

**File**: `dependencies/requirements.txt`

**Format**: Standard pip requirements format

**Example**:
```txt
# Data processing
beautifulsoup4>=4.12.0
lxml>=4.9.0
pandas>=2.0.0

# API clients
requests>=2.28.0
httpx>=0.24.0

# Utilities
python-dateutil>=2.8.2
```

**Version Specifiers**:
- `package==1.2.3` - Exact version
- `package>=1.2.0` - Minimum version
- `package>=1.2.0,<2.0.0` - Version range
- `package` - Latest version (not recommended)

**After editing**:
```bash
cd cc-master-agent-config  # or cc-example-agent-config
git add dependencies/requirements.txt
git commit -m "Add beautifulsoup4 and lxml for HTML parsing"
git push
```

Then rebuild container: `/cc-deploy`

### Node.js Packages

**File**: `dependencies/package.json`

**Format**: Standard npm package.json dependencies section

**Example**:
```json
{
  "name": "my-agent-runtime",
  "version": "1.0.0",
  "description": "Runtime dependencies for my agent",
  "dependencies": {
    "docx": "^8.5.0",
    "puppeteer": "^21.0.0",
    "axios": "^1.6.0",
    "cheerio": "^1.0.0-rc.12"
  }
}
```

**Version Syntax**:
- `"^1.2.3"` - Compatible with 1.x.x (recommended)
- `"~1.2.3"` - Compatible with 1.2.x
- `"1.2.3"` - Exact version
- `"*"` - Latest (not recommended)

**After editing**:
```bash
cd cc-master-agent-config
git add dependencies/package.json
git commit -m "Add docx package for Word document generation"
git push
```

Then rebuild container: `/cc-deploy`

### System Packages

**File**: `dependencies/system-packages.txt`

**Format**: One APT package name per line

**Example**:
```txt
chromium
chromium-driver
ffmpeg
imagemagick
poppler-utils
```

**Common Packages**:
- `chromium`, `chromium-driver` - Headless browser
- `ffmpeg` - Video/audio processing
- `imagemagick` - Image manipulation
- `poppler-utils` - PDF utilities (pdftotext, etc.)
- `ghostscript` - PostScript/PDF processing
- `tesseract-ocr` - OCR capabilities

**After editing**:
```bash
cd cc-master-agent-config
git add dependencies/system-packages.txt
git commit -m "Add chromium for headless browsing"
git push
```

Then rebuild container: `/cc-deploy`

### Documentation

**File**: `dependencies/README.md`

**Purpose**: Document why each dependency is needed and which plugin uses it

**Example**:
```markdown
# Runtime Dependencies

## Plugin: page-identifier
Enabled in: `.claude/settings.json`

**Python**:
- beautifulsoup4>=4.12.0 - HTML parsing for web scraping
- lxml>=4.9.0 - Fast XML/HTML processing

**Node.js**:
- docx@^8.5.0 - Generate Word document reports
- puppeteer@^21.0.0 - Headless browser automation

**System**:
- chromium - Browser for puppeteer
- chromium-driver - Browser driver

## Base Requirements
(These are always installed by the Dockerfile)
- Python: claude-agent-sdk, kodosumi, ray
- Node.js: @anthropic-ai/claude-code
```

---

## The Dependency Manifest

Every container includes `/app/.dependency-manifest.json` - a runtime inventory of installed packages.

### Viewing the Manifest

**From within container**:
```bash
cat /app/.dependency-manifest.json | jq '.'
```

**Example manifest**:
```json
{
  "timestamp": "2025-11-06T10:30:00Z",
  "source": "Config repositories (master + project)",
  "python_packages": [
    "beautifulsoup4>=4.12.0",
    "lxml>=4.9.0",
    "pandas>=2.0.0"
  ],
  "nodejs_packages": [
    "docx",
    "puppeteer",
    "axios"
  ],
  "system_packages": [
    "chromium",
    "chromium-driver",
    "ffmpeg"
  ]
}
```

### Checking Package Availability

**Python**:
```bash
pip list | grep beautifulsoup4
python -c "import beautifulsoup4; print(beautifulsoup4.__version__)"
```

**Node.js**:
```bash
npm list -g | grep docx
node -e "console.log(require('docx').version)"
```

**System**:
```bash
which chromium
chromium --version
```

---

## Common Scenarios

### Scenario 1: Adding Web Scraping Capabilities

**Goal**: Enable agents to parse HTML and scrape web pages

**Dependencies needed**:
```txt
# requirements.txt
beautifulsoup4>=4.12.0
lxml>=4.9.0
requests>=2.28.0
```

**Steps**:
1. Add packages to `cc-master-agent-config/dependencies/requirements.txt`
2. Commit and push
3. Run `/cc-deploy` to rebuild
4. Test: agents can now `import bs4` and parse HTML

### Scenario 2: Adding Word Document Generation

**Goal**: Generate .docx reports from analysis results

**Dependencies needed**:
```json
// package.json
{
  "dependencies": {
    "docx": "^8.5.0"
  }
}
```

**Steps**:
1. Add to `cc-master-agent-config/dependencies/package.json`
2. Commit and push
3. Run `/cc-deploy`
4. Test: agents can now use Node.js docx library

### Scenario 3: Adding Headless Browser

**Goal**: Enable automated browsing and screenshots

**Dependencies needed**:
```json
// package.json
{
  "dependencies": {
    "puppeteer": "^21.0.0"
  }
}
```

```txt
# system-packages.txt
chromium
chromium-driver
```

**Steps**:
1. Add both Node.js and system packages
2. Commit and push
3. Run `/cc-deploy`
4. Test: agents can launch headless Chrome

### Scenario 4: Project-Specific Dependencies

**Goal**: Add packages only for one project, not all projects using master config

**Solution**: Use project config repository

```txt
# cc-example-agent-config/dependencies/requirements.txt
# Project-specific data science libraries
scikit-learn>=1.3.0
tensorflow>=2.14.0
```

**Steps**:
1. Add to PROJECT config repo (not master)
2. Commit and push
3. Run `/cc-deploy`
4. Only this project's containers get these packages

---

## Troubleshooting

### Issue: Agent tries to install package at runtime

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied
pip install beautifulsoup4  # Fails
```

**Solution**:
1. Add package to `dependencies/requirements.txt`
2. Rebuild container with `/cc-deploy`
3. Agent can now import the package

**Prevention**: Update agent's CLAUDE.md to explain immutable environment

### Issue: Package version conflict

**Symptoms**:
```
ERROR: Package X requires Y>=2.0, but Y==1.5 is installed
```

**Solution**:
1. Check both master and project `requirements.txt`
2. Ensure compatible versions or remove conflicting specs
3. Use version ranges (`>=1.5,<2.0`) instead of exact versions

**Example fix**:
```txt
# Before (conflict)
# Master: requests>=2.28.0
# Project: requests==2.25.0

# After (compatible)
# Master: requests>=2.28.0
# Project: (remove or upgrade to >=2.28.0)
```

### Issue: Build fails with "package not found"

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement invalid-pkg
```

**Solutions**:
1. Check package name spelling
2. Verify package exists on PyPI/npm
3. Check for typos in `requirements.txt` or `package.json`
4. Use exact package names (case-sensitive for npm)

### Issue: Container size too large

**Symptoms**:
- Container image is >2GB
- Slow builds and deployments

**Solutions**:
1. Review `dependencies/README.md` - remove unused packages
2. Avoid including large ML models in system packages
3. Consider multi-stage builds for heavy dependencies
4. Use `.dockerignore` to exclude unnecessary files

### Issue: Dependency manifest not updated

**Symptoms**:
- Added packages not showing in `.dependency-manifest.json`
- Old packages still listed

**Solution**:
1. Ensure `build.sh` is merging dependencies correctly
2. Check build logs for errors
3. Verify files were committed to config repos
4. Rebuild with `/cc-deploy` (not manual docker build)

---

## Best Practices

### 1. Document Dependencies

Always update `dependencies/README.md` when adding packages:
```markdown
## Plugin: my-plugin
**Python**: requests - HTTP client for API calls
**Why**: Needed to fetch data from external APIs
```

### 2. Use Version Ranges

Prefer version ranges over exact versions:
```txt
# Good
requests>=2.28.0,<3.0.0

# Less good
requests==2.28.0
```

### 3. Group Related Packages

Organize dependencies with comments:
```txt
# Web scraping
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Data processing
pandas>=2.0.0
numpy>=1.24.0
```

### 4. Test After Adding

Always test new dependencies:
```bash
# After /cc-deploy, start a job and test
python -c "import new_package"
node -e "require('new-package')"
```

### 5. Separate Master vs Project

**Master config**: Common dependencies for all projects
**Project config**: Project-specific or experimental dependencies

This keeps master config lean and widely compatible.

### 6. Review Periodically

Every quarter, review `dependencies/`:
- Remove unused packages
- Update to latest compatible versions
- Check for security vulnerabilities

### 7. Communicate with Agents

Update config repo's `.claude/CLAUDE.md` to inform agents about:
- Immutable environment constraints
- Available packages and their purposes
- How to suggest new dependencies

---

## See Also

- **Complete specification**: [specs/immutable-container-dependencies.md](../specs/immutable-container-dependencies.md)
- **Template changes**: [specs/template-repo-changes.md](../specs/template-repo-changes.md)
- **Main documentation**: [CLAUDE.md](../CLAUDE.md#immutable-container-environment)
- **Deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Questions?** Check the troubleshooting section or consult the full specification document.
