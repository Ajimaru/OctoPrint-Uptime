#!/usr/bin/env bash
set -euo pipefail

# Generate JavaScript API docs (jsdoc2md) into MkDocs `docs/api/javascript.md`.
# This script uses paths relative to the repository root so it can be executed
# from any working directory. It requires `jsdoc-to-markdown` (install via npm).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OUT_DIR="$REPO_ROOT/docs/api"
mkdir -p "$OUT_DIR"

CONFIG="$REPO_ROOT/jsdoc.json"
SRC_GLOB="$REPO_ROOT/octoprint_uptime/static/js/**/*.js"
OUT_FILE="$OUT_DIR/javascript.md"

npx jsdoc2md \
  --configure "$CONFIG" \
  "$SRC_GLOB" \
  > "$OUT_FILE"

echo "Generated $OUT_FILE"
