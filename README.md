<!-- markdownlint-disable MD041 MD033-->
<h1 align="center">OctoPrint-Uptime</h1>
<!-- markdownlint-enable MD041 MD033-->

[![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![OctoPrint](https://img.shields.io/badge/OctoPrint-1.12.0%2B-blue.svg)](https://octoprint.org)
[![Latest Release](https://img.shields.io/github/v/release/Ajimaru/OctoPrint-Uptime?sort=semver)](https://github.com/Ajimaru/OctoPrint-Uptime/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Ajimaru/OctoPrint-Uptime/latest/total)](https://github.com/Ajimaru/OctoPrint-Uptime/releases/latest)
[![Issues](https://img.shields.io/github/issues/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/issues)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

OctoPrint-Uptime shows the system uptime and provides a small API.

## Features

- Shows the host system uptime in the navbar.
- Small, read-only API endpoint that returns formatted uptime.
- Frontend widget refreshes the display periodically (short polling).
- Provides a small API endpoint at `/api/plugin/octoprint_uptime` (protected, requires OctoPrint permissions).

## Development quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip build
python3 -m pip install -e ".[develop]"
pre-commit install
pytest
```

For local testing: the `.development/restart_octoprint_dev.sh` helper in this repo uses a local OctoPrint dev setup. After changing templates or assets run `./.development/restart_octoprint_dev.sh --clear-cache`.

## Translations

Translation files live under `octoprint_uptime/translations`. Rebuild/compile catalogs with Babel/pybabel after changes to user-facing strings.

Binary releases are available from the project's GitHub Releases page.

## Configuration

### Settings Defaults

The following default values are used by the plugin (see `get_settings_defaults()`):

- `debug`: `false`
- `navbar_enabled`: `true`
- `display_format`: `"full"` (days + hours + minutes + seconds)
- `debug_throttle_seconds`: `60`

## How It Works

The plugin exposes a small JSON endpoint at `/api/plugin/octoprint_uptime`. A small Knockout-based navbar widget polls that endpoint and displays the formatted uptime.

## FAQ

- How do I enable debug logs? → Toggle the "Debug" option in the plugin settings.
- Why is the API protected? → For security; sensitive or system information is only exposed to authorized OctoPrint users.

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

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Ajimaru/OctoPrint-Uptime/issues)
- 💬 **Discussion**: [OctoPrint Community Forum](https://community.octoprint.org/)

Note: For logs and troubleshooting, enable "debug logging" in the plugin settings.

## Credits

- **Original Request**: [Issue 4355](https://github.com/OctoPrint/OctoPrint/issues/4355) by [@Oxize](https://github.com/Oxize) (2021)
- **Development**: Built following [OctoPrint Plugin Guidelines](https://docs.octoprint.org/en/latest/plugins/index.html)
- **Contributors**: See [AUTHORS.md](AUTHORS.md)

---

**Like this plugin?** ⭐ Star the repo and share it with the OctoPrint community!
