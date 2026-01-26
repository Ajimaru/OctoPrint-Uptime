# Settings Reference

This document lists the plugin settings that affect the uptime display and polling behavior.

Settings

| Setting                 | Type    | Default | Description                                                                 |
| ----------------------- | ------- | ------: | --------------------------------------------------------------------------- |
| `navbar_enabled`        | boolean |  `true` | Show uptime in the navbar when enabled.                                     |
| `display_format`        | string  |   `dhm` | Format of uptime display. One of `full`, `dhm`, `dh`, `d`, `short`.         |
| `poll_interval_seconds` | integer |     `5` | Client polling interval in seconds (frontend may respect server overrides). |

Where to change

Change these values in the plugin settings panel in OctoPrint or via the configuration file when installing headless.
