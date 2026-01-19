\*\*Frontend – API & Testbeispiele

- **Endpoint**: `/api/plugin/octoprint_uptime`
- **Kurz**: Liefert Uptime‑Darstellungen und empfohlene Client‑Einstellungen (z. B. `poll_interval_seconds`).

Beispielantwort (partial):

```json
{
  "seconds": 3600,
  "uptime": "1 hour",
  "uptime_dhm": "0d 1h 0m",
  "uptime_short": "1h",
  "navbar_enabled": true,
  "display_format": "dhm",
  "poll_interval_seconds": 5
}
```

Schnelltest (lokales OctoPrint, mit API‑Key falls benötigt):

```bash
# Mit API-Key
curl -s -H "X-Api-Key: $API_KEY" http://localhost:5000/api/plugin/octoprint_uptime | jq

# Nur Sekundenwert anzeigen
curl -s -H "X-Api-Key: $API_KEY" http://localhost:5000/api/plugin/octoprint_uptime | jq '.seconds'
```

Poll‑Intervall prüfen / testen:

- Die UI verwendet serverseitig gespeicherte `poll_interval_seconds`, falls gesetzt. Der Client fragt diesen Wert bei jedem Poll ab und passt seinen Timer an.
- Zum Testen kannst du in den Plugin‑Einstellungen (`Settings` → `Plugin OctoPrint Uptime`) den Wert `Polling interval` ändern und beobachten, ob die Client‑Polling‑Frequenz im Browser anpasst.

Debugging‑Tipps:

- Wenn die Navbar nicht angezeigt wird, prüfe `navbar_enabled` im API‑Response.
- Bei leeren/fehlerhaften Antworten: prüfe OctoPrint‑Logs und verwende `curl` mit `-v` zur Fehlersuche.

Weitere Ergänzungen:

- Wenn du möchtest, kann ich noch ein kurzes Beispiel hinzufügen, wie man die Plugin‑Einstellungen per API ändert (erfordert Authentifizierung und Kenntnisse der OctoPrint Settings API).
