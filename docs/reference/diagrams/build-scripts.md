# Build Scripts - Flow Diagrams

This section contains detailed flow diagrams for the build and documentation helper scripts in the `/scripts` directory.

## Quick Overview

The OctoPrint-Uptime project uses several helper scripts to automate documentation and build tasks:

- **[Overview Diagram](build-scripts/index.html)** High-level relationship between scripts and their outputs

## Individual Scripts

### Documentation & Diagram Generation

- **[generate-diagrams.sh](build-scripts/generate-diagrams.html)** Generates UML class and package diagrams
  - Uses `pyreverse` (from `pylint`) for Python AST analysis
  - Renders with Graphviz (`dot`) or falls back to ImageMagick + potrace
  - Outputs SVG diagrams to `docs/reference/diagrams/`

- **[generate-jsdocs.sh](build-scripts/generate-jsdocs.html)** Generates JavaScript API documentation
  - Uses `jsdoc-to-markdown` for JSDoc comment extraction
  - Generates Markdown documentation for `octoprint_uptime/static/js/**/*.js`
  - Outputs to `docs/api/javascript.md`

### Platform Support

- **win-bash-wrapper.sh** — Utility script that re-executes Bash scripts under Git Bash on Windows
  - Used by build scripts to ensure consistent behavior across platforms
  - No separate diagram (helper script)

---

For more information about these scripts, see [Scripts README](https://github.com/Ajimaru/OctoPrint-Uptime/blob/main/scripts/README.md).
