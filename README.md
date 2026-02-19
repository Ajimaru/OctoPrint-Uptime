<!-- markdownlint-disable MD041 MD033 -->
<p align="center">
  <img src="octoprint_uptime/static/img/uptime.svg" alt="OctoPrint Uptime Logo" width="96" />
</p>
<h1 align="center">OctoPrint‑Uptime</h1>
<!-- markdownlint-enable MD041 MD033 -->

[![License](https://img.shields.io/github/license/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![OctoPrint](https://img.shields.io/badge/OctoPrint-1.10.0%2B-blue.svg)](https://octoprint.org)
[![Latest Release](https://img.shields.io/github/v/release/Ajimaru/OctoPrint-Uptime?sort=semver)](https://github.com/Ajimaru/OctoPrint-Uptime/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Ajimaru/OctoPrint-Uptime/total.svg)](https://github.com/Ajimaru/OctoPrint-Uptime/releases)
[![Made with Love](https://img.shields.io/badge/made_with-❤️-ff69b4)](https://github.com/Ajimaru/OctoPrint-Uptime)

### Effortlessly track your OctoPrint server's uptime, right from your navbar

<!-- markdownlint-disable MD033-->
<strong>
  Lightweight OctoPrint plugin that displays both host system and OctoPrint process uptime in the navbar and exposes a small JSON API for tooling and integrations.<br />
</strong>
</br />
<img src="assets/img/uptime_navbar.png" alt="OctoPrint Uptime Navbar" width="666" />
<!-- markdownlint-enable MD033-->

## Highlights

- 🖥️ Navbar widget displaying system and OctoPrint uptime with configurable formats (full / dhm / dh / d)
- 🔒 Small read‑only API at `/api/plugin/octoprint_uptime` (OctoPrint auth enforced)
- ⚙️ Configurable polling interval and optional compact toggle mode

## Installation

### Via Plugin Manager (Recommended)

1. Open OctoPrint web interface
2. Navigate to **Settings** → **Plugin Manager**
3. Click **Get More...**
4. Click **Install from URL** and enter: `https://github.com/Ajimaru/OctoPrint-Uptime/releases/latest/download/OctoPrint-Uptime-latest.zip`

5. Click **Install**
6. Restart OctoPrint

### Manual Installation

<!-- markdownlint-disable MD033 -->
<details>
<summary>Manual pip install</summary>

`pip install https://github.com/Ajimaru/OctoPrint-Uptime/releases/latest/download/OctoPrint-Uptime-latest.zip`

The `releases/latest` URL always points to the newest stable release.

</details>
<!-- markdownlint-enable MD033 -->

## How It Works

The navbar widget polls the plugin API and displays both system and OctoPrint process uptime as formatted strings. The tooltip shows the calculated start datetimes for each enabled uptime type (localized).

### Note about uptime retrieval

The plugin determines system uptime using either `/proc/uptime` on Linux systems or the Python library `psutil`; OctoPrint process uptime is retrieved via the OctoPrint API. `psutil` is installed automatically as a dependency. If system uptime cannot be determined, the plugin API returns `uptime_available: false` along with a human‑readable `uptime_note`.

## Configuration

Configure the plugin in **Settings** → **OctoPrint Uptime**:

<!-- markdownlint-disable MD033 -->
<img src="assets/img/uptime_settings.png" alt="OctoPrint Uptime Settings" width="666" />
</br>
<details>
<summary>Settings Defaults</summary>

- `show_system_uptime`: `true` - Show system uptime in the OctoPrint navbar
- `show_octoprint_uptime`: `true` - Show OctoPrint uptime in the navbar
- `compact_display`: `false` - Toggle between system and OctoPrint uptime in the navbar
- `compact_toggle_interval_seconds`: `5` - Interval for toggling between system and OctoPrint uptime in seconds (validated and clamped between 5-60s)
- `display_format`: `full` - Display format for uptime (options: `full`, `dhm`, `dh`, `d`, `short`)
- `poll_interval_seconds`: `5` - Polling interval in seconds (validated and clamped between 1-120s)
- `debug`: `false` - Enable debug logging for troubleshooting
- `debug_throttle_seconds`: `60` - Throttle debug logs to reduce log spam (validated and clamped between 1-120s)

</details>
<!-- markdownlint-enable MD033 -->

## FAQ

**Q: The uptime in the navbar is not updating. What can I do?**
A: Ensure that the `Polling interval` setting is set to a reasonable value (default is 5 seconds). Check the browser console for any errors related to the plugin API. Also, verify that the plugin is enabled in the OctoPrint settings.

**Q: How can I change the display format of the uptime?**
A: You can change the display format in the plugin settings under `Display format`. Options include
`full`, `dhm`, `dh`, `d`, and `short`.

**Q: How do I access the uptime API?**
A: The uptime API is available at `/api/plugin/octoprint_uptime`. You need to include your OctoPrint API key in the request headers for authentication.
Quick curl example:

```bash
curl -s -H "X-Api-Key: $API_KEY" http://localhost:5000/api/plugin/octoprint_uptime | jq
```

**Q: Which OSes are supported?**
A: Linux is tested and supported. Other OSes may work but are not officially supported. See details in [How It Works](#note-about-uptime-retrieval).

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines and instructions.

Please also follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

AGPLv3 - See [LICENSE](LICENSE) for details.

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Ajimaru/OctoPrint-Uptime/issues)
- 💬 **Discussion**: [GitHub Discussions](https://github.com/Ajimaru/OctoPrint-Uptime/discussions)

Note: For logs and troubleshooting, enable "debug logging" in the plugin settings.

## Credits

- **Original Request**: [Issue 4355](https://github.com/OctoPrint/OctoPrint/issues/4355) by [@Oxize](https://github.com/Oxize) (2021)
- **Development**: Built following [OctoPrint Plugin Guidelines](https://docs.octoprint.org/en/main/plugins/index.html)
- **Contributors**: See [AUTHORS.md](AUTHORS.md)

## 100% Badge Coverage

Summary: this project exposes many status and quality badges (CI, linting, coverage, releases, maintenance, etc.). The full badge set is available below; click to expand for details.

<!-- markdownlint-disable MD033 -->
<details>
<summary>Show all badges</summary>

### 🏗️ 1. Build & Test Status

[![CI](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/ci.yml?query=branch%3Amain)
[![i18n](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/i18n.yml/badge.svg?branch=main)](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/i18n.yml?query=branch%3Amain)
[![Lint](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/lint.yml?query=branch%3Amain)
[![Docs workflow](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/docs.yml?query=branch%3Amain)
[![Bandit SARIF](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/bandit-sarif.yml/badge.svg?branch=main)](https://github.com/Ajimaru/OctoPrint-Uptime/actions/workflows/bandit-sarif.yml?query=branch%3Amain)

### 🧪 2. Code Quality & Formatting

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg)](https://github.com/prettier/prettier)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/1b946ed41ef2479fa1eb254e6eea9fb0)](https://app.codacy.com/gh/Ajimaru/OctoPrint-Uptime/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Codacy Coverage](https://app.codacy.com/project/badge/Coverage/1b946ed41ef2479fa1eb254e6eea9fb0)](https://app.codacy.com/gh/Ajimaru/OctoPrint-Uptime)
[![Coverage](https://codecov.io/gh/Ajimaru/OctoPrint-Uptime/graph/badge.svg?branch=main)](https://codecov.io/gh/Ajimaru/OctoPrint-Uptime)
[![Coverage Diff](https://codecov.io/gh/Ajimaru/OctoPrint-Uptime/branch/main/graph/badge.svg?flag=patch)](https://codecov.io/gh/Ajimaru/OctoPrint-Uptime)
[![Pylint Score](https://img.shields.io/badge/pylint-10.0-green.svg)](https://www.pylint.org/)
[![Bandit Security](https://img.shields.io/badge/bandit-security-green.svg)](https://bandit.readthedocs.io/en/latest/)
[![Depfu](https://img.shields.io/badge/dependencies-managed%20by%20Depfu-blue)](https://depfu.com/repos/github/Ajimaru/OctoPrint-Uptime)
[![Known Vulnerabilities](https://snyk.io/test/github/Ajimaru/OctoPrint-Uptime/badge.svg)](https://snyk.io/test/github/Ajimaru/OctoPrint-Uptime)

### 🔄 3. CI/CD & Release

[![SemVer](https://img.shields.io/badge/semver-2.0.0-blue)](https://semver.org/)
[![Release Date](https://img.shields.io/github/release-date/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/releases)
[![Latest Release](https://img.shields.io/github/v/release/Ajimaru/OctoPrint-Uptime?sort=semver)](https://github.com/Ajimaru/OctoPrint-Uptime/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Ajimaru/OctoPrint-Uptime/total.svg)](https://github.com/Ajimaru/OctoPrint-Uptime/releases)
[![Pre‑Release](https://img.shields.io/github/v/release/Ajimaru/OctoPrint-Uptime?include_prereleases&label=pre-release)](https://github.com/Ajimaru/OctoPrint-Uptime/releases)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![OctoPrint](https://img.shields.io/badge/OctoPrint-1.10.0%2B-blue.svg)](https://octoprint.org)
[![Maintenance](https://img.shields.io/maintenance/yes/2026)](https://github.com/Ajimaru/OctoPrint-Uptime/graphs/commit-activity)

### 📊 4. Repository Activity

[![Open Issues](https://img.shields.io/github/issues/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/issues?q=is%3Aissue%20state%3Aopen)
[![Closed Issues](https://img.shields.io/github/issues-closed-raw/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/issues?q=is%3Aissue%20state%3Aclosed)
[![Open PRs](https://img.shields.io/github/issues-pr/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/pulls?q=is%3Apr+is%3Aopen)
[![Closed PRs](https://img.shields.io/github/issues-pr-closed/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/pulls?q=is%3Apr+is%3Aclosed)
[![Last Commit](https://img.shields.io/github/last-commit/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/commits/main)
[![Commit Activity (year)](https://img.shields.io/github/commit-activity/y/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/graphs/commit-activity)
[![Contributors](https://img.shields.io/github/contributors/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/graphs/contributors)

### 🧾 5. Metadata

![Code Size](https://img.shields.io/github/languages/code-size/Ajimaru/OctoPrint-Uptime)
[![Security](https://img.shields.io/badge/security-policy-blue)](https://github.com/Ajimaru/OctoPrint-Uptime/blob/main/SECURITY.md)
[![Snyk](https://img.shields.io/badge/security-snyk-blueviolet)](https://app.snyk.io)
![Languages Count](https://img.shields.io/github/languages/count/Ajimaru/OctoPrint-Uptime)
![Top Language](https://img.shields.io/github/languages/top/Ajimaru/OctoPrint-Uptime)
[![License](https://img.shields.io/github/license/Ajimaru/OctoPrint-Uptime)](https://github.com/Ajimaru/OctoPrint-Uptime/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Ajimaru/OctoPrint-Uptime/pulls)

</details>
<!-- markdownlint-enable MD033 -->

---

![Stars](https://img.shields.io/github/stars/Ajimaru/OctoPrint-Uptime?style=social) ![Forks](https://img.shields.io/github/forks/Ajimaru/OctoPrint-Uptime?style=social) ![Watchers](https://img.shields.io/github/watchers/Ajimaru/OctoPrint-Uptime?style=social)

**Like this plugin?** ⭐ Star the repo and share it with the OctoPrint community!
