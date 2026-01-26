# generate-diagrams.sh — helper script

## What it does

This script runs `pyreverse` (from `pylint`) to analyse the plugin package, uses Graphviz (`dot`) to render DOT files to SVG, and falls back to PNG+`potrace` if direct SVG rendering is unavailable.

## Prerequisites

- Python: install the project development requirements which include `pyreverse` (provided by `pylint`)—this lives in `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
```

- System utilities: `graphviz` (dot). Optional: `imagemagick` (`convert`) and `potrace` for fallback.

## Usage

From the repository root:

```bash
./scripts/generate-diagrams.sh
```

## Translations helper

For working with translations during development, use the repository helper which wraps `pybabel` and copies compiled catalogs into the plugin package for runtime testing.

From the repository root:

```bash
./.development/compile_translations.sh extract    # refresh translations/messages.pot
./.development/compile_translations.sh update     # merge POT into existing PO files
./.development/compile_translations.sh init de    # create a new language (example)
./.development/compile_translations.sh compile    # compile top-level translations and copy into octoprint_uptime/translations/
./.development/compile_translations.sh compile --plugin-only  # compile only package translations
./.development/compile_translations.sh compile --all          # compile both top-level and plugin translations
```

Run `./.development/compile_translations.sh --help` for full details.

## JavaScript docs generation

This repository generates JavaScript API docs from JSDoc comments using `jsdoc-to-markdown` (`jsdoc2md`). The helper script `./scripts/generate-jsdocs.sh` writes Markdown to `docs/api/javascript.md`.

- `./.development/setup_dev.sh` will install Node dev dependencies (`npm install`) when `npm` is available so `jsdoc-to-markdown` is available locally. If you prefer manual control, run `npm install --save-dev jsdoc jsdoc-to-markdown` yourself.
- The pre-commit hook runs `./scripts/generate-jsdocs.sh` but now passes only changed filenames to the script for performance. `generate-jsdocs.sh` documents only the passed files when invoked by pre-commit; when run without arguments it documents the whole package.

Usage examples:

```bash
# Generate docs for the whole package
./scripts/generate-jsdocs.sh

# When called via pre-commit it will receive the changed filenames automatically
```

## Output

- The script writes final SVGs to `docs/reference/diagrams/`:
  - `classes.svg`
  - `classes_detailed.svg`
  - `packages.svg`

## Notes

- CI regenerates these files automatically; the repository ignores generated SVGs and intermediate files. Do not commit the generated SVGs unless you have a specific reason.
- To retain DOT files for debugging, edit the script and comment out the cleanup step.
