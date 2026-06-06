#!/usr/bin/env bash

# Format files using Prettier for pre-commit hooks.
# Usage: scripts/prettier-hook.sh <file>...

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

usage() {
    cat <<'USAGE'
Usage: scripts/prettier-hook.sh <file>...

Format files using Prettier. Uses local `node_modules/.bin/prettier` when available,
otherwise falls back to `npx --yes prettier --write`.
USAGE
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" || "${1:-}" = "help" ]]; then
    usage
    exit 0
fi

if [ "$#" -eq 0 ]; then
    echo "ERROR: no files provided to prettier-hook.sh" >&2
    usage
    exit 2
fi

if [[ -x "${REPO_ROOT}/node_modules/.bin/prettier" ]]; then
    exec "${REPO_ROOT}/node_modules/.bin/prettier" --write "$@"
fi

if command -v node >/dev/null 2>&1 && [ -f package.json ]; then
    echo "Installing npm dependencies (prettier) if missing..."
    attempt=0
    npm_ci_succeeded=false
    until [ "$attempt" -ge 3 ]; do
        if npm ci --no-audit --no-fund; then
            npm_ci_succeeded=true
            break
        fi
        attempt=$((attempt + 1))
        sleep $((2 ** attempt))
    done
    if [ "$npm_ci_succeeded" != "true" ]; then
        echo "Warning: 'npm ci' failed after $attempt attempts; falling back to npx." >&2
    fi
    if [[ -x "${REPO_ROOT}/node_modules/.bin/prettier" ]]; then
        exec "${REPO_ROOT}/node_modules/.bin/prettier" --write "$@"
    fi
fi

attempt=0
until [ "$attempt" -ge 3 ]; do
    if npx --yes prettier --write "$@"; then
        exit 0
    fi
    attempt=$((attempt + 1))
    echo "npx/prettier attempt $attempt failed, retrying..."
    sleep $((2 ** attempt))
done

exec npx --yes prettier --write "$@"
