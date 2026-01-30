"""OctoPrint-Uptime plugin module.

Provides a small API endpoint that returns formatted system uptime.
This module avoids importing OctoPrint/Flask at import-time so it can be
packaged and unit-tested without the OctoPrint runtime present.
"""

from ._version import VERSION
from .plugin import (
    OctoprintUptimePlugin,
    format_uptime,
    format_uptime_d,
    format_uptime_dh,
    format_uptime_dhm,
)

# Backwards-compatible alias expected by tests
UptimePlugin = OctoprintUptimePlugin

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

# Plugin registration for OctoPrint
__plugin_name__ = "OctoPrint-Uptime"
__plugin_version__ = VERSION
__plugin_description__ = "Adds system uptime to the navbar and exposes a small uptime API."
__plugin_author__ = "Ajimaru"
__plugin_url__ = "https://github.com/Ajimaru/OctoPrint-Uptime"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">3.7,<3.13"
__plugin_implementation__ = OctoprintUptimePlugin()
