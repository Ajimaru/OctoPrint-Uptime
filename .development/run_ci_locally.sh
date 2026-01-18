#!/usr/bin/env bash

set -euo pipefail

log() {
    printf '[temp-eta ci] %s\n' "$*"
}

die() {
    log "ERROR: $*"
    exit 1
}

python_is_at_least_310() {
    local python_bin="$1"
    "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' >/dev/null 2>&1
}

usage() {
    cat <<'EOF'
Run CI-like checks locally.

Default behavior runs:
  - pytest
  - pre-commit
  - i18n catalog check + compile
    - python -m build (wheel + sdist + zip)

Usage:
  .development/run_ci_locally.sh [options]

Options:
  --no-tests        Skip pytest
  --no-pre-commit   Skip pre-commit
  --no-i18n         Skip i18n checks
  --no-build        Skip python -m build
  --apply-fixes     Keep auto-fixes made by pre-commit (default: revert changes)
  --allow-dirty     Allow running with a dirty git working tree
  -h, --help        Show this help

Notes:
  - This script targets a Python 3.10+ development environment.
  - It prefers ./venv/bin/python. If not present, it falls back to python3.
EOF
}

RUN_TESTS=1
RUN_PRE_COMMIT=1
RUN_I18N=1
RUN_BUILD=1
APPLY_FIXES=0
ALLOW_DIRTY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-tests)
            RUN_TESTS=0
            shift
            ;;
        --no-pre-commit)
            RUN_PRE_COMMIT=0
            shift
            ;;
        --no-i18n)
            RUN_I18N=0
            shift
            ;;
        --no-build)
            RUN_BUILD=0
            shift
            ;;
        --apply-fixes)
            APPLY_FIXES=1
            shift
            ;;
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1 (use --help)"
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT=""
if command -v git >/dev/null 2>&1; then
    REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$REPO_ROOT"

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CLEAN_START=1
    if ! git diff --quiet || ! git diff --cached --quiet; then
        CLEAN_START=0
    fi

    if [[ "$CLEAN_START" != "1" && "$ALLOW_DIRTY" != "1" ]]; then
        die "Working tree not clean. Commit/stash changes, or rerun with --allow-dirty."
    fi
else
    CLEAN_START=0
fi

PYTHON_BIN="python3"
if [[ -x "$REPO_ROOT/venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/venv/bin/python"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    die "$PYTHON_BIN not found"
fi

if ! python_is_at_least_310 "$PYTHON_BIN"; then
    "$PYTHON_BIN" --version >&2 || true
    die "Python 3.10+ required. Hint: run .development/setup_dev.sh"
fi

log "Using Python: $PYTHON_BIN ($($PYTHON_BIN -c 'import sys; print("%d.%d" % sys.version_info[:2])'))"

# Ensure dependencies are present inside the selected environment.
log "Installing/refreshing CI dependencies (editable + dev extras)"
"$PYTHON_BIN" -m pip install -q -U pip
"$PYTHON_BIN" -m pip install -q -e ".[develop]" build

if [[ "$RUN_TESTS" == "1" ]]; then
    log "Running pytest"
    "$PYTHON_BIN" -m pytest -q
fi

if [[ "$RUN_PRE_COMMIT" == "1" ]]; then
    pre_commit_failed=0

    if [[ -x "$REPO_ROOT/venv/bin/pre-commit" ]]; then
        log "Running pre-commit (from ./venv)"
        "$REPO_ROOT/venv/bin/pre-commit" run --all-files || pre_commit_failed=$?
    elif command -v pre-commit >/dev/null 2>&1; then
        log "Running pre-commit (from PATH)"
        pre-commit run --all-files || pre_commit_failed=$?
    else
        die "pre-commit not found. Run .development/setup_dev.sh or install pre-commit"
    fi

    if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        if [[ "$APPLY_FIXES" != "1" ]] && ! git diff --quiet; then
            if [[ "${CLEAN_START:-0}" == "1" ]]; then
                log "pre-commit would modify files; reverting changes (use --apply-fixes to keep them)"
                git --no-pager diff --stat || true
                git restore --worktree --staged :/ 2>/dev/null || true
                die "pre-commit required changes"
            fi

            log "pre-commit modified files, but the working tree was not clean; leaving changes in place"
            git --no-pager diff --stat || true
            die "pre-commit required changes"
        fi
    fi

    if [[ "$pre_commit_failed" != "0" ]]; then
        die "pre-commit failed"
    fi
fi

if [[ "$RUN_I18N" == "1" ]]; then
    log "Running i18n catalog check"

    # Match CI pins to reduce drift.
    "$PYTHON_BIN" -m pip install -q "Babel==2.16.0" "Jinja2==3.1.4"

    PYBABEL_BIN="pybabel"
    if [[ -x "$REPO_ROOT/venv/bin/pybabel" ]]; then
        PYBABEL_BIN="$REPO_ROOT/venv/bin/pybabel"
    fi

    tmp_pot="${RUNNER_TEMP:-/tmp}/messages.pot"
    "$PYBABEL_BIN" extract --sort-output -F babel.cfg -o "$tmp_pot" .

    "$PYTHON_BIN" - <<'PY' "$tmp_pot"
import pathlib
import sys

def normalize(path: str) -> str:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    for line in lines:
        # These headers are time/tool-version dependent.
        if line.startswith('"POT-Creation-Date:'):
            continue
        if line.startswith('"Generated-By:'):
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"

repo = "translations/messages.pot"
tmp = sys.argv[1]

if not pathlib.Path(repo).exists():
    print(f"Missing {repo}")
    raise SystemExit(1)

if normalize(repo) != normalize(tmp):
    print("translations/messages.pot is out of date. Run:")
    print("  pybabel extract --sort-output -F babel.cfg -o translations/messages.pot .")
    print("  pybabel update -i translations/messages.pot -d octoprint_uptime/translations -l de")
    print("  pybabel update -i translations/messages.pot -d octoprint_uptime/translations -l en")
    raise SystemExit(1)
PY

    log "Compiling catalogs"
    "$PYBABEL_BIN" compile -d octoprint_uptime/translations
fi

if [[ "$RUN_BUILD" == "1" ]]; then
    log "Building wheel + sdist"
    rm -rf dist
    mkdir -p dist
    "$PYTHON_BIN" -m build

    log "Building ZIP artifacts from sdist"
    "$PYTHON_BIN" - <<'PY'
import re
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


def newest(paths):
    return max(paths, key=lambda p: p.stat().st_mtime)


sdists = list(Path("dist").glob("OctoPrint-Uptime-*.tar.gz"))
if not sdists:
    print("ERROR: Expected an sdist matching dist/OctoPrint-Uptime-*.tar.gz", file=sys.stderr)
    raise SystemExit(1)

sdist = newest(sdists)
match = re.match(r"OctoPrint-Uptime-(.+)\.tar\.gz$", sdist.name)
if not match:
    print(f"ERROR: Could not parse version from {sdist.name}", file=sys.stderr)
    raise SystemExit(1)

version = match.group(1)
zip_versioned = Path("dist") / f"OctoPrint-Uptime-{version}.zip"
zip_latest = Path("dist") / "OctoPrint-Uptime-latest.zip"

with tarfile.open(sdist, "r:gz") as tf, zipfile.ZipFile(
    zip_versioned, "w", compression=zipfile.ZIP_DEFLATED
) as zf:
    for member in tf.getmembers():
        if not member.isfile():
            continue

        member_path = PurePosixPath(member.name)
        if (
            member_path.is_absolute()
            or ".." in member_path.parts
            or ":" in member.name
            or member.name.startswith("\\")
        ):
            continue

        extracted = tf.extractfile(member)
        if extracted is None:
            continue

        data = extracted.read()
        zi = zipfile.ZipInfo(str(member_path))
        zi.external_attr = (member.mode & 0o777) << 16
        zf.writestr(zi, data)

shutil.copyfile(zip_versioned, zip_latest)
print(f"Wrote {zip_versioned}")
print(f"Wrote {zip_latest}")
PY
fi

log "Done"
