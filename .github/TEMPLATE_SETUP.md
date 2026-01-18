# GitHub Copilot Instructions - Placeholder Replacement Guide

**Purpose**: Guide for quickly personalizing the template for your plugin using GitHub Copilot.

When cloning or using this template to create a new OctoPrint plugin, follow this guide to replace all placeholders with your actual values.

## Placeholder Values to Replace

| Placeholder | Description | Example |
| --- | --- | --- |
| `your-handle` | Your GitHub username | `octoprint-org` |
| `your-repo` | Your repository name | `octoprint-my-feature` |
| `octoprint_plugin_template` | Python package name | `octoprint_my_feature` |
| `OctoPrint-PluginTemplate` | Project name in pyproject.toml | `OctoPrint-MyFeature` |
| `plugin_template` | Plugin entry point ID | `my_feature` |
| `Your Name` | Author name | `Ajimaru` |
| `you@example.com` | Author email | `ajimaru_gdr@pm.me` |

## Files Requiring Replacement

### Core Configuration

- **[pyproject.toml](pyproject.toml)**
  - `name = "OctoPrint-PluginTemplate"` → Your project name
  - `authors` → Your name and email
  - `Homepage`, `Repository`, `Issues` URLs

### Documentation- **[README.md](README.md)**

  - Badges URLs (v/release, downloads, issues) → Replace `Ajimaru/octoprint_plugin_template` with `Ajimaru/your-repo`
  - Installation URLs → Same replacement
  - Add brief description of your plugin
  - Remove/update example sections

- **[CHANGELOG.md](CHANGELOG.md)**
  - URL to releases page → Update with your repo

- **[SECURITY.md](SECURITY.md)**
  - Email address for security reports

### Code & Build

- **[MANIFEST.in](MANIFEST.in)** → If renaming package
- **[babel.cfg](babel.cfg)** → If renaming package
- **[.github/CODEOWNERS](.github/CODEOWNERS)**
  - `@Ajimaru` → Your GitHub handle
- **[.github/workflows/ci.yml](.github/workflows/ci.yml)**
  - Line with `github.repository == 'Ajimaru/your-repo'` for Codecov condition

### Directory Rename (Optional)

If renaming `octoprint_plugin_template` to `octoprint_my_plugin`:
1. Rename folder: `mv octoprint_plugin_template octoprint_my_plugin`
2. Update above config files
3. Regenerate translations: `pybabel extract -F babel.cfg -o translations/messages.pot . && pybabel update -i translations/messages.pot -d octoprint_my_plugin/translations -l en -l de && pybabel compile -d octoprint_my_plugin/translations`

## Quick Search & Replace

Using your editor's find/replace (Ctrl+Shift+H / Cmd+Shift+H):

```
octoprint_plugin_template  →  octoprint_my_plugin
plugin_template            →  my_plugin
OctoPrint-PluginTemplate   →  OctoPrint-MyFeature
your-handle/your-repo      →  Ajimaru/your-repo
Ajimaru/octoprint_plugin_template  →  Ajimaru/octoprint_my_plugin
Your Name                  →  Ajimaru
you@example.com            →  ajimaru_gdr@pm.me
```

## Verification Checklist

After replacement:

- [ ] All README badges and URLs point to your repo
- [ ] pyproject.toml has correct package name, author, URLs
- [ ] Plugin loads without errors: `python -m pip install -e ".[develop]"`
- [ ] Tests pass: `pytest`
- [ ] Translations compile: `pybabel compile -d octoprint_plugin_template/translations` (or your renamed path)
- [ ] Pre-commit checks pass: `pre-commit run --all-files`

## When to Update Later

- **CHANGELOG.md** → Before each release (add entry with date, version, changes)
- **Translations** → After adding/changing user-facing strings
- **CI badge URLs** → After first commit to match repo structure

---

For full plugin development guidance, see [.github/copilot-instructions.md](.github/copilot-instructions.md).
