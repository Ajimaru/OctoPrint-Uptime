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

- The repository includes a `jsdoc-gen` pre-commit hook that runs `./scripts/generate-jsdocs.sh` when JS files under `octoprint_uptime/static/js` are modified. The hook uses `pass_filenames: true` so it only passes changed files to the script (faster local commits).

- Populate `node_modules` and install the doc generator:

```bash
# From the repository root, install JS deps (use `npm ci` if you have a lockfile):
npm install
# Install the generator so the script can run without an extra install step
# as a devDependency (preferred):
npm install --save-dev jsdoc-to-markdown
# or install it globally if you prefer:
npm install -g jsdoc-to-markdown
```

- Regenerate the JS docs (the pre-commit hook runs this automatically for changed files):

```bash
./scripts/generate-jsdocs.sh <changed-file.js>
```

Note: The generated `docs/api/javascript.md` file is not committed (see `.gitignore`).

## Internationalization

- After compiling, restart OctoPrint or reload the plugin so the runtime picks up the new `.mo` files (they are copied into `octoprint_uptime/translations/`).

To compile translation messages use Babel's `pybabel` tool. From the repository root run:

```bash
# compile all available translations from PO -> MO
pybabel compile -d octoprint_uptime/translations -D messages
```

This will write the compiled `.mo` files into `octoprint_uptime/translations/<lang>/LC_MESSAGES/messages.mo` (the plugin runtime loads `.mo` files from `octoprint_uptime/translations/`). See the Babel docs for more details: [Babel docs](https://python-babel.github.io/).

Notes:

- Keep changes small and focused. Follow the coding style in `CONTRIBUTING.md` (4-space indentation, English text, use `self._logger` for logging). Use the 'venv' directory for the virtual environment.
