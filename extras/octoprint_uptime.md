---
layout: plugin

id: octoprint_uptime
title: OctoPrint-Uptime
description: Displays the host system and OctoPrint process uptime in the navbar and provides a JSON API for integrations.
authors:
  - Ajimaru
license: AGPLv3

date: 2026-02-18

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
    - 1.10.0
  os:
    - linux
  python: ">=3.8,<3.14"
---

OctoPrint-Uptime is a lightweight plugin that displays both the host system uptime and OctoPrint process uptime in the navbar. Additionally, it provides a small, authenticated JSON API that can be queried by external tools or scripts.

**Features:**

- Display system and/or OctoPrint process uptime independently or with optional compact alternating mode
- Configurable display format (full, dhm, dh, d)
- Adjustable polling interval
- Secure (authenticated API, no unauthorized access)
- Translatable (i18n ready, German/English)

**Installation:**
Via the Plugin Manager using the URL from the README or manually via pip.

**Configuration:**
All settings are available in the OctoPrint UI under "OctoPrint Uptime".

## How Uptime is Retrieved

- The plugin reads system uptime from `/proc/uptime` on Linux or via the `psutil` Python package when available.
- If neither source is available the API sets `uptime_available: false`, and may include an `uptime_note` with remediation instructions (for example, suggesting `pip install psutil` in the OctoPrint virtualenv).

GET `/api/plugin/octoprint_uptime` (OctoPrint API key required)

**Lizenz:**
AGPLv3
