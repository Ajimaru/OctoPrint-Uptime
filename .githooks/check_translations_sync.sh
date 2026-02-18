#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
if _dir="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"; then
  _SCRIPT_DIR_HINT="$_dir"
else
  _SCRIPT_DIR_HINT="$(dirname "$0")"
fi
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
VENV_PYTHON="./venv/bin/python3"
PYBABEL=""
if [[ -x "$VENV_PYBABEL" ]]; then
  PYBABEL="$VENV_PYBABEL"
else
  if command -v pybabel >/dev/null 2>&1; then
    PYBABEL="$(command -v pybabel)"
  else
    echo "pybabel not found in ./venv or system PATH. Install dev requirements: pip install Babel" >&2
    exit 1
  fi
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

# run pybabel update on the temporary copy (capture output for diagnostics)
if ! output="$($PYBABEL update -i translations/messages.pot -d "$tmpdir"/translations 2>&1)"; then
    echo "pybabel failed while updating temporary translations. Output follows:" >&2
    printf '%s\n' "$output" >&2
  exit 1
fi

# mirror compile_translations behavior: autofill translations in temp copy if argostranslate is available
if [[ -x "$VENV_PYTHON" ]]; then
  "$VENV_PYTHON" - <<'AUTOFILL' "$tmpdir" "$REPO_ROOT" || true
import os
import sys
from pathlib import Path

tmpdir = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
translations = tmpdir / "translations"

try:
  import polib
except ImportError:
  sys.exit(0)

try:
  import argostranslate.package
  import argostranslate.translate
except ImportError:
  sys.exit(0)

def has_model(from_code: str, to_code: str) -> bool:
  try:
    installed = argostranslate.translate.get_installed_languages()
    has_from = next((inst for inst in installed if inst.code == from_code), None)
    has_to = next((inst for inst in installed if inst.code == to_code), None)
    return has_from is not None and has_to is not None
  except Exception:
    return False

def translate_text(text: str, from_code: str, to_code: str) -> str:
  try:
    return argostranslate.translate.translate(text, from_code, to_code)
  except Exception:
    return ""

def autofill_language(lang: str, source_lang: str = "en"):
  po_path = translations / lang / "LC_MESSAGES" / "messages.po"
  if not po_path.exists():
    return 0
  if not has_model(source_lang, lang):
    return 0

  po = polib.pofile(str(po_path))
  changed = 0
  for entry in po:
    if not entry.msgstr or entry.msgstr.strip() == "":
      src = entry.msgid
      tr = translate_text(src, source_lang, lang)
      if tr:
        entry.msgstr = tr
        if "fuzzy" not in entry.flags:
          entry.flags.append("fuzzy")
        entry.comment = (entry.comment + "\n" if entry.comment else "") + "Auto-translated by argostranslate"
        changed += 1
  if changed > 0:
    po.save()
  return changed

source_lang = os.environ.get("AUTOFILL_SOURCE_LANG", "en")
langs = []
if translations.exists():
  for child in translations.iterdir():
    if (child / "LC_MESSAGES" / "messages.po").exists():
      langs.append(child.name)

total = 0
for lang in langs:
  if lang == source_lang:
    continue
  total += autofill_language(lang, source_lang)
AUTOFILL
fi

# mirror compile_translations behavior: remove obsolete (#~) entries in temp copy
if [[ -x "$VENV_PYTHON" ]]; then
  FORCE_CLEAN=true "$VENV_PYTHON" - <<'PY' "$tmpdir" || true
import os
import sys
from pathlib import Path

tmpdir = Path(sys.argv[1])
translations = tmpdir / "translations"

try:
  import polib
except Exception:
  print("polib not available; skipping obsolete cleanup in temp copy", file=sys.stderr)
  sys.exit(0)

def iter_po_files(root: Path):
  if not root.exists():
    return
  for lang_dir in root.iterdir():
    po = lang_dir / "LC_MESSAGES" / "messages.po"
    if po.exists():
      yield po

total = 0
for po in iter_po_files(translations):
  pofile = polib.pofile(str(po))
  obsolete = [e for e in pofile if e.obsolete]
  if not obsolete:
    continue
  for entry in obsolete:
    try:
      pofile.remove(entry)
    except ValueError:
      pass
  pofile.save()
  total += len(obsolete)

if total:
  print(f"Removed {total} obsolete entries from temp PO files.")
PY
fi

# normalize PO files in temp copy to match build output (polib reads/writes in canonical format)
if [[ -x "$VENV_PYTHON" ]]; then
  "$VENV_PYTHON" - <<'NORMALIZE' "$tmpdir" || true
import sys
from pathlib import Path

tmpdir = Path(sys.argv[1])
translations = tmpdir / "translations"

try:
  import polib
except ImportError:
  sys.exit(0)

def iter_po_files(root: Path):
  if not root.exists():
    return
  for lang_dir in root.iterdir():
    po = lang_dir / "LC_MESSAGES" / "messages.po"
    if po.exists():
      yield po

for po in iter_po_files(translations):
  try:
    pofile = polib.pofile(str(po))
    pofile.save()
  except Exception:
    pass
NORMALIZE
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
