#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
_SCRIPT_DIR_HINT="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd || dirname "$0")"
REPO_ROOT="$(cd "$_SCRIPT_DIR_HINT/.." >/dev/null 2>&1 && pwd || echo "$_SCRIPT_DIR_HINT")"
WRAPPER="$REPO_ROOT/scripts/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
  if [ -x "$WRAPPER" ]; then
    exec "$WRAPPER" "$0" "$@"
  elif command -v bash >/dev/null 2>&1; then
    exec bash "$0" "$@"
  fi
fi

# Helper: verify that top-level PO catalogs are synchronized with translations/messages.pot
# Behavior:
#  - Creates a temporary copy of `translations/`, runs `pybabel update` against the POT
#    on the temporary copy and compares it to the real `translations/` directory.
#  - Performs a read-only check (does not modify the working tree); intended for pre-commit.
#  - Exits 0 when translations are up-to-date; otherwise prints diffs and exits non-zero.
# Usage:
#  - Typically invoked from a pre-commit hook or CI to ensure translators are synchronized.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VENV_PYBABEL="./venv/bin/pybabel"
if [[ ! -x "$VENV_PYBABEL" ]]; then
  echo "pybabel not found in ./venv. Install dev requirements: <TODO> describe how to manually install pybabel in the virtual environment <TODO>" >&2
  exit 1
fi

if [[ ! -f translations/messages.pot ]]; then
  echo "POT file not found at translations/messages.pot. Update .pot files first." >&2
  exit 1
fi

echo "Checking translations against POT (no changes will be made to working tree)..."

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# copy translations to temporary location
cp -a translations "$tmpdir"/translations

# run pybabel update on the temporary copy
if ! "$VENV_PYBABEL" update -i translations/messages.pot -d "$tmpdir"/translations >/dev/null 2>&1; then
  echo "pybabel failed while updating temporary translations. Ensure the venv is healthy." >&2
  exit 1
fi

# check for any differences between real translations and the updated temp copy
if diff -r -q translations "$tmpdir"/translations >/dev/null 2>&1; then
  printf '%s\n' "Translations are up-to-date."
  exit 0
fi

printf '%s\n' "ERROR: Translations are out of sync with translations/messages.pot. The following differences were detected:"
diff -r -q translations "$tmpdir"/translations || true

printf '%s\n' "Update the real PO files."
printf '%s\n' "Then review and commit the updated PO (and compiled MO if you keep them)."
exit 1
