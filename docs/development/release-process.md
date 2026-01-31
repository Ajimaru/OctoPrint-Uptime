# Release process

This document summarizes the release workflow and the helper scripts used by maintainers.

## Build artifacts

Create source and wheel distributions locally:

```bash
python -m build
```

## Tagging and publishing

- Create a git tag for the release (e.g. `v1.2.3`) and push the tag to GitHub.
- Releases may be published from GitHub releases or via CI workflows that build and upload artifacts.

## Security & checks

- After adding or updating dependencies, run the repository security checks and the packaging validation in CI. The bump scripts try to be conservative but you should run tests and `pre-commit` locally before tagging.

Notes

- The `docs` CI workflow runs `./scripts/generate-jsdocs.sh` before `mkdocs build` to regenerate JavaScript API docs (see `.github/workflows/docs.yml`).
- If you use the bump helpers, verify the final `pyproject.toml` version string follows PEP 440 (the bump helper normalizes `-devN` into `.devN`).
