
# Contributing

Thanks for your interest in contributing to the OctoPrint-Uptime plugin!

## Quick Start

1. Fork the repository
2. Create a feature branch: `git checkout -b wip/my-feature`
3. Write tests for new features
4. Submit a pull request
5. For local development scripts (setup, restart helper, post-commit build hook, performance monitor), see [.development/README.md](.development/README.md).
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

### Using the repository helper script (recommended)

The repository provides a helper script at `.development/setup_dev.sh` that
creates a `venv` and prepares the development tooling. IMPORTANT: by default
the helper will NOT install distribution artifacts from `dist/`. Its purpose
is to create the virtualenv, restore repo executable bits, enable repo-local
git hooks and optionally install helpful developer utilities.

To prepare the environment (default):

```bash
.development/setup_dev.sh
```

To install the package into the venv in editable mode for active development,
pass `editable` or set the `DEV_EDITABLE=1` environment variable:

```bash
.development/setup_dev.sh editable
DEV_EDITABLE=1 .development/setup_dev.sh
```

Use `-h` or `--help` to see usage:

```bash
.development/setup_dev.sh -h
```

If you use the helper scripts, see `.development/README.md`.

## Windows notes

The repository's helper scripts and git hooks are POSIX shell scripts and are intended to run under Bash. On native Windows systems the repository provides an automatic re-exec wrapper that will attempt to locate Git Bash and run the invoked script under that interpreter. If Git Bash is not available, the setup helper will offer to open the Git for Windows download page. For native PowerShell workflows consider using WSL or Git Bash when running repository helper scripts.

Guidance for Windows users:

- Preferred: use Git Bash (installed via Git for Windows) or WSL to run the repository helper scripts and hooks.
- If `bash` is not available, `.development/setup_dev.sh` will offer to open the Git for Windows download page (interactive). A PowerShell helper exists at `.development/install-git-for-windows.ps1` to assist.
- Hooks and scripts are modified to re-exec under Git Bash when available; if you must run scripts from PowerShell or CMD, explicitly invoke them via `bash .development/setup_dev.sh`.

If you are contributing from Windows and prefer native PowerShell scripts, consider adding Windows-specific `.ps1` helpers rather than editing the POSIX scripts directly; the repository keeps the shell scripts as the canonical implementation.

## Notes

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

### Translations sync check

We added a repository-local pre-commit hook `check-translations` that ensures PO files in `translations/` are kept in sync with `translations/messages.pot`.

If a commit is rejected due to the translations check, do the following:

```bash
# merge POT into PO files
./.development/compile_translations.sh update

# inspect and stage updated PO files
git add translations/*/LC_MESSAGES/*.po

# optionally compile and copy compiled catalogs into the package for runtime testing
./.development/compile_translations.sh compile

# then retry committing
git commit
```

This hook helps prevent missing or stale translations being merged. The helper script uses the project's `venv` `pybabel`, so ensure you ran `.development/setup_dev.sh` to have the necessary tooling available.

### Prettier and formatting

We use a project-local Prettier for JS/HTML/Markdown formatting. The `pre-commit`
hook runs a helper script located at `.development/prettier-hook.sh` which will
prefer the repository `node_modules/.bin/prettier` if present, otherwise it will
fall back to `npx --yes prettier --write`.

Note: the generated API document `docs/api/python.md` is intentionally excluded
from automatic formatting to avoid changes from generated artifacts.

### Post-commit / artifact creation

Artifact builds belong in CI; if you need to create local distributions, run the build helper manually:

```bash
# create sdist and wheel locally
./.development/post_commit_build_dist.sh --sdist --wheel
```

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

### If you add or change strings, update and compile catalogs

We provide a repository helper that wraps `pybabel` and keeps the plugin package catalogs in sync. Use it from the repository root:

```bash
# refresh POT (extract)
./.development/compile_translations.sh extract

# merge POT into existing PO files
./.development/compile_translations.sh update

# compile top-level translations and copy compiled catalogs into the package
./.development/compile_translations.sh compile
```

Note: A `pre-commit` local hook (`check-translations`) will run `./.development/compile_translations.sh update` and block commits if PO files would be modified by the update step. If your commit is rejected with a translations error, run the above `update` command, review and commit the changed PO files (and compiled MO if you keep them in the repo), then retry the commit.

## What not to commit

Do not commit generated or environment-specific files such as:

- `dist/`, `build/`, `*.egg-info/`
- `__pycache__/`, `.pytest_cache/`, `.coverage/`, `htmlcov/`
- local virtual environments (`venv/`)
- IDE/editor configs (`.idea/`, `.vscode/`)
