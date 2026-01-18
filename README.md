<!-- markdownlint-disable MD041 MD033-->
<h1 align="center">OctoPrint Plugin Template</h1>
<!-- markdownlint-enable MD041 MD033-->

[![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![OctoPrint](https://img.shields.io/badge/OctoPrint-1.12.0%2B-blue.svg)](https://octoprint.org)
[![Latest Release](https://img.shields.io/github/v/release/Ajimaru/octoprint_plugin_template?sort=semver)](https://github.com/Ajimaru/octoprint_plugin_template/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Ajimaru/octoprint_plugin_template/latest/total)](https://github.com/Ajimaru/octoprint_plugin_template/releases/latest)
[![Issues](https://img.shields.io/github/issues/Ajimaru/octoprint_plugin_template)](https://github.com/Ajimaru/octoprint_plugin_template/issues)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A minimal, opinionated starting point for building OctoPrint plugins. It follows the [OctoPrint plugin guidelines](https://docs.octoprint.org/en/main/plugins/index.html) and ships with i18n scaffolding, CI workflows, and a stub plugin implementation.

## How to use this template

1. **Create your repo from this template** (GitHub → Use this template).
2. **Configure GitHub settings**: See [.github/GITHUB_REPO_SETTINGS.md](.github/GITHUB_REPO_SETTINGS.md).
3. **Replace all placeholders** with your actual values: See [.github/TEMPLATE_SETUP.md](.github/TEMPLATE_SETUP.md) for detailed instructions on all files requiring changes.
4. **Test locally**: `pytest && pre-commit run --all-files`
5. **Push and verify** CI workflows run successfully on first commit.

## Development quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[develop]"
pre-commit install
pytest
```

The stub plugin exposes a simple settings pane and is safe to load in OctoPrint for local testing.

## Translations

Update and compile catalogs whenever user-facing strings change:

```bash
pip install https://github.com/Ajimaru/octoprint_plugin_template/releases/latest/download/octoprint_plugin_template-latest.zip
```

The `releases/latest` URL always points to the newest stable release.

## Configuration

### Settings Defaults

## How It Works

## FAQ

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b wip/my-feature`
3. Write tests for new features
4. Submit a pull request
5. For local development scripts (setup, restart helper, post-commit build hook, performance monitor), see [.development/README.md](.development/README.md).
6. See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
7. Please follow our [Code of Conduct](CODE_OF_CONDUCT.md).

Note: `main` is protected on GitHub, so changes go through PRs.

## License

AGPLv3 - See [LICENSE](LICENSE) for details.

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Ajimaru/octoprint_plugin_template/issues)
- 💬 **Discussion**: [OctoPrint Community Forum](https://community.octoprint.org/)

Note: For logs and troubleshooting, enable "debug logging" in the plugin settings.

## Credits

- **Original Request**: [Issue ](https://github.com/OctoPrint/OctoPrint/issues/xxx) by [@](https://github.com/) (20xx)
- **Development**: Built following [OctoPrint Plugin Guidelines](https://docs.octoprint.org/en/latest/plugins/index.html)
- **Contributors**: See [AUTHORS.md](AUTHORS.md)

---

**Like this plugin?** ⭐ Star the repo and share it with the OctoPrint community!
