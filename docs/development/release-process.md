# Release process

This document summarizes the release workflow and the helper scripts in `.development` used by maintainers.

Build artifacts

Create source and wheel distributions locally:

```bash
python -m build
```

Tagging and publishing

- Create a git tag for the release (e.g. `v1.2.3`) and push the tag to GitHub.
- Releases may be published from GitHub releases or via CI workflows that build and upload artifacts.

Helper scripts

The repository provides a set of helper scripts under `.development/` used during the release and development lifecycle:

- `.development/bump_control.sh` — bump the project version, update `pyproject.toml` (ensures PEP 440 `.devN` format for dev versions), and optionally trigger the post-commit build flow.
- `.development/post_commit_build_dist.sh` — helper to create source and binary distributions and (optionally) upload or package them for release candidates.
- `.development/setup_dev.sh` — prepare local developer environment (venv, permissions, hooks).
- `.development/restart_octoprint_dev.sh` — convenience helper to restart a local OctoPrint instance for manual testing while developing the plugin.

Security & checks

- After adding or updating dependencies, run the repository security checks and the packaging validation in CI. The bump scripts try to be conservative but you should run tests and `pre-commit` locally before tagging.

Notes

- The `docs` CI workflow runs `./scripts/generate-jsdocs.sh` before `mkdocs build` to regenerate JavaScript API docs (see `.github/workflows/docs.yml`).
- If you use the bump helpers, verify the final `pyproject.toml` version string follows PEP 440 (the bump helper normalizes `-devN` into `.devN`).
