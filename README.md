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

OctoPrint-Uptime zeigt die System-Uptime an und bietet eine kleine API.

Aktueller Status: Release Candidate 0.1.0rc52

Kurz:

- Zeigt die System-Uptime in der Navbar an.
- Bietet ein kleines API-Endpunkt unter `/api/plugin/octoprint_uptime` (geschützt, Auth erforderlich).

Wichtiges Verhalten in dieser Version:

- `debug` Standard ist auf `false` gesetzt (weniger Lärm in Logs).
- `is_api_protected()` ist standardmäßig aktiv (`True`) — API-Zugriff erfordert OctoPrint-Berechtigungen.

## How to use this template

1. **Create your repo from this template** (GitHub → Use this template).
2. **Configure GitHub settings**: See [.github/GITHUB_REPO_SETTINGS.md](.github/GITHUB_REPO_SETTINGS.md).
3. **Replace all placeholders** with your actual values: See [.github/TEMPLATE_SETUP.md](.github/TEMPLATE_SETUP.md) for detailed instructions on all files requiring changes.
4. **Test locally**: `pytest && pre-commit run --all-files`
5. **Push and verify** CI workflows run successfully on first commit.

## Features

- Zeigt die Host-System-Uptime in der Navbar.
- Kleines, gelesenes API-Endpunkt, das formatierte Uptime zurückgibt.
- Frontend-Widget aktualisiert die Anzeige periodisch (kurzes Polling).

## Development quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip build
python3 -m pip install -e ".[develop]"
pre-commit install
pytest
```

Zum lokalen Testen: die `.development/restart_octoprint_dev.sh`-Hilfe im Repo nutzt ein lokales OctoPrint-Dev-Setup. Nach Änderungen am Template oder an den Assets `./.development/restart_octoprint_dev.sh --clear-cache` ausführen.

## Translations

Übersetzungsdateien liegen unter `octoprint_uptime/translations`. Kataloge neu erzeugen / kompilieren mit Babel/pybabel nach Änderungen an Nutzertexten.

Für Nutzer: vorgebaute Releases sind unter Releases auf GitHub verfügbar.

## Configuration

### Settings Defaults

Die folgenden Standardwerte werden vom Plugin verwendet (siehe `get_settings_defaults()`):

- `debug`: `false`
- `navbar_enabled`: `true`
- `display_format`: `"full"` (Tage + Stunden + Minuten + Sekunden)
- `debug_throttle_seconds`: `60`

### Verhalten

- API-Zugriff ist standardmäßig geschützt — OctoPrint-Berechtigungen werden geprüft.
- Debug-Logging ist standardmäßig deaktiviert; aktivierbar in den Plugin-Einstellungen.

## How It Works

Das Plugin stellt einen kleinen JSON-Endpunkt unter `/api/plugin/octoprint_uptime` bereit, und ein kleines Knockout-basiertes Navbar-Widget pollt diesen Endpunkt und zeigt die formatierte Uptime an.

## FAQ

- Wie aktiviere ich Debug-Logs? → In den Plugin-Einstellungen die Option "Debug" einschalten.
- Warum ist die API geschützt? → Sicherheitsgründe; personenbezogene oder systemkritische Infos werden nur nach OctoPrint-Berechtigung ausgegeben.

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

- **Original Request**: [Issue ](https://github.com/OctoPrint/OctoPrint/issues/xxx) by [@](https://github.com/) (20xx)
- **Development**: Built following [OctoPrint Plugin Guidelines](https://docs.octoprint.org/en/latest/plugins/index.html)
- **Contributors**: See [AUTHORS.md](AUTHORS.md)

---

**Like this plugin?** ⭐ Star the repo and share it with the OctoPrint community!
