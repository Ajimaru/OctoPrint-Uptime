#!/usr/bin/env bash
set -euo pipefail

# Check that top-level PO files are up-to-date with the POT.
# This script is intended to be called from a pre-commit hook.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VENV_PYBABEL="./venv/bin/pybabel"
if [[ ! -x "$VENV_PYBABEL" ]]; then
  echo "pybabel not found in ./venv. Install dev requirements: ./.development/setup_dev.sh" >&2
  exit 1
fi

if [[ ! -f translations/messages.pot ]]; then
  echo "POT file not found at translations/messages.pot. Run './.development/compile_translations.sh extract' first." >&2
  exit 1
fi

echo "Checking translations against POT (no changes will be made to working tree)..."

tmpdir=$(mktemp -d)
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

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

printf '%s\n' "To update the real PO files run:"
printf '%s\n' "  ./.development/compile_translations.sh update"
printf '%s\n' "Then review and commit the updated PO (and compiled MO if you keep them)."
exit 1
