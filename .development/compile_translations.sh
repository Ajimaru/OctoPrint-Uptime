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

# Description: Manage translation workflow for the repository: extract, init, update, and
# compile PO/MO using pybabel.
#
# The canonical, single source of truth for translations is the top-level `translations/`
# directory. Compiled `.mo` files are copied into `octoprint_uptime/translations/`.
# By default the script does NOT copy `.po` files into the package to avoid creating a
# second source of truth; enable copying of `.po` files only by setting the environment
# variable `COPY_PO=true` when invoking the script.
#
# Behavior / subcommands (all commands require a leading `--`):
#   --init <lang>        Initialize a new language from the POT into `translations/<lang>`
#   --update             Update existing PO files in `translations/` from POT
#   --compile            Compile translations; default compiles top-level
#                        translations and copies compiled catalogs into
#   --clean              Remove obsolete ("#~") entries from top-level PO files.
#                        Use `FORCE_CLEAN=true` to skip interactive confirmation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VENV_PYBABEL="./venv/bin/pybabel"
if [[ ! -x "$VENV_PYBABEL" ]]; then
  echo "pybabel not found in ./venv. Install Babel into the venv first: ./venv/bin/python -m pip install Babel" >&2
  exit 1
fi

# Prefer the venv's python3 when available for running helper scripts (autofill, cleaners)
VENV_PYTHON="./venv/bin/python3"

# Global flag: if set, remove fuzzy entries before compiling
REMOVE_FUZZY=false
# Consume a global --remove-fuzzy from the argument list (if present)
if [[ "$#" -gt 0 ]]; then
  new_args=()
  for _a in "$@"; do
    if [[ "$_a" == "--remove-fuzzy" ]]; then
      REMOVE_FUZZY=true
    else
      new_args+=("$_a")
    fi
  done
  # reset positional parameters to remaining args (commands)
  if (( ${#new_args[@]} )); then
    set -- "${new_args[@]}"
  else
    set --
  fi
fi

# path to babel.cfg used for extraction
BABEL_CFG="${REPO_ROOT}/babel.cfg"

usage() {
  cat <<'USAGE'
Usage: compile_translations.sh [--command] [args]

Commands:
  --init <lang>             Initialize a new language (e.g. --init de)
  --all                     Compile both top-level and plugin translations
  --plugin-only             Compile only plugin translations (octoprint_uptime/translations)
  --clean                   Remove obsolete ("#~") entries from top-level PO files
                            (set FORCE_CLEAN=true to skip interactive prompts)

Notes:
  - The script does NOT copy `.po` files into the package by default. To copy
    `.po` files as well (for reviewer convenience), set `COPY_PO=true` in the
    environment before running the script.

USAGE
}

copy_compiled_to_package() {
  echo "Copying compiled catalogs from translations/ to octoprint_uptime/translations/..."
  shopt -s nullglob
  for mo in translations/*/LC_MESSAGES/*.mo; do
    lang_dir="$(basename "$(dirname "$(dirname "$mo")")")"
    target_dir="octoprint_uptime/translations/${lang_dir}/LC_MESSAGES"
    mkdir -p "$target_dir"
    echo "  -> $lang_dir: copying $(basename "$mo")"
    cp -a "$mo" "$target_dir/"
    # optionally copy the .po if present (keeps package in-sync for reviewers)
    # enable by setting environment variable: COPY_PO=true
    po="translations/${lang_dir}/LC_MESSAGES/$(basename "${mo%.mo}.po")"
    if [[ "${COPY_PO:-false}" == "true" && -f "$po" ]]; then
      cp -a "$po" "$target_dir/"
    fi
  done
  shopt -u nullglob
}

clean_obsolete() {
  echo "Cleaning obsolete PO entries (obsolete entries start with '#~')..."
  if [[ -x "$VENV_PYTHON" ]] && [[ -f "$REPO_ROOT/.development/clean_obsolete.py" ]]; then
    if FORCE_CLEAN=true "$VENV_PYTHON" "$REPO_ROOT/.development/clean_obsolete.py"; then
      return 0
    else
      echo "Python clean_obsolete failed; falling back to msgattrib if available." >&2
    fi
  fi
  if ! command -v msgattrib >/dev/null 2>&1; then
    echo "msgattrib not found. Please install gettext (msgattrib) to use --clean." >&2
    return 1
  fi
  shopt -s nullglob
  for po in translations/*/LC_MESSAGES/*.po; do
    echo "Processing: $po"
    if [[ "${FORCE_CLEAN:-false}" == "true" ]]; then
      if msgattrib --no-obsolete "$po" >"${po}.clean"; then
        mv "${po}.clean" "$po"
        echo "  -> cleaned $po"
      else
        echo "  -> msgattrib failed for $po" >&2
      fi
    else
      read -r -p "  Remove obsolete entries from $po? [y/N] " ans
      case "$ans" in
        [Yy]*)
          if msgattrib --no-obsolete "$po" >"${po}.clean"; then
            mv "${po}.clean" "$po"
            echo "  -> cleaned $po"
          else
            echo "  -> msgattrib failed for $po" >&2
          fi
          ;;
        *)
          echo "  -> skipped $po"
          ;;
      esac
    fi
  done
  shopt -u nullglob
}

compile_plugin() {
  echo "Compiling plugin translations (octoprint_uptime/translations)..."
  # Prefer msgfmt (gettext) so we can include fuzzy entries by default.
  if command -v msgfmt >/dev/null 2>&1; then
    shopt -s nullglob
    for po in octoprint_uptime/translations/*/LC_MESSAGES/*.po; do
      mo="${po%.po}.mo"
      if [[ "$REMOVE_FUZZY" == "true" ]]; then
        # remove fuzzy entries and compile
        if command -v msgattrib >/dev/null 2>&1; then
          msgattrib --no-fuzzy "$po" >"${po}.nofuzzy" && mv "${po}.nofuzzy" "$po" || echo "msgattrib failed for $po" >&2
        fi
        msgfmt -o "$mo" "$po" || echo "msgfmt failed for $po" >&2
      else
        msgfmt --use-fuzzy -o "$mo" "$po" || echo "msgfmt failed for $po" >&2
      fi
    done
    shopt -u nullglob
  else
    "$VENV_PYBABEL" compile -d octoprint_uptime/translations || {
      echo "pybabel compile failed for plugin translations" >&2
      return 1
    }
  fi
}

compile_top_level() {
  echo "Updating POT (translations/messages.pot) from sources..."
  if [[ -f "$BABEL_CFG" ]]; then
    echo "Extracting translatable strings to translations/messages.pot..."
    if ! "$VENV_PYBABEL" extract --sort-output -F "$BABEL_CFG" -o translations/messages.pot .; then
      echo "Warning: updating POT failed — continuing with existing POT" >&2
    fi
  else
    echo "babel.cfg not found; skipping POT update" >&2
  fi

  # Update PO files from the POT so the repository's PO files stay in sync
  if [[ -f translations/messages.pot ]]; then
    echo "Updating PO files from POT..."
    if ! "$VENV_PYBABEL" update -i translations/messages.pot -d translations >/dev/null 2>&1; then
      echo "Warning: pybabel update failed; PO files may not be synchronized." >&2
    fi
    # Normalize PO files using polib to ensure consistent formatting for pre-commit
    if [[ -x "$VENV_PYTHON" ]]; then
      "$VENV_PYTHON" - <<'NORMALIZE' || true
import sys
from pathlib import Path

translations = Path("translations")
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
  fi

  # Attempt to autofill missing translations using Argos (local) if available.
  if [[ -x "$VENV_PYTHON" ]] && [[ -f "$REPO_ROOT/.development/autofill_translations.py" ]]; then
    echo "Running autofill (.development/autofill_translations.py)..."
    if ! "$VENV_PYTHON" "$REPO_ROOT/.development/autofill_translations.py"; then
      echo "Autofill script failed or skipped; continuing." >&2
    fi
  fi

  echo "Compiling top-level translations (translations)..."
  # If requested, remove fuzzy entries before compiling.
  if [[ "$REMOVE_FUZZY" == "true" ]]; then
    if ! command -v msgattrib >/dev/null 2>&1; then
      echo "msgattrib not found; cannot remove fuzzy entries. Proceeding without removal." >&2
    else
      shopt -s nullglob
      for po in translations/*/LC_MESSAGES/*.po; do
        echo "Removing fuzzy entries from: $po"
        msgattrib --no-fuzzy "$po" >"${po}.nofuzzy" && mv "${po}.nofuzzy" "$po" || echo "msgattrib failed for $po" >&2
      done
      shopt -u nullglob
    fi
  fi

  # Prefer msgfmt to allow including fuzzy translations by default.
  if command -v msgfmt >/dev/null 2>&1; then
    shopt -s nullglob
    for po in translations/*/LC_MESSAGES/*.po; do
      mo="${po%.po}.mo"
      if [[ "$REMOVE_FUZZY" == "true" ]]; then
        msgfmt -o "$mo" "$po" || echo "msgfmt failed for $po" >&2
      else
        msgfmt --use-fuzzy -o "$mo" "$po" || echo "msgfmt failed for $po" >&2
      fi
    done
    shopt -u nullglob
  else
    "$VENV_PYBABEL" compile -d translations || {
      echo "pybabel compile failed for top-level translations" >&2
      return 1
    }
  fi
  copy_compiled_to_package
  # After copying compiled catalogs into the package, offer to remove obsolete
  # entries from the top-level PO files. This keeps PO files in sync with the POT
  # and avoids leaving obsolete `#~` entries around.
  clean_obsolete
}

handle_init() {
  local lang="$1"
  if [[ -z "$lang" ]]; then
    echo "init requires a language code (e.g. de)" >&2
    return 2
  fi
  if [[ ! -f translations/messages.pot ]]; then
    echo "POT file not found. Run 'extract' first." >&2
    return 1
  fi
  # Attempt to install an Argos English-><lang> package into the venv
  if [[ -x "$VENV_PYTHON" ]]; then
    echo "Attempting to install Argos en->$lang model into venv (if available)..."
    if ! "$VENV_PYTHON" - <<PY
from __future__ import print_function
try:
    from argostranslate import package
    pkgs = package.get_available_packages()
    for p in pkgs:
        if getattr(p, 'from_code', '') == 'en' and getattr(p, 'to_code', '') == '${lang}':
            try:
                print('Installing', p)
                p.install()
                print('Installed en->${lang} Argos package')
            except Exception as e:
                print('Failed to install Argos package:', e)
            break
    else:
        print('No en->${lang} Argos package found')
except Exception as e:
    print('argostranslate not available or install failed:', e)
PY
    then
      echo "Argos model install attempt failed; continuing." >&2
    fi
  fi
  echo "Initializing language: $lang"
  "$VENV_PYBABEL" init -i translations/messages.pot -d translations -l "$lang" || return 1
}

handle_update() {
  if [[ ! -f translations/messages.pot ]]; then
    echo "POT file not found. Run 'extract' first." >&2
    return 1
  fi
  echo "Updating PO files from POT..."
  "$VENV_PYBABEL" update -i translations/messages.pot -d translations || return 1
    clean_obsolete
}

if [[ "$#" -gt 0 ]]; then
  first="$1"
  if [[ "$first" == --* ]]; then
    cmd="${first#--}"
    shift
  else
    echo "Commands must be given with a leading '--', e.g. --extract or --compile" >&2
    usage
    exit 2
  fi
else
  cmd="__default__"
fi

case "$cmd" in
  init)
    handle_init "$1"
    ;;
  update)
     echo "The '--update' command has been removed. Run the script without arguments to update PO files and compile." >&2
     exit 2
     ;;
  plugin-only)
    compile_plugin
    ;;
  all)
    compile_top_level
    compile_plugin
    ;;
  __default__)
    export FORCE_CLEAN=true
    compile_top_level
    ;;
  help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac

echo "Done."
