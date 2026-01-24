# -*- coding: utf-8 -*-
"""OctoPrint-Uptime plugin module.

Provides a small API endpoint that returns formatted system uptime.
This module avoids importing OctoPrint/Flask at import-time so it can be
packaged and unit-tested without the OctoPrint runtime present.
"""

from ._version import VERSION
from .plugin import format_uptime  # noqa: F401
from .plugin import format_uptime_d  # noqa: F401
from .plugin import format_uptime_dh  # noqa: F401
from .plugin import format_uptime_dhm  # noqa: F401

# Public API
__all__ = [
    "VERSION",
    "OctoprintUptimePlugin",
    "UptimePlugin",
    "format_uptime",
    "format_uptime_d",
    "format_uptime_dh",
    "format_uptime_dhm",
]
from .plugin import OctoprintUptimePlugin

# Backwards-compatible alias expected by tests
UptimePlugin = OctoprintUptimePlugin

# Plugin registration for OctoPrint
__plugin_name__ = "OctoPrint-Uptime"
__plugin_pythoncompat__ = ">=3.10,<4"
__plugin_implementation__ = OctoprintUptimePlugin()
__plugin_description__ = (
    "Adds system uptime to the navbar and exposes a small uptime API."
)
__plugin_license__ = "AGPLv3"
__plugin_version__ = VERSION
