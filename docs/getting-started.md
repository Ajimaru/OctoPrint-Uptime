# Getting started

- Create and activate a **separate** Python virtual environment for docs to avoid dependency conflicts:

```bash
python -m venv venv-docs
source venv-docs/bin/activate  # On Windows: venv-docs\Scripts\activate
```

- Install docs dependencies in the activated venv:

```bash
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
```

- Generate JS docs (if desired):

```bash
./scripts/generate-jsdocs.sh
```

- Serve docs locally:

```bash
mkdocs serve
```

## Developer utilities

### Translation Management

When working on translations during development, use the repository helper script to manage translations.

To perform a clean translation build that removes stale or old translation files, run:

```bash
FORCE_CLEAN=true ./.development/compile_translations.sh --all
```

If a commit fails due to translations being out of sync, run the compile command above, add the changed PO/MO files, and re-commit.

Note: the repository's translations pre-commit check is non-destructive; it reports when PO/MO files would change and fails the commit so you can run the update step manually.

### Windows

The repository helper scripts are POSIX shell scripts and expect a Bash
environment. On Windows prefer running the helper scripts from Git Bash.
