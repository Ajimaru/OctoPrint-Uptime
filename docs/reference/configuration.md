# Configuration

This page documents the plugin settings and their defaults. The source of truth is
the `get_settings_defaults()` method in `octoprint_uptime/plugin.py`.

Settings (defaults):

- `debug` (bool) - default: `false`\
   Enable throttled debug logging for the plugin (for example, API access messages).
  Other debug/info messages still depend on OctoPrint's global log level.

- `show_system_uptime` (bool) - default: `true`\
   Controls whether the system uptime is shown in the OctoPrint navbar.

- `show_octoprint_uptime` (bool) - default: `true`\
   Controls whether the OctoPrint process uptime is shown in the navbar.

- `compact_display` (bool) - default: `false`\
   When enabled and both uptimes are shown, alternates between system and OctoPrint uptime. Has no effect if fewer than two uptimes are visible.

- `compact_toggle_interval_seconds` (int) - default: `5`\
   Interval in seconds between navbar uptime switches when compact mode is active.
  Valid range: 5-60 seconds (integers only). Values are validated and clamped by
  the plugin on save.

- `display_format` (string) - default: `"full"`\
   Controls the default formatted uptime string returned by the API and used in
  the UI. Valid values include `full`, `dhm`, `dh`, and `d` which map to the
  helper formatters exposed by the plugin (see [API docs](../api/python.md)).

- `debug_throttle_seconds` (int) - default: `60`\
   Minimum interval (in seconds) between repeated debug log messages to avoid
  logging spam when debug mode is enabled. Values are validated and clamped
  to a sensible range (currently 1-120 seconds).

- `poll_interval_seconds` (int) - default: `5`\
   Suggested polling interval (in seconds) that clients can use to refresh the
  uptime display. The frontend uses this to adjust its polling frequency. The
  plugin validates and clamps this value (1-120 seconds).

## Changing settings

You can adjust these settings via OctoPrint's `Settings` → `Plugin OctoPrint-Uptime` UI,
or programmatically using OctoPrint's settings API. Numeric fields are validated
and clamped to sensible ranges by the plugin (e.g., interval values are bounded).
