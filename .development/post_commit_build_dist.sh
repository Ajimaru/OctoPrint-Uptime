#!/usr/bin/env bash
set -euo pipefail

# Post-commit hook: if the project version changed in this commit, build fresh
# artifacts into dist/ (wheel + sdist via build, plus a zip derived from sdist).

log() {
  printf '[OctoPrint-Uptime post-commit] %s\n' "$*"
}

python_is_at_least_310() {
  local python_bin="$1"
  "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' >/dev/null 2>&1
}

resolve_python() {
  local candidate

  for candidate in "./venv/bin/python"; do
    if [[ -x "$candidate" ]] && python_is_at_least_310 "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done

  if command -v python3 >/dev/null 2>&1 && python_is_at_least_310 "python3"; then
    echo "python3"
    return 0
  fi

  return 1
}

PYTHON=""
if PYTHON="$(resolve_python 2>/dev/null)"; then
  :
else
  log "ERROR: Python 3.10+ not available (expected ./venv/bin/python or python3>=3.10)."
  log "ERROR: Run: .development/setup_dev.sh"
  exit 1
fi

semver_is_lt() {
  "$PYTHON" -c '
import sys

def parse(v: str):
    parts = v.strip().split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            # Non-numeric (e.g. prerelease) -> treat as 0 to keep it safe.
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])

a = parse(sys.argv[1])
b = parse(sys.argv[2])
sys.exit(0 if a < b else 1)
' "$1" "$2"
}

semver_is_gt() {
  "$PYTHON" -c '
import sys

def parse(v: str):
    parts = v.strip().split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])

a = parse(sys.argv[1])
b = parse(sys.argv[2])
sys.exit(0 if a > b else 1)
' "$1" "$2"
}

get_previous_version_from_dist() {
  local new_version="$1"

  if [[ ! -d "dist" ]]; then
    echo ""
    return 0
  fi

  local best=""
  local file version
  for file in dist/OctoPrint-Uptime-*.tar.gz dist/OctoPrint-Uptime-*.whl dist/OctoPrint-Uptime-*.zip; do
    [[ -e "$file" ]] || continue
    version="$(basename "$file" | sed -nE 's/^OctoPrint-Uptime-([0-9]+\.[0-9]+\.[0-9]+).*/\1/p')"
    [[ -n "$version" ]] || continue

    if [[ "$version" == "$new_version" ]]; then
      continue
    fi

    if semver_is_lt "$version" "$new_version"; then
      if [[ -z "$best" ]] || semver_is_gt "$version" "$best"; then
        best="$version"
      fi
    fi
  done

  echo "$best"
}

get_version_from_pyproject() {
  local file_path="$1"

  "$PYTHON" -c '
import sys

path = sys.argv[1]
raw = open(path, "rb").read()

try:
  import tomllib  # py3.11+
  data = tomllib.loads(raw.decode("utf-8"))
except ModuleNotFoundError:
  import tomli  # type: ignore
  data = tomli.loads(raw.decode("utf-8"))

version = data.get("project", {}).get("version")
if not version:
  raise SystemExit("Unable to determine version from pyproject.toml")

print(version)
' "$file_path"
}

get_version_from_pyproject_content() {
  "$PYTHON" -c '
import sys

raw = sys.stdin.buffer.read()

try:
  import tomllib  # py3.11+
  data = tomllib.loads(raw.decode("utf-8"))
except ModuleNotFoundError:
  import tomli  # type: ignore
  data = tomli.loads(raw.decode("utf-8"))

version = data.get("project", {}).get("version")
if not version:
  raise SystemExit(1)

print(version)
'
}

create_zip_from_sdist() {
  local tar_path="$1"
  local zip_path="$2"

  "$PYTHON" - "$tar_path" "$zip_path" <<'PY'
import sys
import tarfile
import zipfile

from pathlib import Path

tar_path = Path(sys.argv[1])
zip_path = Path(sys.argv[2])

zip_path.parent.mkdir(parents=True, exist_ok=True)

with tarfile.open(tar_path, 'r:gz') as tf, zipfile.ZipFile(
    zip_path, 'w', compression=zipfile.ZIP_DEFLATED
) as zf:
    for member in tf.getmembers():
        if not member.isfile():
            continue

        extracted = tf.extractfile(member)
        if extracted is None:
            continue

        data = extracted.read()
        zi = zipfile.ZipInfo(member.name)
        # Preserve unix permissions (best-effort)
        zi.external_attr = (member.mode & 0o777) << 16
        zf.writestr(zi, data)
PY
}

main() {
  if ! command -v git >/dev/null 2>&1; then
    exit 0
  fi

  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -z "$repo_root" ]]; then
    exit 0
  fi

  cd "$repo_root"

  local pyproject="${repo_root}/pyproject.toml"
  if [[ ! -f "$pyproject" ]]; then
    exit 0
  fi

  # Only consider commits that touched pyproject.toml
  if ! git show --name-only --pretty=format: HEAD | grep -qx "pyproject.toml"; then
    exit 0
  fi

  local new_version old_version
  new_version="$(get_version_from_pyproject "$pyproject")"

  old_version=""
  if git show HEAD^:pyproject.toml >/dev/null 2>&1; then
    old_version="$(git show HEAD^:pyproject.toml | get_version_from_pyproject_content || true)"
  fi

  if [[ -z "$old_version" ]]; then
    # No baseline to compare (e.g. first commit) -> do nothing.
    exit 0
  fi

  if [[ "$new_version" == "$old_version" ]]; then
    exit 0
  fi

  # Prefer a "previous released" version from dist/ for display, if available.
  # This avoids confusing output when the git baseline doesn't match what was built locally.
  local display_old
  display_old="$(get_previous_version_from_dist "$new_version")"
  if [[ -z "$display_old" ]]; then
    display_old="$old_version"
  fi

  log "Detected version bump: ${display_old} -> ${new_version}"

  if ! "$PYTHON" -m build --help >/dev/null 2>&1; then
    log "ERROR: python -m build not available in the selected Python environment"
    log "ERROR: Install with: $PYTHON -m pip install build"
    exit 1
  fi

  log "Building wheel + sdist into dist/"
  "$PYTHON" -m build >/dev/null

  local sdist="dist/OctoPrint-Uptime-${new_version}.tar.gz"
  local zip="dist/OctoPrint-Uptime-${new_version}.zip"

  if [[ ! -f "$sdist" ]]; then
    log "Expected sdist not found: ${sdist}; skipping zip creation"
    exit 0
  fi

  log "Creating zip from sdist: ${zip}"
  rm -f "$zip"
  create_zip_from_sdist "$sdist" "$zip"

  log "Done: dist/ artifacts updated"
}

main "$@"
