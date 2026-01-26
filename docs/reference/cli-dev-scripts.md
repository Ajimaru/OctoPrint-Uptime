# CLI / Dev helper scripts

This page documents the helper scripts in the repository `.development/` that are useful when developing, testing, bumping versions and preparing release artifacts.

## Location

All helper scripts live under the `.development/` directory at the project root. They are intended for maintainers and contributors and may rely on a local Python virtual environment.

## Important scripts

- `.development/setup_dev.sh`
  - Prepares a local development environment (creates `venv/`, restores executable bits, configures local git hooks and installs common developer tooling).
  - IMPORTANT: by default it does NOT install distribution artifacts from `dist/`. To install the package into the venv for live-editing, run with `editable` or set `DEV_EDITABLE=1`.
  - Usage: `bash .development/setup_dev.sh` (may require executable permission).
  - Note: the setup helper now also installs the full development requirements from `requirements-dev.txt` into the created `venv` to ensure tooling such as `pre-commit`, `build` and `tomli` are available automatically.
  - Additionally, when `npm` is available the helper will populate `node_modules` (run `npm install`) so Node-based dev tools listed in `package.json` (for example `jsdoc-to-markdown`) are available for documentation generation. This makes `./scripts/generate-jsdocs.sh` usable without a separate `npm install` step.

- `.development/restart_octoprint_dev.sh`
  - This will not install `dist/` artifacts by default.
  - Convenience script to stop/start or restart a local OctoPrint instance used for manual testing of the plugin.
  - It forwards `OCTOPRINT_ARGS` as separate argv tokens so commands like `serve --debug` are passed correctly.
  - Usage example:

```bash
# restart OctoPrint in dev mode (default behavior)
.development/restart_octoprint_dev.sh

# restart and clear generated webassets cache
.development/restart_octoprint_dev.sh --clear-cache --restart-all
```

Setting `OCTOPRINT_ARGS`

You can pass additional CLI arguments to the OctoPrint executable by exporting the `OCTOPRINT_ARGS` environment variable before running the restart helper. The script splits the value into argv tokens and forwards them to the resolved `octoprint` binary.

Example:

```bash
# run OctoPrint with the built-in server in debug mode
export OCTOPRINT_ARGS="serve --debug"
.development/restart_octoprint_dev.sh

# or specify a virtualenv and pass extra args
export OCTOPRINT_VENV="$PWD/venv"
export OCTOPRINT_ARGS="serve --debug --ip=0.0.0.0"
.development/restart_octoprint_dev.sh --clear-cache
```

Tip: instead of `OCTOPRINT_ARGS` you can set `OCTOPRINT_CMD` to an absolute octoprint binary (or `OCTOPRINT_VENV` to point at a venv) if you need full control over the executable used.

- `.development/bump_control.sh`
  - Helper to bump project version numbers consistently across `pyproject.toml` and other metadata.
  - Ensures dev versions use a PEP 440 compatible `.devN` suffix (converts `-devN` to `.devN` when writing files).
  - It also offers to trigger the post-commit build flow (see `post_commit_build_dist.sh`) and contains logic to run the correct packaging command depending on environment.
  - Use with caution: double-check the new version string before pushing tags.

- `.development/post_commit_build_dist.sh`
  - Creates source and binary distributions, and supports packaging steps used for release candidates.
    It will error on unknown CLI flags and tries to resolve the correct Python executable from common venv locations.
  - Typical usage (from repo root):

```bash
.development/post_commit_build_dist.sh --sdist --wheel
```

## Other helpers

- `.development/monitor_octoprint_performance.sh` — lightweight monitor for file descriptor and process checks (useful during long-running tests).
- `.development/test_checklist.sh` — interactive checklist script for manual release verification.

## Best practices

- Run `bash .development/setup_dev.sh` once to prepare your development environment and enable recommended pre-commit hooks.
- When bumping versions, review the changes produced by `.development/bump_control.sh` before committing or tagging.
- After adding dependencies, run the repository's security checks as documented (see `codacy` rules in the top-level `.github/instructions` if applicable) and compile translation catalogs if strings changed.

- The repository includes a `pre-commit` hook `check-translations` which will run during commits to ensure PO files are up-to-date with the POT. If a commit fails with a translations check, run:

```bash
./.development/compile_translations.sh update
git add translations/*/LC_MESSAGES/*.po
```

Then re-run the commit. To compile and copy compiled catalogs into the package for runtime testing, run:

```bash
./.development/compile_translations.sh compile
```

## JS documentation generation

The repository provides an automated JSDoc → Markdown step integrated into pre-commit. The `jsdoc-gen` hook runs `./scripts/generate-jsdocs.sh`. To make local commits faster the hook passes only changed filenames to the script (`pass_filenames: true`) and the script documents only the files it receives. When running the script manually it still documents the whole package if no filenames are given.

If you rely on the JS docs generator, ensure you've run `.development/setup_dev.sh` (it will install `jsdoc-to-markdown` into `node_modules` when `npm` is present).

## Notes

- These scripts are convenience helpers and are not a shield against manual verification. Always run tests (`pytest`) and check the generated artifacts before publishing.
