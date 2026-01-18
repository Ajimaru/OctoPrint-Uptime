# GitHub Repository Settings Checklist

Based on [OctoPrint-TempETA repository structure](https://github.com/Ajimaru/OctoPrint-TempETA), configure your plugin repository with these settings.

## Repository Settings

### General

- **Repository name**: `octoprint_my_plugin` (lowercase, with underscore)
- **Description**: "OctoPrint plugin for [feature description]"
- **Visibility**: Public
- **Template repository**: ✓ Check this box (optional, but recommended for future plugins)

### Branch Protection Rules

**Branch**: `main`

- ✓ Require a pull request before merging
  - ✓ Require approvals: **1**
  - ✓ Dismiss stale pull request approvals when new commits are pushed
- ✓ Require status checks to pass before merging
  - Status checks required:
    - `CI / Test (Python 3.11)`
    - `CI / Test (Python 3.12)` (or your chosen version for coverage)
    - `CI / Test (Python 3.13)` (if applicable)
    - `i18n / i18n catalog check`
    - Other checks: pre-commit, build, etc.
  - ✓ Require branches to be up to date before merging
- ✓ Require code reviews before merging
- ✓ Include administrators
- ✓ Restrict who can push to matching branches

### Access

#### Collaborators & Teams

- Add maintainers with **Maintain** or **Admin** role
- Add contributors with **Push** or **Triage** role

#### Code Owners

File: [.github/CODEOWNERS](.github/CODEOWNERS)
- Define owners for critical paths (core code, workflows, translations)
- Example: `@your-handle` for key areas

### Actions

#### Runner Settings
- Use **GitHub-hosted runners** (Ubuntu latest, Python 3.11+)
- No custom runners needed for standard CI

#### Permissions

Set workflow permissions to **Minimal**:
- ✓ Read repository contents and deployments

### Pages (Optional)

If you plan to host plugin documentation:
- Source: Deploy from branch → `main` + `/docs` folder
- Or: Use GitHub Pages + separate docs site

### Secrets & Variables (for Codecov/PyPI)

**If publishing to PyPI:**
- Add secret: `PYPI_API_TOKEN` (from PyPI account settings)
- Uncomment `Publish to PyPI` step in [.github/workflows/release.yml](.github/workflows/release.yml)

**If using Codecov:**
- Repository setting: Codecov access in CI config
- Adjust [.github/workflows/ci.yml](.github/workflows/ci.yml) line: `github.repository == 'your-handle/your-repo'`

### Labels

Recommended labels for issues:
- `bug` (red) - Something isn't working
- `enhancement` (blue) - New feature or request
- `documentation` (green) - Improvements or additions to documentation
- `help wanted` (purple) - Extra attention is needed
- `needs-triage` (gray) - Needs review and categorization
- `good first issue` (yellow) - Good for newcomers

### Webhooks & Integrations

- **Dependabot** (optional): Enable for dependency updates
  - Configure: `.github/dependabot.yml` (example provided in template)

### Templates

- Use provided issue templates:
  - [.github/ISSUE_TEMPLATE/bug_report.yml](.github/ISSUE_TEMPLATE/bug_report.yml)
  - [.github/ISSUE_TEMPLATE/feature_request.yml](.github/ISSUE_TEMPLATE/feature_request.yml)
- Use provided PR template: [.github/pull_request_template.md](.github/pull_request_template.md)

### Description & Links

- **Description**: "OctoPrint plugin for [your feature]"
- **Website**: Link to documentation (optional)
- **Topics**: `octoprint`, `octoprint-plugin`, `python`
- **Include in organization**: If applicable

---

## Workflows & Automation

### CI/CD Workflows

Workflows are pre-configured in [.github/workflows/](.github/workflows/):

1. **ci.yml** (on push to main, pull requests, tags)
   - Tests: Python 3.11, 3.12, 3.13
   - Pre-commit checks
   - Coverage upload to Codecov
   - Build package (wheel + sdist)

2. **i18n.yml** (before merge, on tags)
   - Verify translation catalogs are up-to-date
   - Compile translations

3. **release.yml** (on version tags: `v*`)
   - Build distribution artifacts
   - Create GitHub releases
   - Attach `.whl`, `.tar.gz`, `.zip` files
   - Optional: Publish to PyPI (uncomment step)

### First-Time Setup

1. **Create repository** on GitHub
2. **Clone and push** this template
3. **Configure branch protection** for `main` (as above)
4. **Verify workflows run** on first push
5. **Test locally**: `pytest && pre-commit run --all-files`

---

## Community & Contribution

- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **License**: AGPL-3.0 ([LICENSE](LICENSE))

### Communication

- **Issues**: For bug reports and feature requests
- **Discussions** (optional): Enable for Q&A and announcements
- **OctoPrint Community Forum**: For plugin support discussions

---

## Release Process

1. Bump version in [pyproject.toml](pyproject.toml)
2. Create release branch: `git switch -c release/vX.Y.Z`
3. Update [CHANGELOG.md](CHANGELOG.md)
4. Submit PR → Get approval → Merge to `main`
5. Tag release: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push origin vX.Y.Z`
6. Workflow builds artifacts automatically
7. Add release notes on GitHub

See [RELEASING.md](RELEASING.md) for detailed instructions.

---

## Security

- Enable **Dependabot** for dependency updates (`.github/dependabot.yml`)
- Configure **Security Advisories** for private vulnerability reports
- Keep OctoPrint dependency up-to-date
- Run local checks before pushing: `pytest && pre-commit run --all-files`

---

## Optional Enhancements

- **Documentation site**: GitHub Pages or ReadTheDocs
- **Discord/Slack**: Community chat for users
- **Package registry**: Publish to PyPI for `pip install` support
- **Auto-formatting**: Pre-commit hooks (already configured)
- **Code coverage reporting**: Codecov badge (configure in CI)
