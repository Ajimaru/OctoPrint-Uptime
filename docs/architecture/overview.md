# Architecture Overview

This page gives a concise overview of the main components of the OctoPrint-Uptime plugin and links to more detailed architecture pages.

## Components

- Backend: A small Python module that exposes a plugin API endpoint at `/api/plugin/octoprint_uptime` (returns both system and OctoPrint process uptime) and helper functions for formatting uptime values.
- Frontend: A Knockout.js ViewModel that queries the plugin API periodically and updates the navbar display with configurable uptime values and optional compact toggle mode.
- Settings: Plugin settings control the polling interval, which uptime values
  are shown in the navbar (`show_system_uptime`, `show_octoprint_uptime`),
  whether compact alternating mode is active (`compact_display`), and the
  display format.
- Internationalization: Translatable strings provided via `translations/` and compiled with `pybabel`.

## Quick links

- [Data flow](data-flow.md)
- [Algorithms & formatting](algorithms.md)
- [Settings reference](settings.md)
- [OctoPrint integration](octoprint-integration.md)

The class/interaction diagrams used in the docs are available below; see the reference section for more context.

- Compact class diagram: See [../reference/diagrams/classes.md](../reference/diagrams/classes.md)
- Detailed class diagram (includes private/protected members): See [../reference/diagrams/classes_detailed.md](../reference/diagrams/classes_detailed.md)
- Package/module overview: See [../reference/diagrams/packages.md](../reference/diagrams/packages.md)

Note: The SVG diagrams are auto-generated during CI and available when viewing the rendered documentation online.
