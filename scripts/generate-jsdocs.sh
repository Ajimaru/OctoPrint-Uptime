#!/usr/bin/env bash
set -e

echo "Generating JavaScript API documentation..."

# Resolve repository root (one level up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"
JS_SRC_DIR="$PROJECT_ROOT/octoprint_temp_eta/static/js"
DOCS_API_DIR="$PROJECT_ROOT/docs/api"
OUTPUT="${DOCS_API_DIR}/javascript.md"

# Check if JS files exist (robust recursive check)
if ! find "$JS_SRC_DIR" -type f -name '*.js' -print -quit >/dev/null 2>&1; then
    echo "Warning: No JavaScript files found"
    mkdir -p "$DOCS_API_DIR"
    echo "# JavaScript API" > "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "No JavaScript files found for documentation generation." >> "$OUTPUT"
    exit 0
fi

# Generate documentation
mkdir -p "$DOCS_API_DIR"

# Locate local jsdoc-to-markdown binary (prefer local dev dependency)
if [ -x "$PROJECT_ROOT/node_modules/.bin/jsdoc2md" ]; then
    JSdoc2md="$PROJECT_ROOT/node_modules/.bin/jsdoc2md"
elif command -v jsdoc2md >/dev/null 2>&1; then
    JSdoc2md="jsdoc2md"
else
    # Interactive prompt to optionally install the dev dependency
    if [ -t 0 ]; then
        read -r -p "jsdoc-to-markdown not found locally. Install as dev-dependency now? (y/N) " REPLY
        case "$REPLY" in
            [yY])
                (cd "$PROJECT_ROOT" && npm install --save-dev jsdoc-to-markdown) || {
                    echo "Failed to install jsdoc-to-markdown" >&2
                    exit 1
                }
                JSdoc2md="$PROJECT_ROOT/node_modules/.bin/jsdoc2md"
                ;;
            *)
                echo "jsdoc-to-markdown not installed; aborting documentation generation." >&2
                exit 1
                ;;
        esac
    else
        echo "jsdoc-to-markdown not found and session is non-interactive; aborting." >&2
        exit 1
    fi
fi

# Run the generator from the project root so relative patterns resolve correctly
if ! (cd "$PROJECT_ROOT" && "$JSdoc2md" --configure "jsdoc.json" "octoprint_temp_eta/static/js/**/*.js" > "$OUTPUT"); then
    echo "JSDoc generation failed" >&2
    exit 1
fi

# Normalize generated output to avoid accidental diffs from trailing whitespace
# and ensure consistent formatting across environments. This prevents
# pre-commit hooks from modifying the file in CI.
if command -v sed >/dev/null 2>&1; then
    sed -E -i 's/[[:space:]]+$//' "$OUTPUT" || true
fi

# Ensure file ends with exactly one newline (remove extra blank lines at EOF)
if command -v perl >/dev/null 2>&1; then
    # Remove trailing whitespace on lines and ensure exactly one newline at EOF
    perl -0777 -pe 's/[ \t]+$//mg; s/\n+\z/\n/' "$OUTPUT" > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT" || true
else
    # Fallback: try awk to ensure there is a single trailing newline
    awk 'BEGIN{ORS=""} {print}' "$OUTPUT" | sed -E ':a;/\n$/{$!{N;ba}};s/\n+$/\n/' > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT" || true
fi

# Check if output is empty (no JSDoc comments)
if [ ! -s "$OUTPUT" ]; then
    echo "Warning: No JSDoc comments found in JavaScript files"
    cat > "$OUTPUT" << 'EOF'
# JavaScript API

This page will contain auto-generated JavaScript API documentation.

## Current Status

The JavaScript source files exist but don't yet have JSDoc comments. To generate documentation:

1. Add JSDoc comments to JavaScript files
2. Run `./scripts/generate-jsdocs.sh`

## Example JSDoc Comment

```javascript
/**
 * Calculate ETA for a heater.
 * @param {string} heater - Heater name (e.g., "tool0", "bed")
 * @param {Object} data - Temperature data
 * @param {number} data.current - Current temperature
 * @param {number} data.target - Target temperature
 * @returns {number} ETA in seconds, or null if unavailable
 */
function calculateETA(heater, data) {
    // Implementation
}
```

## Source Files

- `octoprint_temp_eta/static/js/temp_eta.js`

## Manual Overview

For now, see the [manual overview](javascript.md) in this directory.
EOF
fi

echo "Generated $OUTPUT"
