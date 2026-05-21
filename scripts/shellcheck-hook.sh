#!/usr/bin/env bash

# Lint shell scripts using ShellCheck for pre-commit hooks.
# Usage: scripts/shellcheck-hook.sh <file>...

set -euo pipefail

SHELLCHECK_MIN_VERSION="0.10.0"

usage() {
    cat <<'USAGE'
Usage: scripts/shellcheck-hook.sh <file>...

Lint shell scripts using ShellCheck. Requires ShellCheck >= 0.10.0.
USAGE
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" || "${1:-}" = "help" ]]; then
    usage
    exit 0
fi

if ! command -v shellcheck >/dev/null 2>&1; then
    echo "ERROR: shellcheck is not installed or not in PATH" >&2
    echo "Please install ShellCheck >= $SHELLCHECK_MIN_VERSION" >&2
    echo "  Ubuntu/Debian: sudo apt-get install shellcheck" >&2
    echo "  macOS: brew install shellcheck" >&2
    exit 127
fi

SHELLCHECK_VERSION=$(shellcheck --version | sed -n 's/^version: \([0-9]*\.[0-9]*\.[0-9]*\).*/\1/p')
if [ -z "$SHELLCHECK_VERSION" ]; then
    echo "ERROR: Could not determine shellcheck version" >&2
    exit 1
fi

version_to_int() {
    local version="$1"
    local major=0 minor=0 patch=0
    IFS='.' read -r major minor patch <<< "$version"
    printf "%03d%03d%03d" "$major" "$minor" "$patch"
}

VERSION_INT="$(version_to_int "$SHELLCHECK_VERSION")"
MIN_VERSION_INT="$(version_to_int "$SHELLCHECK_MIN_VERSION")"

if [ "$VERSION_INT" -lt "$MIN_VERSION_INT" ]; then
    echo "ERROR: ShellCheck version $SHELLCHECK_VERSION is outdated" >&2
    echo "Minimum required version: $SHELLCHECK_MIN_VERSION" >&2
    echo "Please upgrade ShellCheck:" >&2
    echo "  Ubuntu/Debian: sudo apt-get install --only-upgrade shellcheck" >&2
    echo "  macOS: brew upgrade shellcheck" >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    echo "ERROR: no files provided to shellcheck-hook.sh" >&2
    usage
    exit 2
fi

shellcheck --severity=warning "$@"
