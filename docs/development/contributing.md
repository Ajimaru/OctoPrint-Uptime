# Contributing

This page summarizes the contributor workflow for developers. The authoritative, repository-wide contributor guidance is in the top-level `CONTRIBUTING.md` — keep both in sync.

## Quickstart

- Create and activate a virtual environment and install development deps:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[develop]"
```

If you prefer helper scripts, run the repository helper to set up a dev environment:

```bash
bash .development/setup_dev.sh
```

### Note: The helper prepares the venv and common developer tooling but does **not**

install distribution artifacts from `dist/` by default. To install in editable
mode (for live editable development), pass the argument `editable` or set
`DEV_EDITABLE=1`:

```bash
.development/setup_dev.sh editable
DEV_EDITABLE=1 .development/setup_dev.sh
```

### Note: The setup helper now installs the full development requirements from

`requirements-dev.txt` into the created `venv` to ensure common tooling (for
example `pre-commit`, `build`, `tomli`) is present automatically.

Use `-h` for help:

```bash
.development/setup_dev.sh -h
```

## Branches & PRs

- Create a feature branch and open a PR into `main` (direct pushes to `main` are blocked).
- One logical change per PR; include testing notes and screenshots for UI changes.

## Pre-commit

- We use `pre-commit` hooks. To run all hooks locally:

```bash
pre-commit run --hook-stage manual --all-files
```

### Notes on JS docs & pre-commit

- The repository includes a `jsdoc-gen` pre-commit hook that runs `./scripts/generate-jsdocs.sh` when JS files under `octoprint_uptime/static/js` are modified. The hook now uses `pass_filenames: true` so it only passes changed files to the script (faster local commits).
- `./.development/setup_dev.sh` will populate `node_modules` by running `npm install` when `npm` is available, installing `jsdoc-to-markdown` so the generator can run without a separate `npm install` step.

### Post-commit artifact policy

Artifact creation is handled in CI; to build locally use the packaging helper manually:

```bash
./.development/post_commit_build_dist.sh --sdist --wheel
```

This avoids unexpected local builds during routine commits.

## Internationalization

- Use the repository helper `./.development/compile_translations.sh` when extracting, updating or compiling translations. It uses the project's `venv` `pybabel` and treats the top-level `translations/` directory as the single source of truth. Common commands:

```bash
# extract updated msgids to translations/messages.pot
./.development/compile_translations.sh extract

# update existing PO files from the POT
./.development/compile_translations.sh update

# initialize a new language
./.development/compile_translations.sh init de

# compile top-level translations and copy compiled catalogs into the package
./.development/compile_translations.sh compile

# compile only package translations
./.development/compile_translations.sh compile --plugin-only

# compile both top-level and package translations
./.development/compile_translations.sh compile --all
```

- After compiling, restart OctoPrint or reload the plugin so the runtime picks up the new `.mo` files (they are copied into `octoprint_uptime/translations/`).

## Notes

- Keep changes small and focused. Follow the coding style in `CONTRIBUTING.md` (4-space indentation, English text, use `self._logger` for logging).
