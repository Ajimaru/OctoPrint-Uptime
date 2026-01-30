#!/usr/bin/env bash

# When running on native Windows, prefer to re-exec this script under
# Git Bash if available. This attempts to locate a Git Bash `bash.exe`
# and exec the original script under it. Comments are English-only.
_SCRIPT_DIR_HINT="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd || dirname "$0")"
# Wrapper moved to project-level `scripts/` directory
WRAPPER="$_SCRIPT_DIR_HINT/../scripts/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
    if [ -x "$WRAPPER" ]; then
        exec "$WRAPPER" "$0" "$@"
        else
        # If wrapper is not present but bash is available, try to re-exec directly
        if command -v bash >/dev/null 2>&1; then
            exec bash "$0" "$@"
        fi

        # If we reached here, no bash found. If we're on Windows (where.exe present),
        # offer to open the Git for Windows download page via PowerShell helper.
        if command -v where.exe >/dev/null 2>&1; then
                echo "Git Bash not found on PATH."
                read -r -p "Install Git for Windows (open download page)? [Y/n] " _ans
                _ans=${_ans:-Y}
                if [[ "$_ans" =~ ^[Yy] ]]; then
                        # Try to invoke the PowerShell helper to open the download page
                        if command -v powershell.exe >/dev/null 2>&1; then
                                powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$_SCRIPT_DIR_HINT/install-git-for-windows.ps1" -OpenOnly
                        else
                                echo "Could not find powershell.exe to open download page. Please visit: https://git-scm.com/download/win"
                        fi
                        echo "Please install Git for Windows and re-run this script inside Git Bash or ensure 'bash' is on PATH." >&2
                        exit 1
                else
                        echo "Git Bash is required on Windows to run this script. Exiting." >&2
                        exit 1
                fi
        fi
    fi
fi

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

# Create logs directory and redirect all output to a timestamped logfile (also tee to console)
LOG_DIR="${LOG_DIR:-$REPO_ROOT/.logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/setup_dev-$(date +'%Y%m%d-%H%M%S').log"
# Redirect stdout/stderr to logfile while preserving console output
exec > >(tee -a "$LOG_FILE") 2>&1
echo "Logging to $LOG_FILE"

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
if (major, minor) <= (3, 7) or (major, minor) >= (3, 13):
    print(f"ERROR: Python {major}.{minor} found, but Python >3.7 and <3.13 is required for development setup.")
    print("\nUpgrade instructions:")
    print("- Windows: Download and install Python 3.8–3.12 from https://www.python.org/downloads/windows/")
    print("- macOS: Use Homebrew: brew install python@3.12 (or similar)")
    print("- Linux: Use your package manager, e.g. sudo apt install python3.12")
    print("\nAfter upgrading, ensure 'python3' points to the new version, or set PYTHON_BIN to the correct executable.")
    sys.exit(1)

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
    echo "WARNING: No requirements-dev.txt found at ${REQ_DEV}; skipping full dev install"
fi

# If argostranslate is present in dev requirements, attempt to install an
# English->German Argos model into the venv for offline autofill support.
echo "Ensuring Argos (argostranslate) and models are installed into the venv..."
# Use the venv python explicitly to avoid ambiguity when executing model install
VENV_PYTHON="${VENV_DIR}/bin/python"
echo "Using venv python: ${VENV_PYTHON}"

# Configure Argos environment to install packages inside the venv
export ARGOS_PACKAGES_DIR="${VENV_DIR}/.local/share/argos-translate/packages"
export XDG_DATA_HOME="${VENV_DIR}/.local/share"
export XDG_CACHE_HOME="${VENV_DIR}/.local/cache"
export XDG_CONFIG_HOME="${VENV_DIR}/.config"
mkdir -p "${ARGOS_PACKAGES_DIR}" "${XDG_CACHE_HOME}" "${XDG_CONFIG_HOME}"
echo "Configured Argos data dirs inside venv: ${ARGOS_PACKAGES_DIR}"

# If argostranslate is not present in the venv, try to install it there.
# Use a compact one-liner for the python -c invocation to avoid multiline
# quoting/here-doc parsing issues in shells.
if ! "${VENV_PYTHON}" -c "import importlib.util as util, sys; sys.exit(0 if util and util.find_spec('argostranslate') else 1)" >/dev/null 2>&1; then
    echo "argostranslate not detected in venv; attempting to install via ${VENV_PYTHON} -m pip install argostranslate"
    if "${VENV_PYTHON}" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 && "${VENV_PYTHON}" -m pip install argostranslate; then
        echo "argostranslate installed into venv"
    else
        echo "WARNING: Failed to install argostranslate into venv; skipping Argos model install"
    fi
else
    echo "argostranslate already present in venv"
fi

# Run the model installation using the venv python; make this step robust and non-fatal.
"${VENV_PYTHON}" - <<'PY' || true
import traceback
try:
    import importlib.util as util
except Exception:
    util = None
try:
    if util is None:
        print('importlib.util is not available in this interpreter; cannot proceed with Argos model install')
    else:
        if util.find_spec('argostranslate') is None:
            print('argostranslate not available in venv; skipping Argos model install')
        else:
            try:
                from argostranslate import package
                installed = package.get_installed_packages()
                already = False
                for ip in installed:
                    if getattr(ip, 'from_code', '') == 'en' and getattr(ip, 'to_code', '') == 'de':
                        print('Argos en->de model already installed in venv')
                        already = True
                        break
                if not already:
                    pkgs = package.get_available_packages()
                    for p in pkgs:
                        if getattr(p, 'from_code', '') == 'en' and getattr(p, 'to_code', '') == 'de':
                            print('Installing Argos en->de package into venv...')
                            try:
                                p.install()
                                print('Argos en->de package installed')
                            except Exception:
                                print('Failed to install Argos en->de package:')
                                traceback.print_exc()
                            break
                    else:
                        print('No en->de Argos package available from remote index')
                print('Installed Argos packages (venv):', [f"{getattr(x,'from_code','')}->{getattr(x,'to_code','')}" for x in package.get_installed_packages()])
            except Exception:
                print('Argos model installation skipped or failed during package handling:')
                traceback.print_exc()
except Exception:
    print('Argos model installation skipped due to unexpected error:')
    traceback.print_exc()
PY

# Ensure venv activation exports Argos/XDG env vars so subsequent shells see venv-local packages
ACTIVATE_FILE="$VENV_DIR/bin/activate"
if [[ -f "$ACTIVATE_FILE" ]]; then
    if ! grep -q "ARGOS_PACKAGES_DIR" "$ACTIVATE_FILE" 2>/dev/null; then
        cat >> "$ACTIVATE_FILE" <<'EOF'
    # Argos Translate venv-local data directories (added by setup_dev.sh)
    # Use VIRTUAL_ENV so these paths are correct when the venv is activated.
    export ARGOS_PACKAGES_DIR="${VIRTUAL_ENV}/.local/share/argos-translate/packages"
    export XDG_DATA_HOME="${VIRTUAL_ENV}/.local/share"
    export XDG_CACHE_HOME="${VIRTUAL_ENV}/.local/cache"
    export XDG_CONFIG_HOME="${VIRTUAL_ENV}/.config"
EOF
        echo "Added Argos env exports to $ACTIVATE_FILE"
    else
        echo "Argos env exports already present in $ACTIVATE_FILE"
    fi
fi

# Install runtime requirements (requirements.txt) into the virtualenv if present
REQ_RUNTIME="$REPO_ROOT/requirements.txt"
if [[ -f "${REQ_RUNTIME}" ]]; then
    echo "Installing runtime requirements from: ${REQ_RUNTIME}"
    python -m pip install -r "${REQ_RUNTIME}" || echo "WARNING: Some runtime requirements failed to install. You can retry manually: python -m pip install -r ${REQ_RUNTIME}"
else
    echo "WARNING: No requirements.txt found at ${REQ_RUNTIME}; skipping runtime requirements install"
fi

# Full dev requirements install: ensure all documentation dependencies are available
REQ_DOCS="$REPO_ROOT/requirements-docs.txt"
if [[ -f "${REQ_DOCS}" ]]; then
    echo "INFO: requirements-docs.txt is present at ${REQ_DOCS}, but this script intentionally does NOT install docs requirements into the main venv."
    echo "If you want a separate docs virtualenv, create .venv-docs and install the file there:"
    echo "  python -m venv .venv-docs && .venv-docs/bin/pip install -r ${REQ_DOCS}"
else
    echo "INFO: No requirements-docs.txt found at ${REQ_DOCS}; nothing to install for docs (intentional)."
fi

if ! command -v bump-my-version >/dev/null 2>&1; then
    echo "bump-my-version not found in the virtual environment; installing..."
    if python -m pip install bump-my-version; then
        echo "bump-my-version installed into the virtualenv"
    else
        echo "WARNING: Failed to install bump-my-version. You can install manually with: python -m pip install bump-my-version" >&2
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
