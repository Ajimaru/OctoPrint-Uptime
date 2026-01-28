#!/usr/bin/env bash

# Description: Generate JavaScript API documentation (docs/api/javascript.md) using jsdoc-to-markdown.
# Behavior:
#  - Uses `jsdoc-to-markdown` (local `node_modules/.bin/jsdoc2md` or global `jsdoc2md`).
#  - Accepts explicit file paths as arguments or scans `octoprint_uptime/static/js/**/*.js`.
#  - Optionally offers to install `jsdoc-to-markdown` interactively when run in a TTY.
#  - Normalizes and trims trailing whitespace from the generated Markdown output.
# Usage examples:
#  - ./scripts/generate-jsdocs.sh
#  - ./scripts/generate-jsdocs.sh octoprint_uptime/static/js/uptime.js

set -e

usage() {
cat <<'USAGE'
Usage: scripts/generate-jsdocs.sh [FILES...]

Generate JavaScript API documentation into `docs/api/javascript.md`.

If FILES are provided they are used as the input list; otherwise the script
scans `octoprint_uptime/static/js/**/*.js` for source files.

Options:
    -h, --help    Show this help message and exit

Examples:
    ./scripts/generate-jsdocs.sh
    ./scripts/generate-jsdocs.sh octoprint_uptime/static/js/uptime.js
USAGE
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" || "${1:-}" = "help" ]]; then
        usage
        exit 0
fi

echo "Generating JavaScript API documentation..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"
JS_SRC_DIR="$PROJECT_ROOT/octoprint_uptime/static/js"
DOCS_API_DIR="$PROJECT_ROOT/docs/api"
OUTPUT="${DOCS_API_DIR}/javascript.md"

ARGS=("$@")
USE_PASSED_FILES=0
if [ "${#ARGS[@]}" -gt 0 ]; then
    USE_PASSED_FILES=1
fi

if [ "$USE_PASSED_FILES" -eq 1 ]; then
    missing=0
    for f in "${ARGS[@]}"; do
        if [ ! -f "$PROJECT_ROOT/$f" ]; then
            echo "Warning: passed file not found: $f" >&2
            missing=1
        fi
    done
    if [ "$missing" -eq 1 ]; then
        echo "Aborting jsdoc generation due to missing files." >&2
        exit 1
    fi
else
    if ! find "$JS_SRC_DIR" -type f -name '*.js' -print -quit >/dev/null 2>&1; then
        echo "Warning: No JavaScript files found"
        mkdir -p "$DOCS_API_DIR"
        echo "# JavaScript API" > "$OUTPUT"
        echo "" >> "$OUTPUT"
        echo "No JavaScript files found for documentation generation." >> "$OUTPUT"
        exit 0
    fi
fi

mkdir -p "$DOCS_API_DIR"

if [ -x "$PROJECT_ROOT/node_modules/.bin/jsdoc2md" ]; then
    JSdoc2md="$PROJECT_ROOT/node_modules/.bin/jsdoc2md"
elif command -v jsdoc2md >/dev/null 2>&1; then
    JSdoc2md="jsdoc2md"
else
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

if [ "$USE_PASSED_FILES" -eq 1 ]; then
    if ! (cd "$PROJECT_ROOT" && "$JSdoc2md" --configure "docs/jsdoc.json" "${ARGS[@]}" > "$OUTPUT"); then
        echo "JSDoc generation failed" >&2
        exit 1
    fi
else
    if ! (cd "$PROJECT_ROOT" && "$JSdoc2md" --configure "docs/jsdoc.json" "octoprint_uptime/static/js/**/*.js" > "$OUTPUT"); then
        echo "JSDoc generation failed" >&2
        exit 1
    fi
fi

if command -v sed >/dev/null 2>&1; then
    sed -E -i 's/[[:space:]]+$//' "$OUTPUT" || true
fi

if command -v perl >/dev/null 2>&1; then
    perl -0777 -pe 's/[ \t]+$//mg; s/\n+\z/\n/' "$OUTPUT" > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT" || true
else
    awk 'BEGIN{ORS=""} {print}' "$OUTPUT" | sed -E ':a;/\n$/{$!{N;ba}};s/\n+$/\n/' > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT" || true
fi

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

- `octoprint_uptime/static/js/uptime.js`

## Manual Overview

For now, see the [manual overview](javascript.md) in this directory.
EOF
fi

echo "Generated $OUTPUT"

