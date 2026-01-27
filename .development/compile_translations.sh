#!/usr/bin/env bash

# Description: Manage translation workflow for the repository: extract, init, update, and compile PO/MO using pybabel.
# Behavior / subcommands:
#  extract             - run `pybabel extract` to refresh `translations/messages.pot`
#  init <lang>         - initialize a new language from the POT into `translations/<lang>`
#  update              - update existing PO files in `translations/` from POT
#  compile             - compile top-level `translations/` and copy compiled catalogs
#                        into `octoprint_uptime/translations/` (Single Source: translations/)
#  compile --plugin-only
#                      - compile only `octoprint_uptime/translations`
#  compile --all       - compile both top-level and plugin translations
#
# Usage examples:
#   ./compile_translations.sh extract
#   ./compile_translations.sh init de
#   ./compile_translations.sh update
#   ./compile_translations.sh compile          # default: compile top-level and copy to package
#   ./compile_translations.sh compile --all    # compile both top-level and plugin translations
#   ./compile_translations.sh compile --plugin-only

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
Usage: compile_translations.sh <command> [args]

Commands:
  extract                 Extract translatable strings into translations/messages.pot
  init <lang>             Initialize a new language (e.g. init de)
  update                  Update existing PO files from translations/messages.pot
  compile [--plugin-only|--all]
                          Compile translations; default compiles top-level translations
                          and copies compiled catalogs into octoprint_uptime/translations.
USAGE
}

copy_compiled_to_package() {
  echo "Copying compiled catalogs from translations/ to octoprint_uptime/translations/..."
  shopt -s nullglob
  for mo in translations/*/LC_MESSAGES/*.mo; do
    # mo -> translations/<lang>/LC_MESSAGES/messages.mo
    lang_dir="$(basename "$(dirname "$(dirname "$mo")")")"
    target_dir="octoprint_uptime/translations/${lang_dir}/LC_MESSAGES"
    mkdir -p "$target_dir"
    echo "  -> $lang_dir: copying $(basename "$mo")"
    cp -a "$mo" "$target_dir/"
    # also copy the .po if present (keeps package in-sync for reviewers)
    po="translations/${lang_dir}/LC_MESSAGES/$(basename "${mo%.mo}.po")"
    if [[ -f "$po" ]]; then
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
}

cmd="${1:-compile}"
case "$cmd" in
  extract)
    handle_extract
    ;;
  init)
    handle_init "$2"
    ;;
  update)
    handle_update
    ;;
  compile)
    case "${2:-}" in
      --plugin-only)
        compile_plugin
        ;;
      --all)
        compile_top_level
        compile_plugin
        ;;
      *)
        compile_top_level
        ;;
    esac
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac

echo "Done."
