#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
_SCRIPT_DIR_HINT="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd || dirname "$0")"
REPO_ROOT="$(cd "$_SCRIPT_DIR_HINT/.." >/dev/null 2>&1 && pwd || echo "$_SCRIPT_DIR_HINT")"
WRAPPER="$REPO_ROOT/.development/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
    if [ -x "$WRAPPER" ]; then
        exec "$WRAPPER" "$0" "$@"
    elif command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
fi

# Description: Format files using Prettier for pre-commit hooks.
# Behavior:
#  - Uses local `node_modules/.bin/prettier --write` when available, otherwise falls back to `npx --yes prettier --write`.
#  - Intended to be invoked from git pre-commit hooks with a list of files to format.
# Usage:
#  - .development/prettier-hook.sh <file>...

set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: .development/prettier-hook.sh <file>...

Format files using Prettier. Uses local `node_modules/.bin/prettier` when available,
otherwise falls back to `npx --yes prettier --write`.

Options:
    -h, --help    Show this help message and exit
USAGE
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" || "${1:-}" = "help" ]]; then
    usage
    exit 0
fi

# Prettier pre-commit hook helper (moved to .development)
# Usage: prettier-hook.sh <file>...

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -x "${REPO_ROOT}/node_modules/.bin/prettier" ]]; then
    exec "${REPO_ROOT}/node_modules/.bin/prettier" --write "$@"
else
    # Use npx fallback; --yes to avoid prompts
    exec npx --yes prettier --write "$@"
fi
