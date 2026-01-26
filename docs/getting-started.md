# Getting started

- Install docs dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
```

- Generate JS docs (if desired):

```bash
# recommended: run the repository setup helper which installs Node dev deps
.development/setup_dev.sh

# then generate JS docs
./scripts/generate-jsdocs.sh
```

- Serve docs locally:

```bash
mkdocs serve
```

## Developer utilities

When working on translations during development, use the repository helper which wraps `pybabel` and copies compiled catalogs into the package for runtime testing.

From the repository root:

```bash
# refresh POT
./.development/compile_translations.sh extract

# merge POT into existing PO files
./.development/compile_translations.sh update

# compile and copy into octoprint_uptime/translations/
./.development/compile_translations.sh compile
```

If a commit fails due to translations being out of sync, run the `update` command above, add the changed PO files, and re-commit.

## Notes

This document is contributor-focused and omits end-user installation guidance such as package dependencies. For user-facing instructions about uptime dependencies (for example how to install `psutil` in your OctoPrint virtualenv), see the `Installation` and `Dependencies` sections in the [project README](../README.md).
