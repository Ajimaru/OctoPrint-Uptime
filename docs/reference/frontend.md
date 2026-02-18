# Frontend - API & Test Examples

- **Endpoint**: `/api/plugin/octoprint_uptime`
- **Summary**: Returns uptime representations and recommended client settings (e.g., `poll_interval_seconds`).

Example response (partial):

```json
{
  "seconds": 3600,
  "uptime": "1 hour",
  "uptime_dhm": "0d 1h 0m",
  "uptime_short": "1h",
  "display_format": "dhm",
  "poll_interval_seconds": 5,
  "uptime_available": true,
  "uptime_note": null
}
```

Quick test (local OctoPrint, with API key if needed):

```bash
# With API key
curl -s -H "X-Api-Key: $API_KEY" http://localhost:5000/api/plugin/octoprint_uptime | jq

# Show only seconds value
curl -s -H "X-Api-Key: $API_KEY" http://localhost:5000/api/plugin/octoprint_uptime | jq '.seconds'
```

Check / test poll interval:

- The UI uses the server-side stored `poll_interval_seconds` if set. The client queries this value on each poll and adjusts its timer accordingly.
- For testing, you can change the value `Polling interval` in the plugin settings (`Settings` → `Plugin OctoPrint Uptime`) and observe if the client polling frequency in the browser adapts.

## Handling unavailable uptime

- If the API returns `uptime_available: false` the client should fall back to a sensible UI state (for example display "unknown") and surface the localized `uptime_note` when present to guide remediation.

## Navbar show / hide behaviour

Navbar visibility is driven entirely by the JavaScript ViewModel:

- The element is shown (`navbarEl.show()`) when at least one of `show_system_uptime`
  or `show_octoprint_uptime` is enabled.
- When both settings are `false` the element is hidden (`navbarEl.hide()`) and
  polling continues at the configured interval so the widget reappears
  immediately when a setting is re-enabled without a page reload.
- Compact mode (`compact_display: true`) is active only when **both** uptime
  types are enabled; it alternates the displayed entry at the interval configured
  by `compact_toggle_interval_seconds` (default: 5 seconds, range: 5-60 seconds).
- The navbar mouseover tooltip is updated in both regular and compact modes
  and shows the same localized start-time details (`System Started`,
  `OctoPrint Started`) as long as the corresponding uptime values are enabled.

## Startup lifecycle

The polling loop starts in the OctoPrint `onStartupComplete` hook rather than
in the ViewModel constructor. This guarantees that `settingsViewModel.settings`
is fully populated when the first settings read occurs. Starting the loop
prematurely (in the constructor) caused settings reads to silently fail and
return their default values, which made the show/hide and compact-mode logic
appear broken.

## Debugging tips

- If the navbar is not displayed, check `show_system_uptime` and `show_octoprint_uptime`
  in the plugin settings (Settings → Plugin OctoPrint-Uptime).
- Enable `debug: true` in the plugin settings to get throttled server-side log
  messages from each API call.
- For empty or faulty responses: check OctoPrint logs and use `curl -v` for troubleshooting.

## Further additions

- See the OctoPrint Settings API documentation for examples on how to change plugin settings via API (requires authentication).

## Translations / testing localized strings

When you need to test localized frontend strings, compile the translations and copy compiled catalogs into the package for runtime use.

This ensures localized strings (e.g. `uptime_note`) are available at runtime.
