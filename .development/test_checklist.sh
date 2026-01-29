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

# Description: Quick checklist to verify the development environment and basic project sanity.
# Behavior:
#  - Verifies Python version and virtualenv presence, checks project metadata in `pyproject.toml`,
#    confirms presence of templates, translations, and sample frontend assets.
#  - Prints simple installation instructions for development and isolated testing.
# Usage:
#  - Run interactively to get a quick overview before running tests or manual testing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT=""
if command -v git >/dev/null 2>&1; then

    REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$REPO_ROOT" ]]; then

    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$REPO_ROOT"

PYTHON_BIN="python3"
PIP_BIN="pip"
if [[ -x "$REPO_ROOT/venv/bin/python" ]]; then

    PYTHON_BIN="$REPO_ROOT/venv/bin/python"
    PIP_BIN="$REPO_ROOT/venv/bin/pip"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then

    echo "ERROR: $PYTHON_BIN not found" >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' >/dev/null 2>&1; then

    "$PYTHON_BIN" --version >&2 || true
    echo "ERROR: Python 3.10+ is required to run this checklist" >&2
    echo "Hint: Run .development/setup_dev.sh to create ./venv" >&2
    exit 1
fi

REPO_ROOT_CMD="$REPO_ROOT"

echo "======================================"
echo "OctoPrint Plugin Template - Test Setup"
echo "======================================"
echo ""

# Step 1: Check Python
echo "1️⃣  Python & pip:"
"$PYTHON_BIN" --version
"$PIP_BIN" --version
echo ""

# Step 2: Check pyproject.toml
echo "2️⃣  Project Configuration:"
echo "   Plugin Name: $(grep '^name' pyproject.toml | cut -d'"' -f2)"
echo "   Version: $(grep '^version' pyproject.toml | cut -d'"' -f2)"
echo "   Python Requirement: $(grep 'requires-python' pyproject.toml)"
echo ""

# Step 3: Check main plugin file
echo "3️⃣  Backend Implementation:"
PLUGIN_METHODS=$(grep -c "def " octoprint_uptime/__init__.py)
echo "   ✓ $PLUGIN_METHODS backend methods implemented"
echo ""

# Step 4: Check Templates
echo "4️⃣  Templates:"
echo "   ✓ Settings: $(test -s octoprint_uptime/templates/settings.jinja2 && echo 'Ready' || echo 'Missing')"
echo ""

# Step 5: Check Templates
echo "5️⃣  Templates:"
echo "   ✓ Navbar: $(test -s octoprint_octoprint_uptime/templates/octoprint_uptime_navbar.jinja2 && echo 'Ready' || echo 'Missing')"
echo "   ✓ Settings: $(test -s octoprint_octoprint_uptime/templates/octoprint_uptime_settings.jinja2 && echo 'Ready' || echo 'Missing')"
echo "   ✓ Tab: $(test -s octoprint_octoprint_uptime/templates/octoprint_uptime_tab.jinja2 && echo 'Ready' || echo 'Missing')"
echo ""

# Step 6: Check Styling
echo "6️⃣  Styling:"
LESS_LINES=$(wc -l < octoprint_octoprint_uptime/static/less/octoprint_uptime.less)
echo "   ✓ LESS: $LESS_LINES lines"
echo ""

# Step 7: Check Translations
echo "7️⃣  Internationalization:"
echo "   ✓ POT: $(test -s translations/messages.pot && echo 'Ready' || echo 'Missing')"
echo "   ✓ German: $(test -s octoprint_uptime/translations/de/LC_MESSAGES/messages.po && echo 'Ready' || echo 'Missing')"
echo "   ✓ English: $(test -s octoprint_uptime/translations/en/LC_MESSAGES/messages.po && echo 'Ready' || echo 'Missing')"
echo ""

# Step 8: Installation Instructions
echo "======================================"
echo "Installation Instructions"
echo "======================================"
echo ""
echo "Method A: Development Installation (for existing OctoPrint)"
echo "   cd $REPO_ROOT_CMD"
echo "   source venv/bin/activate"
echo "   python -m pip install -e \".[develop]\""
echo "   # Restart OctoPrint"
echo ""
echo "Method B: Isolated Testing Environment"
echo "   python3 -m venv /tmp/octoprint_test"
echo "   source /tmp/octoprint_test/bin/activate"
echo "   pip install OctoPrint"
echo "   cd $REPO_ROOT_CMD"
echo "   pip install -e \".[develop]\""
echo "   octoprint serve"
echo "   # Open http://localhost:5000"
echo ""
echo "======================================"
echo "✅ Plugin is ready for testing!"
echo "======================================"
