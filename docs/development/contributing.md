# Contributing

This page summarizes the contributor workflow for developers. The authoritative, repository-wide contributor guidance is in the top-level `CONTRIBUTING.md` — keep both in sync.

## Quickstart

- Create and activate a virtual environment (venv) and install development deps:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[develop]"
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

**TODO** Describe how to populate `node_modules` by running `npm install` when `npm` is available, installing `jsdoc-to-markdown` so the generator can run without a separate `npm install` step.

## Internationalization

- After compiling, restart OctoPrint or reload the plugin so the runtime picks up the new `.mo` files (they are copied into `octoprint_uptime/translations/`).

Notes

- Keep changes small and focused. Follow the coding style in `CONTRIBUTING.md` (4-space indentation, English text, use `self._logger` for logging). Use the 'venv' directory for the virtual environment.
