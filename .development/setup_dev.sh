#!/usr/bin/env bash

# Description: Create and prepare a development virtual environment and install tooling.
# Behavior:
#  - Creates a `venv/` virtualenv (if missing), activates it, and installs packaging/dev tools.
#  - Installs optional development and docs requirements from `requirements-dev.txt` and
#  - `requirements-docs.txt` when present.
#  - Ensures helper tools (`bump-my-version`, `pre-commit`, `build`, etc.) are available
#    in the venv and configures repo-local git hooks (`.githooks`).
#  - Optionally installs Node.js dev dependencies (`npm install`) to populate `node_modules`.
# Usage examples:
#  - .development/setup_dev.sh
#  - DEV_EDITABLE=1 .development/setup_dev.sh  # install editable for development

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


# Activate virtual environment (cross-platform)
echo "Activating virtual environment..."
if [ -f "$VENV_DIR/bin/activate" ]; then
    # Unix/Linux/WSL
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    # Windows (Git Bash, CMD, PowerShell)
    # shellcheck disable=SC1091
    source "$VENV_DIR/Scripts/activate"
else
    echo "ERROR: Could not find virtualenv activation script."
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Ensure `tomli` is available for scripts that parse pyproject.toml on Python <3.11
echo "Ensuring tomli is installed in the virtualenv..."
if ! python -c "import tomli" >/dev/null 2>&1; then
    python -m pip install tomli || echo "WARNING: failed to install tomli into virtualenv"
else
    echo "tomli already present in virtualenv"
fi

# Ensure `build` is available for creating distribution artifacts
echo "Ensuring build is installed in the virtualenv..."
if ! python -c "import build" >/dev/null 2>&1; then
    python -m pip install build || echo "WARNING: failed to install build into virtualenv"
else
    echo "build already present in virtualenv"
fi

# Full dev requirements install: ensure all development dependencies are available
REQ_DEV="$REPO_ROOT/requirements-dev.txt"
if [[ -f "${REQ_DEV}" ]]; then
    echo "Installing full development requirements from: ${REQ_DEV}"
    # Try to install; don't fail the script if some optional packages fail
    python -m pip install -r "${REQ_DEV}" || echo "WARNING: Some dev requirements failed to install. You can retry manually: python -m pip install -r ${REQ_DEV}"
else
    echo "No requirements-dev.txt found at ${REQ_DEV}; skipping full dev install"
fi

# Full dev requirements install: ensure all documentation dependencies are available
REQ_DOCS="$REPO_ROOT/requirements-docs.txt"
if [[ -f "${REQ_DOCS}" ]]; then
    echo "Installing documentation requirements from: ${REQ_DOCS}"
    python -m pip install -r "${REQ_DOCS}" || echo "WARNING: Some docs requirements failed to install. You can retry manually: python -m pip install -r ${REQ_DOCS}"
else
    echo "No requirements-docs.txt found at ${REQ_DOCS}; skipping docs requirements install"
fi

# Check for bump-my-version and offer to install into the venv
if ! command -v bump-my-version >/dev/null 2>&1; then
    echo "bump-my-version not found in the virtual environment."
    read -r -p "Install bump-my-version into the virtualenv now? [Y/n] " _ans
    _ans=${_ans:-Y}
    if [[ "$_ans" =~ ^[Yy] ]]; then
        echo "Installing bump-my-version into virtualenv..."
        python -m pip install bump-my-version
    else
        echo "Skipping bump-my-version installation. You can install later with: python -m pip install bump-my-version"
    fi
else
    echo "bump-my-version is already available in the virtual environment."
fi

# Create .development/bumpversion.toml if it does not exist
BUMP_TOML=".development/bumpversion.toml"
if [[ ! -f "$BUMP_TOML" ]]; then
    cat > "$BUMP_TOML" <<EOF
# bump-my-version / bump2version-compatible TOML config (root copy)
# Created for OctoPrint-Uptime. Adjust patterns if needed.

[bumpversion]
current_version = "0.0.1"
tag = false
tag_name = "v{new_version}"
tag_message = "Bump version: {current_version} → {new_version}"
commit = false
message = "Bump version: {current_version} → {new_version}"

[[bumpversion.files]]
path = "octoprint_uptime/_version.py"
search = "VERSION = \"{current_version}\""
replace = "VERSION = \"{new_version}\""

[[bumpversion.files]]
path = "pyproject.toml"
search = "version = \"{current_version}\""
replace = "version = \"{new_version}\""

# Add additional files if you want documentation or README updated automatically.
EOF
    echo "Created $BUMP_TOML with default content."
fi

# Command-line parsing: support `-h|--help` and optional `editable` arg
INSTALL_MODE="${1:-}"
if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
        cat <<'USAGE'
Usage: setup_dev.sh [editable]

This script prepares a development virtual environment. It will NOT
install any distribution artifacts from the `dist/` folder. To install
the package into the venv for development, pass the single argument
`editable` or set `DEV_EDITABLE=1` in the environment to perform an
editable install (`pip install -e .`).

Examples:
    # default: create venv and prepare dev environment (no dist installs)
    ./.development/setup_dev.sh

    # install in editable mode (dev workflow)
    ./.development/setup_dev.sh editable

    # equivalent via env
    DEV_EDITABLE=1 ./.development/setup_dev.sh

Options:
    -h, --help    Show this help message and exit
USAGE
        exit 0
fi

# Install plugin with development dependencies
# IMPORTANT: This dev setup MUST NOT install artifacts from `dist/`.
# If the developer wants an editable install, pass `editable` or set
# `DEV_EDITABLE=1`. Otherwise this script only prepares the venv and
# dev tooling (no dist installs are performed).
if [[ "${DEV_EDITABLE:-0}" = "1" ]] || [[ "${INSTALL_MODE}" = "editable" ]]; then
    echo "Installing plugin in editable mode with development dependencies..."
    python -m pip install -e ".[develop]"
else
    echo "Skipping installation of distribution artifacts from dist/."
    echo "This script only prepares the development environment by default."
    echo "To install the package into the venv for testing, build a wheel and then:"
    echo "  python -m pip install dist/<your-wheel-file>.whl"
fi

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
# Prefer the virtualenv's pre-commit binary to ensure hooks run inside the venv
VENV_PRECOMMIT="$VENV_DIR/bin/pre-commit"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ -x "${VENV_PRECOMMIT}" ]]; then
    "${VENV_PRECOMMIT}" install-hooks || echo "WARNING: failed to install hooks using ${VENV_PRECOMMIT}"
else
    echo "pre-commit not found in venv; installing into venv via ${VENV_PYTHON}..."
    # Ensure packaging tools are reasonably up-to-date before installing
    "${VENV_PYTHON}" -m pip install --upgrade pip setuptools wheel || true
    if "${VENV_PYTHON}" -m pip install pre-commit; then
        if [[ -x "${VENV_PRECOMMIT}" ]]; then
            "${VENV_PRECOMMIT}" install-hooks || echo "WARNING: pre-commit installed but installing hooks failed"
        else
            echo "WARNING: pre-commit installed into venv but ${VENV_PRECOMMIT} not found"
        fi
    else
        echo "WARNING: Failed to install pre-commit into the virtualenv. You can install it manually with: ${VENV_PYTHON} -m pip install pre-commit"
    fi
fi

    # Ensure JavaScript documentation tooling is available (jsdoc-to-markdown)
    # If a local `node_modules/.bin/jsdoc2md` is missing, run `npm install` in the
    # repository root to populate `node_modules` (package.json already lists the
    # devDependency). If `npm` is not present, print a warning but do not fail.
    echo "Ensuring jsdoc-to-markdown is available for generating JavaScript docs..."
    if command -v npm >/dev/null 2>&1; then
        # Ensure the local node dev deps are present (jsdoc2md, prettier, etc.)
        NEED_INSTALL=0
        if [[ ! -x "${REPO_ROOT}/node_modules/.bin/jsdoc2md" ]]; then
            echo "jsdoc-to-markdown missing"
            NEED_INSTALL=1
        fi
        if [[ ! -x "${REPO_ROOT}/node_modules/.bin/prettier" ]]; then
            echo "prettier missing"
            NEED_INSTALL=1
        fi

        if [[ ${NEED_INSTALL} -eq 1 ]]; then
            echo "Installing Node.js dev dependencies (this will install jsdoc-to-markdown, prettier, etc.)..."
            if (cd "${REPO_ROOT}" && npm install --no-audit --no-fund); then
                echo "Node dev dependencies installed"
            else
                echo "WARNING: 'npm install' failed. You can install manually by running 'npm install' in the project root." >&2
            fi
        else
            echo "Node dev dependencies already installed locally"
        fi
    else
        echo "WARNING: 'npm' not found on PATH — skipping automatic installation of Node dev dependencies. Install Node.js and run 'npm install' to enable JS doc generation and Prettier." >&2
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

