"""OctoPrint plugin template with a minimal settings pane."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, List

from flask_babel import gettext
import octoprint.plugin

try:  # pragma: no cover - during editable installs the dist name may be absent
    __version__ = version("OctoPrint-PluginTemplate")
except PackageNotFoundError:  # pragma: no cover - fallback for development
    __version__ = "0.0.0"


class PluginTemplatePlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
):
    """Minimal example plugin implementation."""

    def get_settings_defaults(self) -> Dict[str, Any]:
        return {
            "example_toggle": True,
            "example_text": gettext("Hello from your plugin!"),
        }

    def get_template_configs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "settings",
                "name": gettext("Plugin Template"),
                "template": "octoprint_plugin_template/settings.jinja2",
                "custom_bindings": False,
            }
        ]

    def on_settings_save(self, data: Dict[str, Any]) -> None:
        super().on_settings_save(data)
        self._logger.info("Settings saved: %s", self._settings.get_all_data())


__plugin_name__ = "Plugin Template"
__plugin_pythoncompat__ = ">=3.11,<4"
__plugin_version__ = __version__
__plugin_description__ = "Starter template for building OctoPrint plugins"


def __plugin_load__() -> None:
    global __plugin_implementation__
    __plugin_implementation__ = PluginTemplatePlugin()
