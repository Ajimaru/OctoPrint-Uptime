# Releasing

This repository uses a protected default branch (`main`). Releases are created via tags and GitHub Actions.

## Release flow (protected `main`)

1. Create a release branch

   ```bash
   git switch -c release/vX.Y.Z
   ```

2. Make the release changes
   - Bump the version in `pyproject.toml`.
   - Run local checks:

     ```bash
     pre-commit run --all-files
     pytest
     ```

3. Open a Pull Request into `main`
   - Wait for required CI checks to pass.
   - Merge the PR.

4. Create an annotated tag on the merge commit

   Make sure your local `main` is up to date:

   ```bash
   git switch main
   git pull --ff-only
   ```

   Then create and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. Publish the GitHub Release

   Pushing the tag triggers the `Release` workflow, which builds and attaches:
   - `octoprint_plugin_template-X.Y.Z.zip` (user installable)
   - `octoprint_plugin_template-latest.zip` (stable URL for docs)
   - sdist + wheel

   After the workflow completes, add release notes on GitHub.

## Notes

- Do not push directly to `main` (branch protection blocks it).
- Keep public-facing communication in English (issues/PRs/discussions/wiki/security).
