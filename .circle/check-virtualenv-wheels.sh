#!/bin/bash
# Diagnostic script to check virtualenv bundled wheel SHA256 hashes
# This helps identify if bundled wheels are corrupted

set -e

echo "========================================"
echo "  VIRTUALENV BUNDLED WHEELS DIAGNOSTIC"
echo "========================================"
echo ""

# Check virtualenv version
echo "1. Virtualenv Version:"
/opt/stackstorm/st2/bin/python -m virtualenv --version || echo "  ERROR: Could not determine virtualenv version"
echo ""

# Find virtualenv package location
echo "2. Virtualenv Package Location:"
VENV_PKG=$(/opt/stackstorm/st2/bin/python -c "import virtualenv; print(virtualenv.__file__)" 2>/dev/null || echo "")
if [ -z "$VENV_PKG" ]; then
    echo "  ERROR: Could not locate virtualenv package"
    exit 1
fi
VENV_DIR=$(dirname "$VENV_PKG")
echo "  Package file: $VENV_PKG"
echo "  Package dir:  $VENV_DIR"
echo ""

# Find bundled wheels directory
echo "3. Bundled Wheels Directory:"
WHEELS_DIR="$VENV_DIR/seed/wheels/embed"
if [ -d "$WHEELS_DIR" ]; then
    echo "  Location: $WHEELS_DIR"
    echo "  Contents:"
    ls -lh "$WHEELS_DIR" | grep -E '\.(whl|txt)$' || echo "  No .whl or .txt files found"
else
    echo "  ERROR: Wheels directory not found at $WHEELS_DIR"
    # Try alternate location
    WHEELS_DIR="$VENV_DIR/seed/embed"
    if [ -d "$WHEELS_DIR" ]; then
        echo "  Found alternate location: $WHEELS_DIR"
    else
        echo "  ERROR: Could not find bundled wheels directory"
        exit 1
    fi
fi
echo ""

# Calculate SHA256 hashes for all wheel files
echo "4. SHA256 Hashes of Bundled Wheels:"
WHEEL_COUNT=0
while IFS= read -r wheel; do
    if [ -f "$wheel" ]; then
        WHEEL_COUNT=$((WHEEL_COUNT + 1))
        BASENAME=$(basename "$wheel")
        echo "  File: $BASENAME"

        # Calculate actual hash
        ACTUAL_HASH=$(sha256sum "$wheel" | awk '{print $1}')
        echo "    Actual SHA256: $ACTUAL_HASH"

        # Try to find expected hash in wheels.json or similar
        WHEEL_NAME="${BASENAME%.whl}"
        JSON_FILE="$WHEELS_DIR/../wheels.json"
        if [ -f "$JSON_FILE" ]; then
            EXPECTED_HASH=$(python -c "
import json
try:
    with open('$JSON_FILE') as f:
        data = json.load(f)
        for entry in data:
            if '$BASENAME' in str(entry):
                print(entry.get('sha256', 'Not found'))
                break
except:
    pass
" 2>/dev/null)
            if [ ! -z "$EXPECTED_HASH" ] && [ "$EXPECTED_HASH" != "Not found" ]; then
                echo "    Expected SHA256: $EXPECTED_HASH"
                if [ "$ACTUAL_HASH" = "$EXPECTED_HASH" ]; then
                    echo "    Status: ✓ MATCH"
                else
                    echo "    Status: ✗ MISMATCH - CORRUPTED WHEEL DETECTED!"
                fi
            fi
        fi
        echo ""
    fi
done < <(find "$WHEELS_DIR" -name "*.whl" -type f 2>/dev/null)

if [ $WHEEL_COUNT -eq 0 ]; then
    echo "  WARNING: No wheel files found in $WHEELS_DIR"
fi
echo ""

# Check virtualenv cache
echo "5. Virtualenv Cache Status:"
CACHE_DIR="${HOME}/.cache/virtualenv"
if [ -d "$CACHE_DIR" ]; then
    echo "  Cache location: $CACHE_DIR"
    CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | awk '{print $1}')
    echo "  Cache size: $CACHE_SIZE"

    WHEEL_FILES=$(find "$CACHE_DIR" -type f -name "*.whl" 2>/dev/null | wc -l)
    echo "  Cached wheel files: $WHEEL_FILES"

    if [ $WHEEL_FILES -gt 0 ]; then
        echo "  Recent cached wheels:"
        find "$CACHE_DIR" -type f -name "*.whl" -exec ls -lh {} \; 2>/dev/null | head -10
    fi
else
    echo "  No cache found at $CACHE_DIR"
fi
echo ""

# Check Python and pip versions for context
echo "6. Python Environment:"
echo "  Python: $(python --version 2>&1)"
echo "  Pip: $(pip --version 2>&1 | awk '{print $2}')"
echo ""

# Show virtualenv seed wheels module info if available
echo "7. Virtualenv Seed Module Info:"
python -c "
try:
    from virtualenv.seed.wheels.embed import BUNDLE_FOLDER, BUNDLE_SUPPORT
    print(f'  Bundle folder: {BUNDLE_FOLDER}')
    print(f'  Bundle support: {BUNDLE_SUPPORT}')
except Exception as e:
    print(f'  Could not import seed module: {e}')
" 2>/dev/null || echo "  Could not retrieve seed module info"
echo ""

echo "========================================"
echo "  DIAGNOSTIC COMPLETE"
echo "========================================"