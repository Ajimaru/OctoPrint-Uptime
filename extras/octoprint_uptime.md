---
layout: plugin

id: octoprint_uptime
title: OctoPrint-Uptime
description: Displays the host system uptime in the OctoPrint navbar and provides a small JSON API for integrations.
authors:
  - Ajimaru
license: AGPLv3

date: 2026-01-19

homepage: https://ajimaru.github.io/OctoPrint-Uptime/
source: https://github.com/Ajimaru/OctoPrint-Uptime
archive: https://github.com/Ajimaru/OctoPrint-Uptime/archive/main.zip

tags:
  - system
  - uptime
  - status
  - navbar

screenshots:
  - url: /assets/img/uptime_navbar.png
    alt: OctoPrint Uptime Navbar Widget
    caption: Uptime display in the OctoPrint navbar
  - url: /assets/img/uptime_settings.png
    alt: OctoPrint Uptime Settings
    caption: Plugin settings in the OctoPrint UI

featuredimage: /octoprint_uptime/static/img/uptime.svg

compatibility:
  octoprint:
    - 1.12.0
  os:
    - linux
  python: ">=3.10,<4"
---

OctoPrint-Uptime is a lightweight plugin that displays the system uptime of your OctoPrint server directly in the navbar. Additionally, it provides a small, authenticated JSON API that can be queried by external tools or scripts.

**Features:**

- Configurable display format (full, dhm, dh, d)
- Adjustable polling interval
- Optional: Systeminfo bundle for support purposes
- Secure (authenticated API, no unauthorized access)
- Translatable (i18n ready, German/English)

## Uptime retrieval changes

- The plugin no longer executes the system `uptime` binary.
- Uptime is retrieved by one of two methods:
  - `/proc/uptime` (Linux)
  - the `psutil` Python package (when available)
- If neither source is available the API will set `uptime_available: false` and may include an `uptime_note` with remediation instructions (for example suggesting `pip install psutil` in the OctoPrint virtualenv).

**Installation:**
Via the Plugin Manager using the URL from the README or manually via pip.

**Configuration:**
All settings are available in the OctoPrint UI under "OctoPrint Uptime".

GET `/api/plugin/octoprint_uptime` (OctoPrint API key required)

**Lizenz:**
AGPLv3
