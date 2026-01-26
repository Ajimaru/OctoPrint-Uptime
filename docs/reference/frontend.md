# Frontend – API & Test Examples

- **Endpoint**: `/api/plugin/octoprint_uptime`
- **Summary**: Returns uptime representations and recommended client settings (e.g., `poll_interval_seconds`).

Example response (partial):

```json
{
  "seconds": 3600,
  "uptime": "1 hour",
  "uptime_dhm": "0d 1h 0m",
  "uptime_short": "1h",
  "navbar_enabled": true,
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

- If the API returns `uptime_available: false` the client should fall back to a sensible UI state (for example display "unknown") and surface the localized `uptime_note` when present to guide remediation (e.g., "install psutil in OctoPrint virtualenv").

Debugging tips:

- If the navbar is not displayed, check `navbar_enabled` in the API response.
- For empty or faulty responses: check OctoPrint logs and use `curl -v` for troubleshooting.

Further additions:

- If you want, I can add a short example on how to change plugin settings via API (requires authentication and knowledge of the OctoPrint Settings API).
