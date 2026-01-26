# generate-diagrams.sh — helper script

What it does

This script runs `pyreverse` (from `pylint`) to analyse the plugin package, uses Graphviz (`dot`) to render DOT files to SVG, and falls back to PNG+`potrace` if direct SVG rendering is unavailable.

Prerequisites

- Python: install project docs requirements for `pyreverse`:

```bash
pip install -r ../requirements-docs.txt
```

- System utilities: `graphviz` (dot). Optional: `imagemagick` (`convert`) and `potrace` for fallback.

Usage

From the repository root:

```bash
./scripts/generate-diagrams.sh
```

Output

- The script writes final SVGs to `docs/reference/diagrams/`:
  - `classes.svg`
  - `classes_detailed.svg`
  - `packages.svg`

Notes

- CI regenerates these files automatically; the repository ignores generated SVGs and intermediate files. Do not commit the generated SVGs unless you have a specific reason.
- To retain DOT files for debugging, edit the script and comment out the cleanup step.
