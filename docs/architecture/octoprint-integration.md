# OctoPrint Integration

This page explains how the plugin integrates with OctoPrint and how other plugins or scripts can consume its API and helpers.

## Plugin registration

- The plugin registers an API endpoint under `/api/plugin/octoprint_uptime`.
- It exposes helper functions and formatting utilities in the `octoprint_uptime` Python package which other plugins may import if installed in the same environment.

## Consuming the API (frontend)

Use OctoPrint's JavaScript helper to query the plugin API:

```js
OctoPrint.simpleApiGet("octoprint_uptime").done(function (data) {
  // System uptime:
  // data.seconds - raw system uptime in seconds
  // data.uptime, data.uptime_dhm, data.uptime_dh, data.uptime_d - formatted variants
  //
  // OctoPrint process uptime:
  // data.octoprint_seconds - raw OctoPrint uptime in seconds
  // data.octoprint_uptime, data.octoprint_uptime_dhm, etc. - formatted variants
  //
  // Configuration & metadata:
  // data.display_format - current display format preference
  // data.poll_interval_seconds - recommended polling interval
});
```

`data.seconds` / `data.uptime` describe host system uptime, while
`data.octoprint_seconds` / `data.octoprint_uptime` describe the OctoPrint process uptime.

**Successful API responses include the following fields:**

- `seconds`, `uptime`, `uptime_dhm`, `uptime_dh`, `uptime_d`: System uptime information in seconds and formatted variants
- `octoprint_seconds`, `octoprint_uptime`, `octoprint_uptime_dhm`, `octoprint_uptime_dh`, `octoprint_uptime_d`: OctoPrint process uptime information
- `display_format`: The currently configured display format preference
- `poll_interval_seconds`: Recommended polling interval for the client

**Error responses** (e.g., permission denied) include:

- `error`: Error message
- `uptime_available`: Boolean `false` indicating that uptime information could not be determined or returned

## Consuming from Python (other plugins)

```py
from octoprint_uptime import format_uptime

print(format_uptime(3600))
```

## Permissions & security

- The plugin API follows OctoPrint's plugin API model; only authenticated requests with sufficient permissions can change settings.
- Read-only API access for uptime is allowed for authenticated UI sessions.
