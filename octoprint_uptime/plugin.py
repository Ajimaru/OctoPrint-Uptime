"""OctoPrint-Uptime plugin module.

Provides uptime information for OctoPrint instances,
including API, navbar, and settings integration.
"""

import gettext
import logging
import os
import subprocess
import time
from typing import Any, Dict, List, Tuple, Type

try:
    import flask as _flask  # type: ignore
except ImportError:
    _flask = None

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None

try:
    _ = gettext.gettext
except (ImportError, AttributeError):

    def _(message):
        return message


try:
    import octoprint.plugin  # type: ignore

    try:
        import octoprint.access.permissions as _perm  # type: ignore
    except ImportError:
        _perm = None
except ModuleNotFoundError:

    class _OctoPrintPluginStubs:
        class SettingsPlugin:
            """
            A plugin class for handling settings operations.

            This class provides methods to manage and process settings data
            within the OctoPrint-Uptime plugin.
            """

            def on_settings_save(self: Any, data: dict) -> dict:
                """
                Handle actions to perform when plugin settings are saved.

                Args:
                    data (dict): The settings data to be saved.

                Returns:
                    dict: The processed settings data.
                """
                return data

        class SimpleApiPlugin:
            """Stub for OctoPrint's SimpleApiPlugin.

            This class provides basic API plugin structure for environments
            where OctoPrint is not installed.
            """

            def on_api_get(self, _request: Any) -> Any:
                """Handle GET requests to the plugin's API endpoint.

                Args:
                    _request (Any): The incoming request object.

                Returns:
                    Any: The response to be returned.
                """
                return {}

            def is_api_protected(self) -> bool:
                """Indicate whether the API endpoint requires authentication.

                Returns:
                    bool: True if API is protected, False otherwise.
                """
                return True

        class AssetPlugin:
            """Stub for OctoPrint's AssetPlugin.

            This class provides basic asset plugin structure for environments
            where OctoPrint is not installed.
            """

            def get_assets(self) -> dict:
                """Return plugin asset files (stub).

                Returns:
                    dict: Asset file mapping.
                """
                return {}

            def asset_enabled(self) -> bool:
                """Indicate whether assets are enabled (stub).

                Returns:
                    bool: True if enabled, False otherwise.
                """
                return True

        class TemplatePlugin:
            """Stub for OctoPrint's TemplatePlugin.

            This class provides basic template plugin structure for environments
            where OctoPrint is not installed.
            """

            def get_template_configs(self) -> dict:
                """Return template configuration (stub).

                Returns:
                    dict: Template configuration mapping.
                """
                return {}

            def is_template_autoescaped(self) -> bool:
                """Indicate whether template autoescaping is enabled (stub).

                Returns:
                    bool: True if autoescaping is enabled, False otherwise.
                """
                return True

    class _OctoPrintStubs:
        plugin = _OctoPrintPluginStubs

    octoprint = _OctoPrintStubs()  # type: ignore

SettingsPluginBase: Type[Any] = getattr(
    octoprint.plugin, "SettingsPlugin", object
)  # type: ignore[attr-defined]
SimpleApiPluginBase: Type[Any] = getattr(
    octoprint.plugin, "SimpleApiPlugin", object
)  # type: ignore[attr-defined]
AssetPluginBase: Type[Any] = getattr(
    octoprint.plugin, "AssetPlugin", object
)  # type: ignore[attr-defined]
TemplatePluginBase: Type[Any] = getattr(
    octoprint.plugin, "TemplatePlugin", object
)  # type: ignore[attr-defined]
StartupPluginBase: Type[Any] = getattr(
    octoprint.plugin, "StartupPlugin", object
)  # type: ignore[attr-defined]

SystemInfoPluginBase: Type[Any] = getattr(
    octoprint.plugin, "SystemInfoPlugin", object
)  # type: ignore[attr-defined]

if SettingsPluginBase is object:

    class _SettingsPluginDummy:
        pass

    SettingsPluginBase = _SettingsPluginDummy
if TemplatePluginBase is object:

    class _TemplatePluginDummy:
        pass

    TemplatePluginBase = _TemplatePluginDummy
if SimpleApiPluginBase is object:

    class _SimpleApiPluginDummy:
        """Dummy SimpleApiPlugin with two public methods to satisfy linting."""

        def public_method_one(self):
            """A dummy public method."""
            return "method_one"

        def public_method_two(self):
            """Another dummy public method."""
            return "method_two"

    SimpleApiPluginBase = _SimpleApiPluginDummy
if AssetPluginBase is object:

    class _AssetPluginDummy:
        pass

    AssetPluginBase = _AssetPluginDummy
if StartupPluginBase is object:

    class _StartupPluginDummy:
        """Dummy StartupPlugin with two public methods to satisfy linting."""

        def public_method_one(self):
            """A dummy public method."""
            return "method_one"

        def public_method_two(self):
            """Another dummy public method."""
            return "method_two"

    StartupPluginBase = _StartupPluginDummy


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _format_uptime_dhm(seconds: float) -> str:
    seconds = int(seconds)
    days = seconds // 86400
    rem = seconds - days * 86400
    hours = rem // 3600
    rem = rem - hours * 3600
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def _format_uptime_dh(seconds: float) -> str:
    seconds = int(seconds)
    days = seconds // 86400
    rem = seconds - days * 86400
    hours = rem // 3600
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h"


def _format_uptime_d(seconds: float) -> str:
    seconds = int(seconds)
    days = seconds // 86400
    return f"{days}d"


class OctoprintUptimePlugin(
    SimpleApiPluginBase,
    AssetPluginBase,
    SettingsPluginBase,
    TemplatePluginBase,
    SystemInfoPluginBase,
):
    """OctoPrint plugin implementation.
    Uses lazy imports for OctoPrint/Flask integration points so the module
    can be imported in environments where OctoPrint is not installed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug_enabled = False
        self._navbar_enabled = True
        self._display_format = "full"
        self._last_debug_time = 0
        self._last_throttle_notice = 0
        self._debug_throttle_seconds = 60

    def get_update_information(self):
        """Return update information for the OctoPrint-Uptime plugin.

        This method provides metadata required for OctoPrint's update mechanism.

        Returns:
            dict: Update information dictionary.
        """
        return {
            "octoprint_uptime": {
                "displayName": "OctoPrint-Uptime",
                "displayVersion": "0.1.0rc5",
                "type": "github_release",
                "user": "Ajimaru",
                "repo": "OctoPrint-Uptime",
                "current": "0.1.0rc5",
                "pip": "https://github.com/Ajimaru/OctoPrint-Uptime/archive/{target_version}.zip",
            }
        }

    def is_api_protected(self) -> bool:
        """Indicate whether the plugin's API endpoint requires authentication.

        Returns:
            bool: True if API is protected, False otherwise.
        """
        return True

    def get_assets(self) -> Dict[str, List[str]]:
        """Return plugin asset files for OctoPrint-Uptime.

        Returns:
            Dict[str, List[str]]: Dictionary mapping asset types to file lists.
        """
        return {"js": ["js/uptime.js"]}

    def get_template_configs(self) -> List[Dict[str, Any]]:
        """
        Returns a list of template configuration dictionaries for the OctoPrint plugin.

        The configurations specify templates for the navbar and settings sections,
        including their types, display names, template file names,
        and whether they use custom bindings.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing template configuration details.
        """
        return [
            {
                "type": "navbar",
                "name": _("navbar_uptime"),
                "template": "navbar.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "settings",
                "name": _("OctoPrint Uptime"),
                "template": "settings.jinja2",
                "custom_bindings": False,
            },
        ]

    def is_template_autoescaped(self):
        """
        Determine if template autoescaping is enabled.

        Returns:
            bool: True if autoescaping is enabled for templates, otherwise False.
        """
        return True

    def _get_uptime_seconds(self) -> float:
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r", encoding="utf-8") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
        except (ValueError, TypeError, OSError):
            pass
        try:
            if psutil is not None:
                return time.time() - psutil.boot_time()
        except (AttributeError, OSError):
            pass
        try:
            args = ["uptime", "-s"]
            out = subprocess.check_output(args, stderr=subprocess.DEVNULL, shell=False)
            out = out.decode().strip()
            boot = time.mktime(time.strptime(out, "%Y-%m-%d %H:%M:%S"))
            return time.time() - boot
        except (subprocess.CalledProcessError, ValueError, OSError):
            return 0

    def get_uptime_seconds(self) -> float:
        """Public wrapper for `_get_uptime_seconds` for tests and external callers."""
        return self._get_uptime_seconds()

    def get_settings_defaults(self) -> Dict[str, Any]:
        """
        Return the default settings for the OctoPrint-Uptime plugin.

        Returns:
            Dict[str, Any]: A dictionary containing default configuration values.
        """
        return dict(
            debug=False,
            navbar_enabled=True,
            display_format="full",
            debug_throttle_seconds=60,
            poll_interval_seconds=5,
        )

    def on_settings_initialized(self) -> None:
        """
        Initializes plugin settings and configures debug logging.

        This method retrieves and sets internal variables based on the plugin's settings,
        such as debug mode, navbar display, display format, and debug throttle timing.
        If debug logging is enabled, it sets the logger level to DEBUG.

        Exceptions during logger configuration are caught and ignored.
        """
        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._last_debug_time = 0
        self._last_throttle_notice = 0
        self._debug_throttle_seconds = int(
            self._settings.get(["debug_throttle_seconds"]) or 60
        )
        try:
            if getattr(self, "_logger", None) and self._debug_enabled:
                try:
                    self._logger.setLevel(logging.DEBUG)
                    self._logger.debug(
                        "UptimePlugin: debug logging enabled (level DEBUG)"
                    )
                except (ValueError, TypeError):
                    pass
        except (KeyError, AttributeError):
            pass

    def on_after_startup(self) -> None:
        """
        Called after the OctoPrint server has started up.

        This method can be used to perform any initialization tasks or setup required
        after the server is fully running. Override this method to add custom startup logic.
        """
        return

    def on_settings_save(self, data: Dict[str, Any]) -> None:
        """
        Save plugin settings, validate config values, and update internal state.

        Args:
            data (Dict[str, Any]): Settings data to save.
        """
        self._validate_and_sanitize_settings(data)
        self._log_settings_save_data(data)
        self._call_base_on_settings_save(data)
        prev_navbar = getattr(self, "_navbar_enabled", None)
        self._update_internal_state()
        self._log_settings_after_save(prev_navbar)

    def _validate_and_sanitize_settings(self, data: Dict[str, Any]) -> None:
        """Validate and sanitize plugin settings in the provided data dict."""
        plugins = data.get("plugins") if isinstance(data, dict) else None
        if not isinstance(plugins, dict):
            return
        uptime_cfg = plugins.get("octoprint_uptime")
        if not isinstance(uptime_cfg, dict):
            return
        for key, default in (
            ("debug_throttle_seconds", 60),
            ("poll_interval_seconds", 5),
        ):
            if key in uptime_cfg:
                raw = uptime_cfg.get(key)
                try:
                    if raw is None:
                        raise ValueError()
                    val = int(raw)
                except (ValueError, TypeError):
                    val = default
                val = max(1, min(val, 120))
                uptime_cfg[key] = val

    def _log_settings_save_data(self, data: Dict[str, Any]) -> None:
        logger = getattr(self, "_logger", None)
        if logger:
            try:
                logger.debug("on_settings_save data: %r", data)
            except (AttributeError, TypeError, ValueError):
                pass

    def _call_base_on_settings_save(self, data: Dict[str, Any]) -> None:
        method = getattr(SettingsPluginBase, "on_settings_save", None)
        if callable(method):
            try:
                method(self, data)
            except (AttributeError, TypeError, ValueError):
                pass

    def _update_internal_state(self) -> None:
        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._debug_throttle_seconds = int(
            self._settings.get(["debug_throttle_seconds"]) or 60
        )

    def _log_settings_after_save(self, prev_navbar: Any) -> None:
        logger = getattr(self, "_logger", None)
        if not logger:
            return
        try:
            msg = (
                "UptimePlugin: settings after save: debug=%s, "
                "navbar_enabled=%s, display_format=%s, "
                "debug_throttle_seconds=%s"
            )
            logger.info(
                msg,
                self._debug_enabled,
                self._navbar_enabled,
                self._display_format,
                self._debug_throttle_seconds,
            )
        except (AttributeError, TypeError, ValueError):
            pass

        if prev_navbar is not None and prev_navbar != self._navbar_enabled:
            try:
                logger.info(
                    "UptimePlugin: navbar_enabled changed from %s to %s",
                    prev_navbar,
                    self._navbar_enabled,
                )
            except (AttributeError, TypeError, ValueError):
                pass

    def _log_debug(self, message: str) -> None:
        try:
            if not getattr(self, "_debug_enabled", False):
                return
            now = time.time()
            last_time = getattr(self, "_last_debug_time", 0)
            if (now - last_time) < self._debug_throttle_seconds:
                return
            self._last_debug_time = now
            try:
                self._logger.debug(message)
            except (AttributeError, TypeError, ValueError):
                pass
        except (AttributeError, TypeError, ValueError):
            pass

    def get_additional_systeminfo_files(self) -> List[Tuple[str, bytes]]:
        """
        Returns a list of additional system information files to be included.

        Each item in the list is a tuple containing the file name and its contents as bytes.
        By default, this method returns an empty list, indicating no additional files.

        Returns:
            List[Tuple[str, bytes]]: A list of tuples with file names and their contents.
        """
        return []

    def on_api_get(self) -> Any:
        """
        Handle GET requests to the plugin's API endpoint.

        Returns:
            Any: Flask JSON response or dict with uptime info.
        """
        if not self._check_permissions():
            return self._abort_forbidden()

        seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d = self._get_uptime_info()
        self._log_debug(_("Uptime API requested, result=%s") % (uptime_full,))

        if _flask is not None:
            navbar_enabled, display_format, poll_interval = self._get_api_settings()
            return _flask.jsonify(
                uptime=uptime_full,
                uptime_dhm=uptime_dhm,
                uptime_dh=uptime_dh,
                uptime_d=uptime_d,
                seconds=seconds,
                navbar_enabled=navbar_enabled,
                display_format=display_format,
                poll_interval_seconds=poll_interval,
            )
        return {"uptime": uptime_full}

    def _check_permissions(self) -> bool:
        try:
            if _perm is not None:
                return _perm.Permissions.SYSTEM.can()
            return True
        except (AttributeError, TypeError, ValueError):
            return True

    def _abort_forbidden(self):
        if _flask is not None:
            _flask.abort(403)
        return {"error": _("Forbidden")}

    def _get_uptime_info(self):
        try:
            getter = getattr(self, "get_uptime_seconds", None)
            seconds = getter() if callable(getter) else self._get_uptime_seconds()
            if isinstance(seconds, (int, float)):
                uptime_full = _format_uptime(seconds)
                uptime_dhm = _format_uptime_dhm(seconds)
                uptime_dh = _format_uptime_dh(seconds)
                uptime_d = _format_uptime_d(seconds)
            else:
                uptime_full = uptime_dhm = uptime_dh = uptime_d = str(seconds)
        except (AttributeError, TypeError, ValueError, KeyError):
            try:
                self._logger.exception(_("Error computing uptime"))
            except (AttributeError, TypeError, ValueError):
                pass
            uptime_full = uptime_dhm = uptime_dh = uptime_d = _("unknown")
            seconds = 0
        return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d

    def _get_api_settings(self):
        try:
            navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        except (AttributeError, TypeError, ValueError, KeyError):
            navbar_enabled = True
        try:
            display_format = str(self._settings.get(["display_format"]))
        except (AttributeError, TypeError, ValueError, KeyError):
            display_format = _("full")
        try:
            poll_interval = int(self._settings.get(["poll_interval_seconds"]) or 5)
        except (AttributeError, TypeError, ValueError, KeyError):
            poll_interval = 5
        return navbar_enabled, display_format, poll_interval
