#!/usr/bin/env bash
# Setup script for OctoPrint octoprint_plugin_template plugin development.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "Setting up development environment..."

# GitHub "Download ZIP" and some extractors may drop executable bits.
# Best-effort: restore execute permission for repo scripts and hooks.
echo "Ensuring scripts are executable (best-effort)..."
chmod +x .development/*.sh 2>/dev/null || true
chmod +x .githooks/* 2>/dev/null || true

PYTHON_BIN="${PYTHON_BIN:-python3}"

# Check if Python 3.10+ is available (dev environment requirement)
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON_BIN is not installed" >&2
    exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys

major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
    raise SystemExit(f"ERROR: Python {major}.{minor} found, but 3.10+ is required for development setup")

print(f"Found Python {major}.{minor}")
PY

VENV_DIR="$REPO_ROOT/venv"

# Create virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment at: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists: $VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install plugin with development dependencies
echo "Installing plugin (editable) with development dependencies..."
python -m pip install -e ".[develop]"

# Enable repo-local git hooks (post-commit build on version bump)
echo "Enabling repository git hooks (.githooks)..."
if command -v git >/dev/null 2>&1; then
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        chmod +x .githooks/post-commit 2>/dev/null || true
        chmod +x .githooks/pre-commit 2>/dev/null || true
        git config core.hooksPath .githooks
        echo "Git hooks enabled (core.hooksPath=.githooks)"
    else
        echo "WARNING: Not a git repository, skipping git hooks setup"
    fi
else
    echo "WARNING: git not found, skipping git hooks setup"
fi

# Install pre-commit environments (hooks are managed via core.hooksPath=.githooks)
echo "Setting up pre-commit..."
if command -v pre-commit >/dev/null 2>&1; then
    pre-commit install-hooks
else
    echo "WARNING: pre-commit not found, skipping pre-commit setup"
    echo "         Install via: python -m pip install pre-commit (recommended)"
    echo "         or system-wide: sudo apt install pre-commit"
fi

# Run pre-commit on all files (optional, can take time)
if [[ "${RUN_PRE_COMMIT_ALL_FILES:-0}" == "1" ]]; then
    echo "Running initial pre-commit checks..."
    if command -v pre-commit >/dev/null 2>&1; then
        pre-commit run --all-files || echo "WARNING: Some pre-commit checks failed (common on first run)."
    else
        echo "WARNING: pre-commit not found, skipping initial checks"
    fi
else
    echo "Skipping initial pre-commit checks (set RUN_PRE_COMMIT_ALL_FILES=1 to enable)."
fi

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run tests: pytest"
echo "  3. Run checks (if installed): pre-commit run --all-files"
echo ""
echo "See CONTRIBUTING.md for more information."
