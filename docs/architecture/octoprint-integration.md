# OctoPrint Integration

This page explains how the plugin integrates with OctoPrint and how other plugins or scripts can consume its API and helpers.

Plugin registration

- The plugin registers an API endpoint under `/api/plugin/octoprint_uptime`.
- It exposes helper functions and formatting utilities in the `octoprint_uptime` Python package which other plugins may import if installed in the same environment.

Consuming the API (frontend)

Use OctoPrint's JavaScript helper to query the plugin API:

```js
OctoPrint.simpleApiGet("octoprint_uptime").done(function (data) {
  // data.seconds, data.uptime, data.uptime_available, data.uptime_note
});
```

Consuming from Python (other plugins)

```py
from octoprint_uptime.plugin import format_uptime

print(format_uptime(3600))
```

Permissions & security

- The plugin API follows OctoPrint's plugin API model; only authenticated requests with sufficient permissions can change settings.
- Read-only API access for uptime is allowed for authenticated UI sessions.
