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
  - **Polling continues when both are disabled because:** It keeps detecting runtime changes and config updates.
- When both are enabled and `compact_display` is `true`, the navbar alternates
  between system and OctoPrint uptime at the configured
  `compact_toggle_interval_seconds` interval (default 5s, range 5-60 seconds)
  without an additional API call.
- The poll interval is taken from the server response (`poll_interval_seconds`);
  if absent it falls back to the local setting (the frontend-configured
  `poll_interval_seconds` value) and then to the built-in default of 5 seconds.
- Configuration is accessed through a `getPluginSettings()` helper that
  re-resolves `settingsViewModel.settings.plugins.octoprint_uptime` on every
  call, avoiding stale captures from early construction time.
- On each fetch the UI updates the navbar text and refreshes the localized
  tooltip content (`System Started`, `OctoPrint Started`) in both regular and
  compact modes.
- Scheduling is adjusted accordingly based on the poll interval.

### Rationale

The ViewModel continues to poll to detect runtime changes to those settings (allowing the navbar to be re-shown without a page reload), to pick up remote or central config updates, and to keep the ViewModel lifecycle simple rather than introducing pause/resume logic.

## Resilience

- **Error handling:** When the API fetch fails, the ViewModel displays "Error" in the navbar and continues polling at the fixed `DEFAULT_POLL` interval (5 seconds) without requiring manual intervention.
- **Graceful degradation:** When uptime data is unavailable (e.g., `/proc/uptime` not accessible on Linux or `psutil` not installed), the API returns `uptime_available: false` and includes an optional `uptime_note` with remediation guidance (e.g., "psutil not available; install via `pip install psutil`"). The UI surfaces this note to help operators resolve the issue.
- **Throttled logging:** Debug log entries are throttled to avoid spam; plugin debug flag controls only these throttled entries while general logs depend on OctoPrint's global log level.
- **Continued operation:** The widget tolerates transient failures and continues polling and refreshing the display, allowing automatic recovery when the API becomes available again without requiring a page reload.
