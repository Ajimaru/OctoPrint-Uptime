# Settings Reference

This document lists the plugin settings that affect the uptime display and polling behavior.

## Settings

| Setting                           | Type    | Default | Description                                                                                                                                                                                                                    |
| --------------------------------- | ------- | ------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `debug`                           | boolean | `false` | Enable debug logging for the plugin (throttled by `debug_throttle_seconds`).                                                                                                                                                   |
| `show_system_uptime`              | boolean |  `true` | Show system uptime in the navbar when enabled.                                                                                                                                                                                 |
| `show_octoprint_uptime`           | boolean |  `true` | Show OctoPrint uptime in the navbar when enabled.                                                                                                                                                                              |
| `compact_display`                 | boolean | `false` | Alternate between system and OctoPrint uptime only when both `show_system_uptime` and `show_octoprint_uptime` are enabled; if only one is enabled, that uptime is shown continuously.                                          |
| `compact_toggle_interval_seconds` | integer |     `5` | Seconds between navbar switches in compact mode; values are validated as integers and constrained to 5-60 (invalid values fall back to default, then are clamped).                                                             |
| `display_format`                  | string  |  `full` | Format of uptime display. One of `full`, `dhm`, `dh`, `d`, `short`.                                                                                                                                                            |
| `debug_throttle_seconds`          | integer |    `60` | Minimum seconds between debug log entries; values are validated as integers and constrained to 1-120 (invalid values fall back to default, then are clamped).                                                                  |
| `poll_interval_seconds`           | integer |     `5` | Client polling interval in seconds; the frontend uses the API response `poll_interval_seconds` when present, otherwise it falls back to the local setting (e.g., API sends `10` → poll every 10s, else use the configured 5s). |

## Where to change

Change these values in the plugin settings panel in OctoPrint or via the configuration file when installing headless.
