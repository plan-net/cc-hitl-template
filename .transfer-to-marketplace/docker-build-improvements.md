# Docker Build Skill Improvements

## Critical Fix Already Applied

The docker-build skill in `cc-marketplace-developers` was updated to fix a critical bug in manifest digest extraction.

### Issue: Wrong Digest Type Extracted

**Problem**: The build script was extracting the **content digest** (`.Digest`) instead of the **manifest digest** (`.RepoDigests[0]`), causing "manifest unknown" errors when Ray tried to pull images.

**Root Cause**: Logic was backwards - trying content digest first, falling back to manifest digest.

```bash
# OLD (WRONG) - Lines 282-286 of build.sh
IMAGE_DIGEST=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{index .Digest}}' 2>/dev/null || echo "")
if [ -z "${IMAGE_DIGEST}" ]; then
  IMAGE_DIGEST=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{index .RepoDigests 0}}' 2>/dev/null | cut -d@ -f2 || echo "unknown")
fi
```

**Fix Applied**: Use manifest digest as primary source, fail if not available.

```bash
# NEW (CORRECT) - Lines 282-286 of build.sh
IMAGE_DIGEST=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{index .RepoDigests 0}}' 2>/dev/null | cut -d@ -f2 || echo "")
if [ -z "${IMAGE_DIGEST}" ]; then
  echo -e "${RED}✗ Error: Failed to get image digest from registry${NC}"
  exit 1
fi
```

**Why This Matters**:
- Content digest (`.Digest`): Platform-specific, local build hash, not available in remote registry
- Manifest digest (`.RepoDigests[0]`): Cross-platform, registry-assigned, required for `podman pull`
- Using content digest causes "manifest unknown: manifest unknown" errors in deployment

---

## Additional Improvements Needed

### 1. Multi-Platform Digest Handling

**Issue**: When an image has multiple RepoDigests (multi-platform builds), the current logic takes the first one without validation.

**Example from our debugging**:
```bash
$ podman inspect ghcr.io/plan-net/claude-hitl-worker:latest --format='{{index .RepoDigests}}'
[ghcr.io/plan-net/claude-hitl-worker@sha256:3ff580747f2a81e5fc4a0d59bfdec221d63c33c4e8faa2b30dd485396c8bc810
 ghcr.io/plan-net/claude-hitl-worker@sha256:c3c1f7b8dbcbd67b9e48f0517a3db682cf1dd4fedb6bc7f21e8e93e08f31bb84]
```

**Current Behavior**: Takes first digest blindly

**Recommended Improvement**:
```bash
# Extract all repo digests
REPO_DIGESTS=$(${CONTAINER_TOOL} inspect "${IMAGE_NAME}" --format='{{range .RepoDigests}}{{println .}}{{end}}' 2>/dev/null || echo "")

if [ -z "${REPO_DIGESTS}" ]; then
  echo -e "${RED}✗ Error: No RepoDigests found. Image must be pushed to registry first.${NC}"
  exit 1
fi

# Count digests
DIGEST_COUNT=$(echo "${REPO_DIGESTS}" | wc -l)

if [ "${DIGEST_COUNT}" -eq 1 ]; then
  # Single digest - use it
  IMAGE_DIGEST=$(echo "${REPO_DIGESTS}" | cut -d@ -f2)
  echo -e "${GREEN}✓ Single platform image digest: ${IMAGE_DIGEST}${NC}"
else
  # Multiple digests - verify each one is pullable and let user choose or pick first working
  echo -e "${YELLOW}⚠ Multiple platform digests found (${DIGEST_COUNT}):${NC}"
  echo "${REPO_DIGESTS}" | nl

  # Try each digest to find a pullable one
  for FULL_DIGEST in ${REPO_DIGESTS}; do
    DIGEST_ONLY=$(echo "${FULL_DIGEST}" | cut -d@ -f2)
    echo -e "${BLUE}Testing pullability: ${DIGEST_ONLY}${NC}"

    if ${CONTAINER_TOOL} pull "${FULL_DIGEST}" &>/dev/null; then
      IMAGE_DIGEST="${DIGEST_ONLY}"
      echo -e "${GREEN}✓ Using verified pullable digest: ${IMAGE_DIGEST}${NC}"
      break
    fi
  done

  if [ -z "${IMAGE_DIGEST}" ]; then
    echo -e "${RED}✗ Error: None of the digests are pullable from registry${NC}"
    exit 1
  fi
fi
```

**Benefits**:
- Handles multi-platform builds correctly
- Verifies digest is actually pullable from registry
- Provides clear feedback about which digest is being used
- Catches registry sync issues early

---

### 2. Post-Push Verification

**Issue**: After pushing, the skill reports a digest but doesn't verify it's actually pullable from the registry.

**Recommended Addition** (after push step):
```bash
echo -e "${BLUE}Verifying image is pullable from registry...${NC}"

# Try to pull the exact digest we just pushed
if ${CONTAINER_TOOL} pull "${IMAGE_NAME%:*}@${IMAGE_DIGEST}" &>/dev/null; then
  echo -e "${GREEN}✓ Image verified pullable from registry${NC}"
else
  echo -e "${RED}✗ Warning: Image was pushed but is not pullable by digest${NC}"
  echo -e "${YELLOW}  This may indicate a registry sync delay or authentication issue${NC}"
  echo -e "${YELLOW}  Digest: ${IMAGE_DIGEST}${NC}"
  # Don't exit - registry might just need time to sync
fi
```

**Benefits**:
- Catches registry authentication issues immediately
- Detects registry sync delays
- Confirms the digest reported to user actually works
- Prevents silent failures in deployment

---

### 3. Clear State Tracking

**Issue**: The `.last-deploy-state.json` is updated with the digest, but there's no validation that this digest matches what's in the YAML configs.

**Recommended Addition** (at end of build script):
```bash
# Report what needs to be updated
echo -e "\n${BLUE}Configuration Update Required:${NC}"
echo -e "${YELLOW}The following files must be updated with the new digest:${NC}"
echo ""
echo -e "1. ${GREEN}.env${NC}"
echo "   CONTAINER_IMAGE_URI=${IMAGE_NAME%:*}@${IMAGE_DIGEST}"
echo ""
echo -e "2. ${GREEN}data/config/claude_hitl_template.yaml${NC}"
echo "   runtime_env.env_vars.CONTAINER_IMAGE_URI: \"${IMAGE_NAME%:*}@${IMAGE_DIGEST}\""
echo ""
echo -e "${RED}⚠ Both files require LITERAL values (no variable substitution)${NC}"
echo -e "${YELLOW}Ray Serve YAML does NOT expand \${VARIABLES}${NC}"
```

**Benefits**:
- Clear instructions on what to update
- Reduces manual error in config updates
- Reminds about YAML literal value requirement
- Provides copy-paste ready values

---

## Podman User Namespace Documentation

The troubleshooting guide now includes comprehensive podman configuration documentation. This should be referenced in the docker-build skill's SKILL.md.

**Add to SKILL.md Prerequisites Section**:
```markdown
### Container Runtime Requirements

**Rootless Podman Users**: Must configure user namespaces before using this skill.

If you encounter errors like:
```
Error: potentially insufficient UIDs or GIDs available in user namespace
```

Configure subordinate UID/GID ranges:
```bash
# Replace 'username' with your actual username
sudo bash -c 'echo "username:100000:65536" >> /etc/subuid'
sudo bash -c 'echo "username:100000:65536" >> /etc/subgid'

# Apply configuration
podman system migrate

# Verify
cat /etc/subuid  # Should show: username:100000:65536
cat /etc/subgid  # Should show: username:100000:65536
```

For detailed troubleshooting, see your project's `docs/TROUBLESHOOTING.md` under "Container Runtime Issues".
```

---

## Summary of Changes

### ✅ Already Fixed (in cc-marketplace-developers plugin)
- Manifest digest extraction (use `.RepoDigests[0]` instead of `.Digest`)
- Proper error handling when digest is unavailable

### 🔄 Recommended Improvements
1. **Multi-platform digest handling**: Verify pullability when multiple digests exist
2. **Post-push verification**: Confirm image is pullable from registry
3. **Clear configuration instructions**: Show exact values to update in configs
4. **Podman prerequisites documentation**: Add user namespace setup to SKILL.md

### 📖 Documentation Improvements
- TROUBLESHOOTING.md now includes comprehensive podman setup
- Permission fixes documented (justfile automation + Dockerfile full ownership)
- Digest type differences explained (content vs manifest)

---

## Testing Checklist

When implementing these improvements, test:

- [ ] Single-platform image build and push
- [ ] Multi-platform image build and push
- [ ] Registry authentication failures
- [ ] Podman without user namespace configuration
- [ ] Docker vs Podman behavior differences
- [ ] Digest verification step with registry delays
- [ ] Config file update instructions accuracy
