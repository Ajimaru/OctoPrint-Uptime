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

## JavaScript docs generation

This repository generates JavaScript API docs from JSDoc comments using `jsdoc-to-markdown` (`jsdoc2md`). The helper script `./scripts/generate-jsdocs.sh` writes Markdown to `docs/api/javascript.md` (which is generated but not committed; see `.gitignore`).

To install the JavaScript doc tooling locally, run from the repository root:

```bash
npm install
```

This will install the project's Node devDependencies (if present), including `jsdoc-to-markdown`.

If you prefer to install only the tools without relying on package.json, run:

```bash
npm install --save-dev jsdoc jsdoc-to-markdown
```

Or run `npx jsdoc-to-markdown` to execute the tool without installing it permanently.

- The pre-commit hook runs `./scripts/generate-jsdocs.sh` but now passes only changed filenames to the script for performance. `generate-jsdocs.sh` documents only the passed files when invoked by pre-commit; when run without arguments it documents the whole package.

Usage examples:

```bash
# Generate docs for the whole package
./scripts/generate-jsdocs.sh
```

## Output

- The script writes final SVGs to `docs/reference/diagrams/`:
  - `classes.svg`
  - `classes_detailed.svg`
  - `packages.svg`

## Notes

- CI regenerates these files automatically; the repository ignores generated SVGs and intermediate files. Do not commit the generated SVGs unless you have a specific reason.
- To retain DOT files for debugging, edit the script and comment out the cleanup step.
