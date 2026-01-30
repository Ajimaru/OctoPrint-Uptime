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
#   --extract            Run `pybabel extract` to refresh `translations/messages.pot`
#   --init <lang>        Initialize a new language from the POT into `translations/<lang>`
#   --update             Update existing PO files in `translations/` from POT
#   --compile            Compile translations; default compiles top-level translations
#                        and copies compiled catalogs into `octoprint_uptime/translations/`
#   --compile --plugin-only
#                        Compile only `octoprint_uptime/translations`
#   --compile --all      Compile both top-level and plugin translations
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

# path to babel.cfg used for extraction
BABEL_CFG="${REPO_ROOT}/babel.cfg"

usage() {
  cat <<'USAGE'
Usage: compile_translations.sh [--command] [args]

Commands:
  --extract                 Extract translatable strings into translations/messages.pot
  --init <lang>             Initialize a new language (e.g. --init de)
  --update                  Update existing PO files from translations/messages.pot
  --compile [--plugin-only|--all]
                            Compile translations. Default: compile top-level
                            translations and copy compiled catalogs into
                            octoprint_uptime/translations/ (single source: translations/)
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
  clean_obsolete() {
    echo "Cleaning obsolete PO entries (obsolete entries start with '#~')..."
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

  for mo in translations/*/LC_MESSAGES/*.mo; do
    lang_dir="$(basename "$(dirname "$(dirname "$mo")")")"
    target_dir="octoprint_uptime/translations/${lang_dir}/LC_MESSAGES"
    mkdir -p "$target_dir"
    echo "  -> $lang_dir: copying $(basename "$mo")"
    cp -a "$mo" "$target_dir/"
    # optionally copy the .po if present (keeps package in-sync for reviewers)
    # default: do NOT copy .po to avoid creating a second source of truth
    # enable by setting environment variable: COPY_PO=true
    po="translations/${lang_dir}/LC_MESSAGES/$(basename "${mo%.mo}.po")"
    if [[ "${COPY_PO:-false}" == "true" && -f "$po" ]]; then
      cp -a "$po" "$target_dir/"
    fi
  done
  shopt -u nullglob
}

compile_plugin() {
  echo "Compiling plugin translations (octoprint_uptime/translations)..."
  "$VENV_PYBABEL" compile -d octoprint_uptime/translations || {
    echo "pybabel compile failed for plugin translations" >&2
    return 1
  }
}

compile_top_level() {
  echo "Compiling top-level translations (translations)..."
  "$VENV_PYBABEL" compile -d translations || {
    echo "pybabel compile failed for top-level translations" >&2
    return 1
  }
  copy_compiled_to_package
}
handle_extract() {
  echo "Extracting translatable strings to translations/messages.pot..."
  if [[ -f "$BABEL_CFG" ]]; then
    "$VENV_PYBABEL" extract -F "$BABEL_CFG" -o translations/messages.pot . || return 1
  else
    echo "babel.cfg not found at $BABEL_CFG; cannot run extract" >&2
    return 1
  fi
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
  cmd="compile"
fi

case "$cmd" in
  extract)
    handle_extract
    ;;
  init)
    handle_init "$1"
    ;;
  update)
    handle_update
    ;;
  compile)
    case "${1:-}" in
      --plugin-only)
        compile_plugin
        ;;
      --all)
        compile_top_level
        compile_plugin
        ;;
      "" )
        compile_top_level
        ;;
      *)
        echo "Unknown compile option: ${1}" >&2
        usage
        exit 2
        ;;
    esac
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
