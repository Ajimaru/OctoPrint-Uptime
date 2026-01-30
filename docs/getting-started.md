# Getting started

- Install docs dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
```

- Generate JS docs (if desired):

````bash
- Install docs dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
````

- Generate JS docs (if desired):

```bash
./scripts/generate-jsdocs.sh
```

- Serve docs locally:

```bash
mkdocs serve
```

## Developer utilities

### Windows

The repository helper scripts are POSIX shell scripts and expect a Bash
environment. On Windows prefer running the helper scripts from Git Bash.

When working on translations during development, use the repository helper which wraps `pybabel` and copies compiled catalogs into the package for runtime testing.

From the repository root:

```bash
./scripts/compile_translations.sh
```

If a commit fails due to translations being out of sync, run the `update` command above, add the changed PO files, and re-commit.

Note: the repository's translations pre-commit check is non-destructive — it reports when PO files would change and fails the commit so you can run the update step manually.

## Notes

This document is contributor-focused and omits end-user installation guidance such as package dependencies. For user-facing instructions about uptime dependencies (for example how to install `psutil` in your OctoPrint virtualenv), see the `Installation` and `Dependencies` sections in this documentation or the [project website](https://github.com/Ajimaru/OctoPrint-Uptime#readme).
