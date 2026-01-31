#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
if _script_dir="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"; then
    _SCRIPT_DIR_HINT="$_script_dir"
else
    _SCRIPT_DIR_HINT="$(dirname "$0")"
fi
if _repo_root="$(cd "$_SCRIPT_DIR_HINT/.." >/dev/null 2>&1 && pwd)"; then
    REPO_ROOT="$_repo_root"
else
    REPO_ROOT="$_SCRIPT_DIR_HINT"
fi
WRAPPER="$REPO_ROOT/scripts/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
    if [ -x "$WRAPPER" ]; then
        exec "$WRAPPER" "$0" "$@"
    elif command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
fi

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
    if [ -z "$(find "$JS_SRC_DIR" -type f -name '*.js' -print -quit 2>/dev/null)" ]; then
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
    if sed --version >/dev/null 2>&1; then
        SED_INPLACE_ARGS=("-i")
    elif [ "$(uname -s 2>/dev/null)" = "Darwin" ]; then
        SED_INPLACE_ARGS=("-i" "")
    else
        SED_INPLACE_ARGS=("-i")
    fi

    if ! sed -E "${SED_INPLACE_ARGS[@]}" 's/[[:space:]]+$//' "$OUTPUT"; then
        echo "sed in-place failed; continuing with perl/awk fallback" >&2
    fi
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
 * Format system uptime for display.
 * @param {number} seconds - Uptime in seconds
 * @param {string} format - Display format: "full", "dhm", "dh", "d", or "short"
 * @returns {string} Formatted uptime string suitable for UI display
 */
function formatUptime(seconds, format) {
    if (typeof seconds !== "number" || isNaN(seconds)) {
        return "unknown";
    }
    const secs = Math.max(0, Math.floor(seconds));
    const days = Math.floor(secs / 86400);
    const hours = Math.floor((secs % 86400) / 3600);
    const minutes = Math.floor((secs % 3600) / 60);

    switch (format) {
        case "dhm":
            return `${days}d ${hours}h ${minutes}m`;
        case "dh":
            return `${days}d ${hours}h`;
        case "d":
            return `${days}d`;
        case "short":
            if (days > 0) return `${days}d ${hours}h`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            return `${minutes}m`;
        case "full":
        default:
            return `${days}d ${hours}h ${minutes}m`;
    }
}
```

## Source Files

- `octoprint_uptime/static/js/uptime.js`

## Manual Overview

For now, see the [manual overview](javascript.md) in this directory.
EOF
fi

echo "Generated $OUTPUT"
