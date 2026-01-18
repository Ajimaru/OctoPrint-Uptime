# Contributing

Thanks for your interest in contributing to the OctoPrint-Uptime plugin.

## Before you start

- Please keep issues and pull requests focused: **one bug/feature per PR**.
- If your change affects user-facing behavior, please describe how you tested it.

## GitHub workflow (protected `main`)

This repository uses a protected default branch (`main`). Please:

- Create a feature branch in your fork (or within the repo if you have access)
- Open a Pull Request into `main` (direct pushes to `main` are blocked)
- Ensure required CI checks pass before merging
- Resolve review conversations (if any)

## Bug reports

When reporting a bug, please include:

- OctoPrint version
- Plugin version
- Steps to reproduce (as minimal as possible)
- Relevant log excerpts
- Screenshots if applicable

## Development setup

This plugin is a standard Python project.

- Create and activate a virtual environment
- Install in editable mode

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[develop]"
```

If you use the helper scripts, see `.development/README.md`.

Notes:

- The helper scripts target a Python 3.10+ development environment. The plugin runtime supports Python 3.10+.
- If you downloaded the repo as a ZIP, executable bits may be missing. In that case run `bash .development/setup_dev.sh` (or `chmod +x .development/setup_dev.sh`).

## Running tests

```bash
pytest
```

## Pre-commit (formatting & linting)

We use `pre-commit` to enforce consistent formatting and basic quality checks.

```bash
pre-commit run --hook-stage manual --all-files
```

If you use `.development/setup_dev.sh`, it enables repo-local git hooks via `core.hooksPath=.githooks`.

## Coding style

- Indentation: **4 spaces** (no tabs)
- Language: **English** in code, comments, docs, and commit messages
- No `print()` for logging: use OctoPrint plugin logging (`self._logger`)
- Keep changes minimal and focused; avoid unrelated refactors
- Do not add dead code (e.g. commented-out experiments)

### Frontend & styles

- Prefer changing **LESS** sources (`octoprint_uptime/static/less`) over compiled CSS.
- Avoid inline styles in templates.

## Internationalization (i18n)

- All user-facing strings must be translatable.
- In templates use `{{ _('...') }}`.
- In JavaScript use OctoPrint's `gettext`.

If you add or change strings, update and compile catalogs:

```bash
pybabel extract -F babel.cfg -o translations/messages.pot .
pybabel update -i translations/messages.pot -d translations
pybabel compile -d translations
```

## What not to commit

Do not commit generated or environment-specific files such as:

- `dist/`, `build/`, `*.egg-info/`
- `__pycache__/`, `.pytest_cache/`, `.coverage/`, `htmlcov/`
- local virtual environments (`venv/`, `.venv/`)
- IDE/editor configs (`.idea/`, `.vscode/`)
