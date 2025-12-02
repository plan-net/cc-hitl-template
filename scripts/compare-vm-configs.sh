#!/bin/bash
# Compare two VM configuration exports to identify differences
# Usage: bash scripts/compare-vm-configs.sh working-config.txt broken-config.txt

if [ $# -ne 2 ]; then
    echo "Usage: $0 <working-config.txt> <broken-config.txt>"
    exit 1
fi

WORKING_CONFIG="$1"
BROKEN_CONFIG="$2"

if [ ! -f "$WORKING_CONFIG" ]; then
    echo "Error: Working config file not found: $WORKING_CONFIG"
    exit 1
fi

if [ ! -f "$BROKEN_CONFIG" ]; then
    echo "Error: Broken config file not found: $BROKEN_CONFIG"
    exit 1
fi

echo "=========================================="
echo "VM Configuration Comparison"
echo "=========================================="
echo ""
echo "Comparing:"
echo "  Working: $WORKING_CONFIG"
echo "  Broken:  $BROKEN_CONFIG"
echo ""

# Function to extract section from config file
extract_section() {
    local file="$1"
    local section="$2"
    sed -n "/=== $section ===/,/^$/p" "$file" | grep -v "^===" | grep -v "^$"
}

# Compare key sections
sections=(
    "OS Information"
    "Architecture"
    "Python Version"
    "Container Runtime"
    "User Namespace Configuration"
    "Ray Installation"
)

for section in "${sections[@]}"; do
    echo "--- $section ---"

    working_data=$(extract_section "$WORKING_CONFIG" "$section")
    broken_data=$(extract_section "$BROKEN_CONFIG" "$section")

    if [ "$working_data" == "$broken_data" ]; then
        echo "✓ IDENTICAL"
    else
        echo "✗ DIFFERENT"
        echo ""
        echo "Working:"
        echo "$working_data"
        echo ""
        echo "Broken:"
        echo "$broken_data"
    fi
    echo ""
done

echo "=========================================="
echo "Recommendations"
echo "=========================================="
echo ""

# Check for common issues
if grep -q "Podman" "$WORKING_CONFIG" && grep -q "Docker" "$BROKEN_CONFIG"; then
    echo "⚠️  Container runtime mismatch: Working uses Podman, broken uses Docker"
    echo "   → Consider switching broken environment to Podman"
    echo ""
fi

if grep -q "Docker" "$WORKING_CONFIG" && grep -q "Podman" "$BROKEN_CONFIG"; then
    echo "⚠️  Container runtime mismatch: Working uses Docker, broken uses Podman"
    echo "   → Consider switching broken environment to Docker"
    echo "   → If using Podman, ensure user namespaces are configured"
    echo ""
fi

if grep -q "arm64" "$WORKING_CONFIG" && grep -q "x86_64" "$BROKEN_CONFIG"; then
    echo "⚠️  Architecture mismatch: Working is arm64 (Apple Silicon), broken is x86_64 (Intel)"
    echo "   → Container images must match architecture"
    echo "   → Rebuild container images on the broken system"
    echo ""
fi

working_python=$(grep -A 1 "Python Version" "$WORKING_CONFIG" | grep "Python 3" | head -1)
broken_python=$(grep -A 1 "Python Version" "$BROKEN_CONFIG" | grep "Python 3" | head -1)

if [ "$working_python" != "$broken_python" ]; then
    echo "⚠️  Python version mismatch"
    echo "   Working: $working_python"
    echo "   Broken:  $broken_python"
    echo "   → Ensure both use Python 3.12+"
    echo ""
fi

if ! grep -q "100000:65536" "$BROKEN_CONFIG"; then
    if grep -q "Podman" "$BROKEN_CONFIG"; then
        echo "⚠️  Missing user namespace configuration for Podman"
        echo "   → Run in VM:"
        echo "     sudo bash -c 'echo \$(whoami):100000:65536 >> /etc/subuid'"
        echo "     sudo bash -c 'echo \$(whoami):100000:65536 >> /etc/subgid'"
        echo "     podman system migrate"
        echo ""
    fi
fi

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Review differences above"
echo "2. Apply recommended fixes to broken environment"
echo "3. Re-export broken config after fixes: bash scripts/export-vm-config.sh > broken-config-fixed.txt"
echo "4. Compare again: bash scripts/compare-vm-configs.sh working-config.txt broken-config-fixed.txt"
echo ""
