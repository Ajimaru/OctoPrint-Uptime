#!/usr/bin/env bash
set -euo pipefail

# Prettier pre-commit hook helper
# Usage: prettier-hook.sh <file>...

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -x "${REPO_ROOT}/node_modules/.bin/prettier" ]]; then
    exec "${REPO_ROOT}/node_modules/.bin/prettier" --write "$@"
else
    # Use npx fallback; --yes to avoid prompts
    exec npx --yes prettier --write "$@"
fi
