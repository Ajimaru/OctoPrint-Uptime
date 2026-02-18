# Data flow

This page describes how uptime is computed and propagated from the server to the frontend, and how polling is coordinated.

## Server-side

- The plugin attempts to read system uptime via `psutil` (declared as a runtime dependency in `pyproject.toml`). If access is restricted the plugin returns an `uptime_available: false` and an optional `uptime_note` hint in the API response.
- Formatting helpers convert raw seconds into human-friendly strings (full, `dhm`, `dh`, `d`, short forms).

## API contract

Example response (partial):

```json
{
  "seconds": 3600,
  "uptime": "1 hour",
  "uptime_dhm": "0d 1h 0m",
  "display_format": "dhm",
  "poll_interval_seconds": 5,
  "uptime_available": true,
  "uptime_note": null
}
```

## Frontend polling

- The frontend ViewModel starts its polling loop in the OctoPrint `onStartupComplete`
  lifecycle hook (not in the constructor) to guarantee that `settingsViewModel.settings`
  is fully populated before the first settings read.
- On each cycle the ViewModel reads `show_system_uptime` and `show_octoprint_uptime`
  from the plugin settings. If both are `false` the navbar is hidden immediately
  via `navbarEl.hide()` and polling resumes after the configured interval.
- When both are enabled and `compact_display` is `true`, the navbar alternates
  between system and OctoPrint uptime every `COMPACT_TOGGLE_INTERVAL` seconds
  without an additional API call.
- The poll interval is taken from the server response (`poll_interval_seconds`);
  if absent it falls back to the local setting and then to the built-in default
  of 5 seconds.
- Configuration is accessed through a `getPluginSettings()` helper that
  re-resolves `settingsViewModel.settings.plugins.octoprint_uptime` on every
  call, avoiding stale captures from early construction time.
- On each fetch the UI updates the navbar text and adjusts scheduling; errors
  are tolerated and the widget falls back to a sensible retry schedule.

## Resilience

- When uptime is unavailable the UI surfaces the `uptime_note` to guide the operator.
