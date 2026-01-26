# Data flow

This page describes how uptime is computed and propagated from the server to the frontend, and how polling is coordinated.

## Server-side

- The plugin attempts to read system uptime via `psutil` when available. If `psutil` is not present or access is restricted the plugin returns an `uptime_available: false` and an optional `uptime_note` hint in the API response.
- Formatting helpers convert raw seconds into human-friendly strings (full, `dhm`, `dh`, `d`, short forms).

## API contract

Example response (partial):

```json
{
  "seconds": 3600,
  "uptime": "1 hour",
  "uptime_dhm": "0d 1h 0m",
  "navbar_enabled": true,
  "display_format": "dhm",
  "poll_interval_seconds": 5,
  "uptime_available": true,
  "uptime_note": null
}
```

## Frontend polling

- The frontend ViewModel polls the plugin API at the configured `poll_interval_seconds` (can be adjusted by server response).
- On each fetch the UI updates the navbar/text and adjusts scheduling; errors are tolerated and the widget falls back to a sensible retry schedule.

## Resilience

- When uptime is unavailable the UI should surface the `uptime_note` to guide the operator (for example a suggestion to install `psutil` into the OctoPrint virtualenv).
