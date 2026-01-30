# Contributing

Thanks for your interest in contributing to the OctoPrint-Uptime plugin!

## Quick Start

1. Fork the repository
2. Create a feature branch: `git checkout -b wip/my-feature`
3. Write tests for new features
4. Submit a pull request
5. **_TODO_** describe manual installation of requirements-dev.txt
6. Please follow our [Code of Conduct](CODE_OF_CONDUCT.md).
7. Note: `main` is protected on GitHub, so changes go through PRs.

---

## Before you start

- Please keep issues and pull requests focused: **one bug/feature per PR**.
- If your change affects user-facing behavior, please describe how you tested it.

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

## Automatic pre-commit autoupdate

If you want your local hooks to attempt to keep themselves updated before running,
set the environment variable `PRECOMMIT_AUTOUPDATE=1`. The repo-local wrapper will
run `pre-commit autoupdate` at most once per 24 hours. This is opt-in — running
autoupdate on every commit by default is not recommended because it may change
`.pre-commit-config.yaml` unexpectedly.

To enable:

```bash
export PRECOMMIT_AUTOUPDATE=1
```

Review any changes created by `autoupdate` before committing them.

## Running tests

```bash
pytest
```

## Pre-commit (formatting & linting)

We use `pre-commit` to enforce consistent formatting and basic quality checks.

```bash
pre-commit run --hook-stage manual --all-files
```

**_TODO_** describe how to manually enables repo-local git hooks via `core.hooksPath=.githooks`.

### Translations sync check

We added a repository-local pre-commit hook `check-translations` that ensures PO files in `translations/` are kept in sync with `translations/messages.pot`.

If a commit is rejected due to the translations check, update the PO files and re-commit.

### Prettier and formatting

We use a project-local Prettier for JS/HTML/Markdown formatting. The `pre-commit`
hook runs a helper script located at `.githooks/prettier-hook.sh`.
The hook will prefer the repository `node_modules/.bin/prettier` if present, otherwise it will
fall back to `npx --yes prettier --write`.

Note: the generated API document `docs/api/python.md` is intentionally excluded
from automatic formatting to avoid changes from generated artifacts.

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

## What not to commit

Do not commit generated or environment-specific files such as:

- `dist/`, `build/`, `*.egg-info/`
- `__pycache__/`, `.pytest_cache/`, `.coverage/`, `htmlcov/`
- local virtual environments (`venv/`)
- IDE/editor configs (`.idea/`, `.vscode/`)
