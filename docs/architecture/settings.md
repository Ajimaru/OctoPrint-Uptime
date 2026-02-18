# Settings Reference

This document lists the plugin settings that affect the uptime display and polling behavior.

## Settings

- `debug` (boolean, default `false`): Enable throttled plugin debug entries (for example, uptime API access messages); throttling duration is controlled by `debug_throttle_seconds`. Other debug/info output still depends on OctoPrint's global log level.
- `show_system_uptime` (boolean, default `true`): Show system uptime in the navbar when enabled.
- `show_octoprint_uptime` (boolean, default `true`): Show OctoPrint uptime in the navbar when enabled.
- `compact_display` (boolean, default `false`): Alternate between system and OctoPrint uptime only when both `show_system_uptime` and `show_octoprint_uptime` are enabled; if only one is enabled, that uptime is shown continuously; if both are disabled, no uptime is displayed.
- `compact_toggle_interval_seconds` (integer, default `5`): Seconds between navbar switches in compact mode; values that cannot be parsed as integers (invalid or non-numeric input) fall back to the default (5), and integer values outside 5-60 are clamped to the nearest bound.
- `display_format` (string, default `full`): Format of uptime display. Options:
  - `full` (default): Human-friendly longest form; e.g., "2 days 3 hours 15 minutes"
  - `dhm`: Days, hours, minutes; e.g., "2d 3h 15m"
  - `dh`: Days, hours; e.g., "2d 3h"
  - `d`: Days only; e.g., "2d"
  - `short`: Compact machine-friendly form; e.g., "2d3h15m" or "2h15m" (omits zero-value leading components)
- `debug_throttle_seconds` (integer, default `60`): Minimum seconds between debug log entries; values that cannot be parsed as integers (invalid or non-numeric input) fall back to the default (60), and integer values outside 1-120 are clamped to the nearest bound.
- `poll_interval_seconds` (integer, default `5`): Client polling interval in seconds; the frontend uses the API response `poll_interval_seconds` when present, otherwise it falls back to the local setting (e.g., API sends `10` → poll every 10s, else use the configured 5s).

## Where to change

Change these values in the plugin settings panel in OctoPrint or via the configuration file when installing headless.
