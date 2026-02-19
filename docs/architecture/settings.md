# Settings Reference

This document lists the plugin settings that affect the uptime display and polling behavior.

## Settings

| Setting                           | Type    | Default | Description                                                                  |
| --------------------------------- | ------- | ------: | ---------------------------------------------------------------------------- |
| `debug`                           | boolean | `false` | Enable debug logging for the plugin (throttled by `debug_throttle_seconds`). |
| `show_system_uptime`              | boolean |  `true` | Show system uptime in the navbar when enabled.                               |
| `show_octoprint_uptime`           | boolean |  `true` | Show OctoPrint uptime in the navbar when enabled.                            |
| `compact_display`                 | boolean | `false` | Alternate between system and OctoPrint uptime in the navbar.                 |
| `compact_toggle_interval_seconds` | integer |     `5` | Seconds between navbar uptime switches in compact mode (5-60, integer).      |
| `display_format`                  | string  |  `full` | Format of uptime display. One of `full`, `dhm`, `dh`, `d`, `short`.          |
| `debug_throttle_seconds`          | integer |    `60` | Minimum seconds between debug log entries (1-120).                           |
| `poll_interval_seconds`           | integer |     `5` | Client polling interval in seconds (frontend may respect server overrides).  |

## Where to change

Change these values in the plugin settings panel in OctoPrint or via the configuration file when installing headless.
