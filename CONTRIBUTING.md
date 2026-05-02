# Contributing

Thanks for your interest in contributing to the OctoPrint-Uptime plugin!

## Quick Start and Development Setup

**Prerequisites:** Python 3.9+ and `python3-venv` (or equivalent) installed.

### Recommended Setup (Reproducible)

This is the recommended approach for a consistent, reproducible development environment:

1. Fork the repository
2. Clone your fork and create a feature branch: `git checkout -b wip/my-feature`
3. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install development dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements-dev.txt
   ```

5. (Optional) Install the package in editable mode with development extras:

   ```bash
   python -m pip install -e ".[develop]"
   ```

### Alternative Minimal Setup

If you prefer a minimal setup without the full development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[develop]"
```

### Setup Checklist

After setting up your environment, complete these steps:

- [ ] Install pre-commit in your venv (included in `requirements-dev.txt` or via `pip install pre-commit`)
- [ ] Install git hooks: `pre-commit install`
- [ ] Run tests to verify setup: `pytest`
- [ ] Run pre-commit to verify hooks: `pre-commit run --hook-stage manual --all-files`

### Running Tests

```bash
pytest
```

### Running Pre-commit

We use `pre-commit` to enforce consistent formatting and basic quality checks.

To run all checks manually:

```bash
pre-commit run --hook-stage manual --all-files
```

### Installing Pre-commit Hooks

Install hooks once per clone:

```bash
pre-commit install
```

**Do not run `pre-commit install`.** The wrapper at `.githooks/pre-commit` is the entry point Git invokes; it then delegates to `./.venv/bin/pre-commit run`. Running `pre-commit install` will fail with `Cowardly refusing to install hooks with 'core.hooksPath' set` (by design).

**Available hooks:**

- `pre-commit` — wrapper that runs the project's pre-commit suite from `./.venv` (formatting, linting, validation)
- `post-commit` — auxiliary post-commit tasks

After configuring, Git automatically runs these hooks on each commit. If a hook fails, the commit is rejected — fix the issues and re-commit.

To temporarily skip hooks (not recommended):

```bash
git commit --no-verify
```

**Automatic pre-commit autoupdate (optional):**

If you want your local hooks to attempt to keep themselves updated before running, set the environment variable `PRECOMMIT_AUTOUPDATE=1`. The repo-local wrapper will run `pre-commit autoupdate` at most once per 24 hours. This is opt-in. Running autoupdate on every commit by default is not recommended because it may change `.pre-commit-config.yaml` unexpectedly.

To enable:

```bash
export PRECOMMIT_AUTOUPDATE=1
```

Review any changes created by `autoupdate` before committing them.

---

## Before You Start

- Please keep issues and pull requests focused: **one bug/feature per PR**.
- If your change affects user-facing behavior, please describe how you tested it.
- Write tests for new features.
- Please follow our [Code of Conduct](CODE_OF_CONDUCT.md).
- Note: `main` is protected on GitHub, so changes go through PRs.

## Bug Reports

When reporting a bug, please include:

- OctoPrint version
- Plugin version
- Steps to reproduce (as minimal as possible)
- Relevant log excerpts
- Screenshots if applicable

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
- local virtual environments (`.venv/`)
- IDE/editor configs (`.idea/`, `.vscode/`)
