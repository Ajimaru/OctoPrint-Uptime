# Development scripts

This folder contains helper scripts for local development.

None of these scripts contain hardcoded, machine-specific absolute paths. Wherever a path is needed, it is either auto-discovered (repo-relative) or configurable via environment variables.

## Quick start

```bash
# from repo root
.development/setup_dev.sh
```

If you downloaded the repository as a ZIP from GitHub, your unzip tool may have dropped executable bits.
In that case, run the script explicitly via bash:

```bash
bash .development/setup_dev.sh
```

Alternatively, you can restore the executable bit and run it directly:

```bash
chmod +x .development/setup_dev.sh
.development/setup_dev.sh
```

`setup_dev.sh` will also try to restore executable permissions for repo scripts and hooks (best-effort).

## Scripts

### setup_dev.sh

Creates/uses a local Python virtual environment in `./venv`, and prepares the
development tooling. IMPORTANT: by default this helper does NOT install any
distribution artifacts from the `dist/` folder. Its purpose is to create the
venv, restore executable bits, enable repo-local git hooks and install common
developer tooling (e.g. `bump-my-version`) when requested.

If you want the package available inside the venv for live-edit development,
run the helper with the single argument `editable` or set `DEV_EDITABLE=1` in
the environment; this performs an editable install (`pip install -e "[develop]"`).
Use `-h` or `--help` to show usage.

#### Examples

```bash
# prepare venv and dev tooling (does not install dist artifacts)
.development/setup_dev.sh

# install in editable mode (development workflow)
.development/setup_dev.sh editable

# equivalent via env
DEV_EDITABLE=1 .development/setup_dev.sh

# show help
.development/setup_dev.sh -h
```

Notes

- The helper scripts target a Python 3.10+ development environment. The plugin itself supports Python 3.10+ as declared in `pyproject.toml`.
- It automatically sets `git config core.hooksPath .githooks` (if the repo is a git checkout).
- `pre-commit` will be installed into the project's `./venv` automatically when missing. The setup helper prefers the venv-installed `pre-commit` and will attempt to install and activate the hook environments from `./venv/bin/pre-commit`.
- To use a specific Python interpreter for the venv (e.g. Python 3.12), set `PYTHON_BIN`: `PYTHON_BIN=python3.12 .development/setup_dev.sh`.
- To run an initial `pre-commit run --all-files` during setup, set `RUN_PRE_COMMIT_ALL_FILES=1`.

### Notes about bump configuration

- During setup the script will also ensure a default bump configuration exists at `.development/bumpversion.toml` (created if missing). This file is used by the helper `bump_control.sh` and is bump-my-version / bump2version-compatible. You can edit it to adjust which files are updated by version bumps.

### bump_control.sh

Interactive helper script to prepare and run version bumps using `bump-my-version`. Key points:

- Location: `.development/bump_control.sh`
- Default config: uses `.development/bumpversion.toml` when `--config` is not provided.
- Verbosity: the script passes `-vv` to `bump-my-version` by default for detailed output; set `--silent` to disable verbose output.
- RC mode: when bumping `rc`, the script can auto-increment RC numbers, update `octoprint_uptime/_version.py` and `pyproject.toml`, and optionally commit/tag (interactive prompts default to No).

Quick examples:

```bash
# Interactive RC dry-run (default verbose)
.development/bump_control.sh rc

# Silent real bump (execute)
.development/bump_control.sh --silent rc --execute

# Use a custom config
.development/bump_control.sh --config .development/bumpversion.toml minor --execute
```

Single-step example (silent, real bump to minor):

```bash
.development/bump_control.sh --silent minor --execute
```

Git hooks behavior:

- `pre-commit` hook: runs from `./venv/bin/pre-commit` and requires the venv Python to be 3.10+. The `setup_dev.sh` helper will install `pre-commit` into the venv and install hook environments when necessary; if you opt out of setup or the install fails, the hook will still fail and instruct you to run `.development/setup_dev.sh`.
- `post-commit` hook: builds dist artifacts on version bumps using Python 3.10+ (prefers `./venv/bin/python`, otherwise `python3`). If Python/build tooling is unavailable, it fails with an error.

### restart_octoprint_dev.sh

Stops OctoPrint (by default: the instance listening on `OCTOPRINT_PORT`), optionally clears webassets cache, and starts OctoPrint again.

```bash
# basic restart
.development/restart_octoprint_dev.sh

# restart and clear OctoPrint webassets cache (useful after frontend changes)
.development/restart_octoprint_dev.sh --clear-cache

# stop all detected OctoPrint instances for the current user and exit
.development/restart_octoprint_dev.sh --stop-all

# stop all detected OctoPrint instances for the current user, then restart
.development/restart_octoprint_dev.sh --restart-all

# alias for --stop-all
.development/restart_octoprint_dev.sh --stop-only

# show help
.development/restart_octoprint_dev.sh --help
```

Configuration (environment variables):

- `OCTOPRINT_CMD=/path/to/octoprint` (preferred)
- `OCTOPRINT_VENV=/path/to/venv` (uses `$OCTOPRINT_VENV/bin/octoprint`)
- `OCTOPRINT_PORT=5000`
- `OCTOPRINT_ARGS="serve --debug"`
- `OCTOPRINT_BASEDIR=$HOME/.octoprint`
- `OCTOPRINT_LOG=$OCTOPRINT_BASEDIR/logs/octoprint.log`
- `NOHUP_OUT=/tmp/octoprint.nohup`

How `octoprint` is resolved (in order):

1. `OCTOPRINT_CMD`
2. `OCTOPRINT_VENV/bin/octoprint`
3. repo-relative fallbacks (e.g. `./venv/bin/octoprint`)
4. `octoprint` on `PATH`

### post_commit_build_dist.sh

Builds fresh distribution artifacts into `dist/` after a commit **only when the project version changed** in `pyproject.toml` compared to the previous commit.

- Creates wheel + sdist via `python3 -m build`
- Creates an additional `.zip` (derived from the sdist `.tar.gz`) for convenience

You usually don't run this manually. It is called by the git `post-commit` hook.

Options:

- `--force`, `-f` — bypass the `pyproject.toml` unchanged check and force creation of dist artifacts.
- `-h`, `--help` — show a short usage message and exit.

Note: `.development/bump_control.sh` will offer to run this helper automatically after a real (executed) bump; you can also run it manually when needed.

### test_checklist.sh

Prints a human-readable quick checklist (versions, file presence, rough counts). It does **not** run automated tests.

```bash
.development/test_checklist.sh
```

### run_ci_locally.sh

Runs a fast, CI-like verification locally (pytest, pre-commit, i18n check, build).

By default it will **not** keep auto-fixes made by pre-commit (it reverts them and fails). Use `--apply-fixes` if you want it to apply changes.

If your working tree is not clean, the script will refuse to run unless you pass `--allow-dirty`.

```bash
.development/run_ci_locally.sh
```

### monitor_octoprint_performance.sh

Lightweight performance monitoring for long-running OctoPrint/plugin tests.

It samples OctoPrint process metrics (CPU, RSS, threads, open FDs), watches the plugin data directory
(`~/.octoprint/data/octoprint_uptime/` by default), and records basic log growth stats.

Logs are written to the repo-local `.logs/` folder (gitignored).

Examples:

```bash
# run until Ctrl+C (sample every 10s)
.development/monitor_octoprint_performance.sh

# sample every 5s for 10 hours
.development/monitor_octoprint_performance.sh --interval 5 --duration 36000

# take a single snapshot
.development/monitor_octoprint_performance.sh --once
```

If PID auto-detection fails (e.g. non-default port), pass `--pid` or `--port`.

## Git hooks

The repo uses a versioned hooks directory:

- Hook path: `.githooks/`
- Enabled via: `git config core.hooksPath .githooks`

The `post-commit` hook triggers `post_commit_build_dist.sh` after version bumps.

## Prettier helper

The repository uses a project-local Prettier installation for frontend/JS
formatting. A small helper script lives at `.development/prettier-hook.sh` and
is invoked by the `pre-commit` hook to run the project `node_modules/.bin/prettier`
when available, or fall back to `npx --yes prettier`.

If you run `npm install` in the repository root the hook will prefer the
locally-installed binary which avoids `npx` network calls during commits.

### Automatic autoupdate option

If you prefer `pre-commit` hook definitions to be kept up-to-date automatically
before hooks run locally, you can enable an opt-in behavior by setting the
environment variable `PRECOMMIT_AUTOUPDATE=1`. When enabled the repo-local
`pre-commit` wrapper will invoke `pre-commit autoupdate` at most once every 24
hours (a timestamp marker is written into the repo git dir). This is
intentionally opt-in to avoid unexpected network calls on every commit.

To enable for your shell session:

```bash
export PRECOMMIT_AUTOUPDATE=1
```

Notes

- `pre-commit autoupdate` may modify `.pre-commit-config.yaml`; review changesbefore committing them.
- For automated, repository-level updates prefer `pre-commit.ci` or ascheduled GitHub Action that runs `pre-commit autoupdate` and opens a PR.
