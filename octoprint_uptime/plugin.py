# pyright: reportGeneralTypeIssues=false
"""OctoPrint-Uptime plugin module.

Provides uptime information for OctoPrint instances,
including API, navbar, and settings integration.
"""

import gettext
import importlib
import inspect
import os
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from ._version import VERSION
except (ImportError, ModuleNotFoundError):
    VERSION = "0.0.0"
try:
    import flask as _flask
except ImportError:
    _flask = None
PERM = None

try:
    # Bind the bundled translations so gettext.lookup will find them.
    _localedir = os.path.join(os.path.dirname(__file__), "translations")
    try:
        gettext.bindtextdomain("messages", _localedir)
        gettext.textdomain("messages")
    except (OSError, RuntimeError):
        # non-fatal: fall back to default gettext behavior
        pass

    _ = gettext.gettext
except (ImportError, AttributeError):

    def _(message: str) -> str:
        return message


try:
    plugin_pkg = importlib.import_module("octoprint.plugin")
    try:
        perm_pkg = importlib.import_module("octoprint.access.permissions")
        PERM = perm_pkg
    except ModuleNotFoundError:
        PERM = None

    SettingsPluginBase = getattr(plugin_pkg, "SettingsPlugin", object)
    SimpleApiPluginBase = getattr(plugin_pkg, "SimpleApiPlugin", object)
    AssetPluginBase = getattr(plugin_pkg, "AssetPlugin", object)
    TemplatePluginBase = getattr(plugin_pkg, "TemplatePlugin", object)
except ModuleNotFoundError:
    PERM = None

    class _SettingsPluginBase:  # pragma: no cover - trivial fallback
        pass

    class _SimpleApiPluginBase:  # pragma: no cover - trivial fallback
        pass

    class _AssetPluginBase:  # pragma: no cover - trivial fallback
        pass

    class _TemplatePluginBase:  # pragma: no cover - trivial fallback
        pass

    SettingsPluginBase = _SettingsPluginBase
    SimpleApiPluginBase = _SimpleApiPluginBase
    AssetPluginBase = _AssetPluginBase
    TemplatePluginBase = _TemplatePluginBase


def format_uptime(seconds: float) -> str:
    """
    Converts a duration in seconds to a human-readable string format.

    Args:
        seconds (float): The total number of seconds to format.

    Returns:
        str: A string representing the duration in days, hours, minutes, and seconds
            (e.g., '1d 2h 3m 4s').
    """
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


def format_uptime_dhm(seconds: float) -> str:
    """
    Converts a duration in seconds to a human-readable string in days, hours, and minutes.

    Args:
        seconds (float): The total number of seconds to format.

    Returns:
        str: A formatted string representing the duration in the form
            'Xd Yh Zm' if days are present,
            or 'Yh Zm' if days are zero.
    """
    seconds = int(seconds)
    days = seconds // 86400
    rem = seconds - days * 86400
    hours = rem // 3600
    rem = rem - hours * 3600
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def format_uptime_dh(seconds: float) -> str:
    """
    Converts a duration in seconds to a human-readable string in days and hours.

    Args:
        seconds (float): The total number of seconds to format.

    Returns:
        str: A string representing the duration in the format 'Xd Yh' if days are present,
             otherwise 'Yh' for hours only.
    """
    seconds = int(seconds)
    days = seconds // 86400
    rem = seconds - days * 86400
    hours = rem // 3600
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h"


def format_uptime_d(seconds: float) -> str:
    """
    Converts a duration in seconds to a string representing the number of whole days.

    Args:
        seconds (float): The duration in seconds.

    Returns:
        str: The formatted string showing the number of days followed by 'd'.
    """
    seconds = int(seconds)
    days = seconds // 86400
    return f"{days}d"


class OctoprintUptimePlugin(
    SimpleApiPluginBase,
    AssetPluginBase,
    SettingsPluginBase,
    TemplatePluginBase,
):
    """OctoPrint plugin implementation.
    Uses lazy imports for OctoPrint/Flask integration points so the module
    can be imported in environments where OctoPrint is not installed.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the OctoPrint-Uptime plugin.

        Sets up default internal state variables for debug settings, navbar display,
        display format, and uptime tracking.

        Args:
            *args: Variable length argument list passed to parent class.
            **kwargs: Arbitrary keyword arguments passed to parent class.
        """
        super().__init__(*args, **kwargs)
        self._debug_enabled: bool = False
        self._navbar_enabled: bool = True
        self._display_format: str = "full"
        self._last_debug_time: float = 0.0
        self._last_throttle_notice: float = 0.0
        self._debug_throttle_seconds: int = 60
        self._last_uptime_source: Optional[str] = None

    def get_update_information(self) -> Dict[str, Any]:
        """Return update information for the OctoPrint-Uptime plugin.

        This method provides metadata required for OctoPrint's update mechanism.

        Returns:
            dict: Update information dictionary.
        """

        info: Dict[str, Any] = {
            "octoprint_uptime": {
                "displayName": "OctoPrint-Uptime",
                "displayVersion": VERSION,
                "type": "github_release",
                "user": "Ajimaru",
                "repo": "OctoPrint-Uptime",
                "current": VERSION,
                "pip": "https://github.com/Ajimaru/OctoPrint-Uptime/archive/{target_version}.zip",
            }
        }
        return info

    def is_api_protected(self) -> bool:
        """Indicate whether the plugin's API endpoint requires authentication.

        Returns:
            bool: True if API is protected, False otherwise.
        """
        result: bool = True
        return result

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

    def is_template_autoescaped(self) -> bool:
        """
        Determine if template autoescaping is enabled.

        Returns:
            bool: True if autoescaping is enabled for templates, otherwise False.
        """
        return True

    def _get_uptime_seconds(self) -> Tuple[Optional[float], str]:
        """Attempts to retrieve system uptime using several strategies.

        Returns a tuple of (seconds|None, source) where source is one of
        "proc", "psutil" or "none".
        """
        uptime = self._get_uptime_from_proc()
        if uptime is not None:
            self._last_uptime_source = "proc"
            return uptime, "proc"

        uptime = self._get_uptime_from_psutil()
        if uptime is not None:
            self._last_uptime_source = "psutil"
            return uptime, "psutil"

        self._last_uptime_source = "none"
        return None, "none"

    def _get_uptime_from_proc(self) -> Optional[float]:
        """Get uptime from /proc/uptime if available."""
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", encoding="utf-8") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
        except (ValueError, TypeError, OSError):
            pass
        return None

    def _get_uptime_from_psutil(self) -> Optional[float]:
        """Get uptime using psutil if available."""
        try:
            _ps = importlib.import_module("psutil")
        except ImportError:
            return None
        try:
            boot = _ps.boot_time()
            uptime = time.time() - boot
            if isinstance(uptime, (int, float)) and 0 <= uptime < 10 * 365 * 24 * 3600:
                return uptime
        except (AttributeError, TypeError, ValueError, OSError):
            return None
        return None

    def _get_octoprint_uptime(self) -> Optional[float]:
        """Get OctoPrint process uptime using psutil if available."""
        try:
            _ps = importlib.import_module("psutil")
        except ImportError:
            return None
        try:
            # Get current process
            current_process = _ps.Process(os.getpid())
            # Get process creation time
            create_time = current_process.create_time()
            uptime = time.time() - create_time
            if isinstance(uptime, (int, float)) and 0 <= uptime < 10 * 365 * 24 * 3600:
                return uptime
        except (AttributeError, TypeError, ValueError, OSError):
            return None
        return None

    def on_settings_initialized(self) -> None:
        """
        Called when OctoPrint has initialized plugin settings.

        This updates the plugin's internal state from the settings store and
        calls a base implementation if provided by OctoPrint.
        """

        self._safe_update_internal_state()

        hook = getattr(super(), "on_settings_initialized", None)
        if not callable(hook):
            hook = getattr(SettingsPluginBase, "on_settings_initialized", None)

        if callable(hook):
            self._invoke_settings_hook(hook)

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

    def _safe_update_internal_state(self) -> None:
        """Helper that updates internal state and logs expected failures."""
        logger = getattr(self, "_logger", None)
        try:
            self._update_internal_state()
        except (AttributeError, KeyError, ValueError) as e:
            if logger:
                logger.warning(
                    "on_settings_initialized: failed to update internal state: %s",
                    e,
                )

    def _get_hook_positional_param_count(self, hook: Any) -> Optional[int]:
        """Return the number of positional params a callable accepts or None on error.

        Uses `inspect.signature` and logs a warning on failure.
        """
        logger = getattr(self, "_logger", None)
        try:
            sig = inspect.signature(hook)
            params = [
                p
                for p in sig.parameters.values()
                if p.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            ]
            return len(params)
        except (ValueError, TypeError, AttributeError) as e:
            if logger:
                logger.info(
                    "_get_hook_positional_param_count: unable to inspect signature for %r: %s",
                    hook,
                    e,
                )
            return None

    def _safe_invoke_hook(self, hook: Any, param_count: int) -> None:
        """Invoke a hook with either zero or one positional parameter and log failures.

        `param_count` should be 0 or 1; any exception raised by the hook is logged
        but not propagated.
        """
        logger = getattr(self, "_logger", None)
        try:
            if param_count == 0:
                hook()
            else:
                hook(self)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            if logger:
                logger.exception("_safe_invoke_hook: %r raised", hook)

    def _invoke_settings_hook(self, hook: Any) -> None:
        """Invoke a settings hook using signature inspection and log call errors.

        Delegates signature inspection and the actual call to small helpers to
        reduce complexity and make failures easier to log/reason about.
        """
        logger = getattr(self, "_logger", None)

        param_count = self._get_hook_positional_param_count(hook)
        if param_count is None:
            return
        if param_count not in (0, 1):
            if logger:
                logger.warning(
                    "_invoke_settings_hook: unexpected parameter count %s for %r; skipping",
                    param_count,
                    hook,
                )
            return

        self._safe_invoke_hook(hook, param_count)

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
        """
        Logs the data passed to the settings save event for debugging purposes.

        Args:
            data (Dict[str, Any]): The data being saved to the settings.

        Notes:
            If the logger is not available or an error occurs during logging,
            the exception is silently ignored.
        """
        logger = getattr(self, "_logger", None)
        if logger:
            try:
                logger.debug("on_settings_save data: %r", data)
            except (AttributeError, TypeError, ValueError):
                pass

    def _call_base_on_settings_save(self, data: Dict[str, Any]) -> None:
        """
        Calls the base class's `on_settings_save` method with the provided data if it exists
        and is callable.

        Args:
            data (Dict[str, Any]): The settings data to be saved.

        Notes:
            - Silently ignores AttributeError, TypeError, and ValueError exceptions that may
              occur during the call.
            - This is typically used to ensure that any base class logic for saving settings
              is executed.
        """
        method = getattr(SettingsPluginBase, "on_settings_save", None)
        if callable(method):
            try:
                method(self, data)
            except (AttributeError, TypeError, ValueError):
                pass

    def get_settings_defaults(self) -> Dict[str, Any]:
        """Return default settings for the plugin.

        OctoPrint populates `settings.plugins.<identifier>` from this mapping so the
        frontend can safely bind to `settings.plugins.octoprint_uptime.*`.
        """
        return {
            "debug": False,
            "navbar_enabled": True,
            "show_octoprint_uptime": True,
            "display_format": "full",
            "debug_throttle_seconds": 60,
            "poll_interval_seconds": 5,
        }

    def _update_internal_state(self) -> None:
        """
        Updates the plugin's internal state variables based on the current settings.

        This method retrieves the latest configuration values from the settings object and updates
        the following internal attributes:
        - _debug_enabled: Whether debug mode is enabled.
        - _navbar_enabled: Whether the navbar display is enabled.
        - _display_format: The format string for displaying uptime.
        - _debug_throttle_seconds: The throttle interval (in seconds) for debug messages.

        Returns:
            None
        """
        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._debug_throttle_seconds = int(self._settings.get(["debug_throttle_seconds"]) or 60)

    def _log_settings_after_save(self, prev_navbar: Any) -> None:
        """
        Logs the current plugin settings after they have been saved.

        This method logs the values of debug mode, navbar visibility, display format,
        and debug throttle seconds. If the navbar setting has changed compared to its
        previous value, it logs the change as well.

        Args:
            prev_navbar (Any): The previous value of the navbar_enabled setting.

        Returns:
            None
        """
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
        """
        Logs a debug message if debugging is enabled and throttling conditions are met.

        This method checks if debugging is enabled via the `_debug_enabled` attribute.
        If enabled, it ensures that debug messages are not logged more frequently than
        the interval specified by `_debug_throttle_seconds`. The timestamp of the last
        logged debug message is tracked using `_last_debug_time`. Any exceptions related
        to missing or invalid attributes, or logging errors, are silently ignored.

        Args:
            message (str): The debug message to log.

        Returns:
            None
        """
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

    def _fallback_uptime_response(self) -> Any:
        """
        Return system uptime info as a JSON or dict response.

        If Flask is available, returns a JSON response with uptime details and settings.
        Otherwise, returns a basic dictionary. On error, returns 'unknown' uptime.
        """
        logger = getattr(self, "_logger", None)
        try:
            seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d = self._get_uptime_info()
            uptime_available = (
                isinstance(seconds, (int, float)) and seconds >= 0 and uptime_full != _("unknown")
            )
            if _flask is not None:
                navbar_enabled, display_format, poll_interval = self._get_api_settings()
                resp = {
                    "uptime": uptime_full,
                    "uptime_dhm": uptime_dhm,
                    "uptime_dh": uptime_dh,
                    "uptime_d": uptime_d,
                    "seconds": seconds,
                    "navbar_enabled": navbar_enabled,
                    "display_format": display_format,
                    "poll_interval_seconds": poll_interval,
                    "uptime_available": uptime_available,
                }
                if not uptime_available:
                    resp["uptime_note"] = _("Uptime could not be determined on this system.")
                try:
                    json_resp = _flask.jsonify(**resp)
                except (TypeError, ValueError, RuntimeError):
                    if logger:
                        logger.exception(
                            "_build_flask_uptime_response: flask.jsonify failed, "
                            "falling back to dict"
                        )
                    return resp
                else:
                    return json_resp

            else:
                resp = {"uptime": uptime_full, "uptime_available": uptime_available}
                if not uptime_available:
                    resp["uptime_note"] = _("Uptime could not be determined on this system.")
                return resp
        except (AttributeError, TypeError, ValueError):
            if logger:
                try:
                    logger.exception(
                        "_fallback_uptime_response: unexpected error while building response"
                    )
                except (AttributeError, TypeError, ValueError):
                    pass
            return {"uptime": _("unknown"), "uptime_available": False}

    def on_api_get(self, _request: Any = None) -> Any:
        """
        Handle GET requests to the plugin's API endpoint.
        """
        permission_result = self._handle_permission_check()
        if permission_result is not None:
            return permission_result

        seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d = self._get_uptime_info()
        (
            octoprint_seconds,
            octoprint_uptime_full,
            octoprint_uptime_dhm,
            octoprint_uptime_dh,
            octoprint_uptime_d,
        ) = self._get_octoprint_uptime_info()
        self._log_debug(_("Uptime API requested, result=%s") % uptime_full)

        if _flask is not None:
            navbar_enabled, display_format, poll_interval = self._get_api_settings()
            return _flask.jsonify(
                uptime=uptime_full,
                uptime_dhm=uptime_dhm,
                uptime_dh=uptime_dh,
                uptime_d=uptime_d,
                seconds=seconds,
                octoprint_uptime=octoprint_uptime_full,
                octoprint_uptime_dhm=octoprint_uptime_dhm,
                octoprint_uptime_dh=octoprint_uptime_dh,
                octoprint_uptime_d=octoprint_uptime_d,
                octoprint_seconds=octoprint_seconds,
                navbar_enabled=navbar_enabled,
                display_format=display_format,
                poll_interval_seconds=poll_interval,
            )

        return {"uptime": uptime_full, "octoprint_uptime": octoprint_uptime_full}

    def _handle_permission_check(self) -> Optional[Any]:
        """
        Handles permission checking and error handling for API GET requests.

        Returns:
            The forbidden response or fallback response if permission is denied or an error occurs,
            otherwise None if permission is granted.
        """
        try:
            if not self._check_permissions():
                try:
                    return self._abort_forbidden()
                except (AttributeError, TypeError, ValueError, RuntimeError, OSError):
                    return {"error": _("Forbidden"), "uptime_available": False}
        except (AttributeError, TypeError, ValueError):
            if hasattr(self, "_logger") and self._logger is not None:
                self._logger.exception("on_api_get: unexpected error while checking permissions")
            try:
                return self._abort_forbidden()
            except (AttributeError, TypeError, ValueError, RuntimeError, OSError):
                return {"error": _("Forbidden"), "uptime_available": False}
        return None

    def _check_permissions(self) -> bool:
        """
        Checks if the current user has the necessary system permissions.

        Returns:
            bool: True if the user has system permissions or if permissions are not enforced;
                  otherwise, returns the result of the permission check. If an exception occurs
                  during the check (AttributeError, TypeError, or ValueError), defaults to True.
        """
        # Intentionally permissive placeholder: permission enforcement is not implemented
        # in this plugin. Always allow access for now; replace with real checks when
        # permission enforcement is required.
        return True

    def _abort_forbidden(self) -> Dict[str, str]:
        """
        Handles forbidden access attempts by aborting the request with a 403 status code if
        Flask is available, and returns a JSON error message indicating the action is
        forbidden.

        Returns:
            dict: A dictionary containing an error message with the key "error" and value
            "Forbidden".
        """
        if _flask is not None:
            _flask.abort(403)
        return {"error": _("Forbidden")}

    def _get_uptime_info(self) -> Tuple[Optional[float], str, str, str, str]:
        """
        Retrieve uptime information and formatted strings.

        Returns:
            Tuple: (seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d)
        """
        try:
            if hasattr(self, "get_uptime_seconds") and callable(self.get_uptime_seconds):
                res = self.get_uptime_seconds()
                if isinstance(res, tuple) and len(res) == 2:
                    seconds, _source = res
                    self._last_uptime_source = _source
                else:
                    seconds = res
                    self._last_uptime_source = "custom"
            else:
                seconds, _source = self._get_uptime_seconds()

            if isinstance(seconds, (int, float)):
                seconds = float(seconds)
            else:
                seconds = None

            if seconds is not None:
                uptime_full = format_uptime(seconds)
                uptime_dhm = format_uptime_dhm(seconds)
                uptime_dh = format_uptime_dh(seconds)
                uptime_d = format_uptime_d(seconds)
            else:
                uptime_full = uptime_dhm = uptime_dh = uptime_d = _("unknown")
            return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d
        except (AttributeError, TypeError, ValueError):
            try:
                self._logger.exception(_("Error computing uptime"))
            except (AttributeError, TypeError, ValueError):
                pass
            uptime_full = uptime_dhm = uptime_dh = uptime_d = _("unknown")
            seconds = None
            return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d

    def _get_octoprint_uptime_info(self) -> Tuple[Optional[float], str, str, str, str]:
        """
        Retrieve OctoPrint process uptime information and formatted strings.

        Returns:
            Tuple: (seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d)
        """
        try:
            seconds = self._get_octoprint_uptime()

            if isinstance(seconds, (int, float)):
                seconds = float(seconds)
            else:
                seconds = None

            if seconds is not None:
                uptime_full = format_uptime(seconds)
                uptime_dhm = format_uptime_dhm(seconds)
                uptime_dh = format_uptime_dh(seconds)
                uptime_d = format_uptime_d(seconds)
            else:
                uptime_full = uptime_dhm = uptime_dh = uptime_d = _("unknown")
            return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d
        except (AttributeError, TypeError, ValueError):
            try:
                self._logger.exception(_("Error computing OctoPrint uptime"))
            except (AttributeError, TypeError, ValueError):
                pass
            uptime_full = uptime_dhm = uptime_dh = uptime_d = _("unknown")
            seconds = None
            return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d

    def _get_api_settings(self) -> Tuple[bool, str, int]:
        """
        Retrieves and returns the plugin's API settings with appropriate fallbacks.

        Attempts to fetch the following settings from the plugin's configuration:
        - navbar_enabled (bool): Whether the navbar is enabled.
            Defaults to True if not set or invalid.
        - display_format (str): The format to display uptime.
            Defaults to "full" if not set or invalid.
        - poll_interval (int): The polling interval in seconds.
            Defaults to 5 if not set or invalid.

        Returns:
            tuple: (navbar_enabled, display_format, poll_interval)
        """
        logger = getattr(self, "_logger", None)

        try:
            raw_nav = self._settings.get(["navbar_enabled"])
            if raw_nav is None:
                navbar_enabled = True
                if logger:
                    logger.debug("_get_api_settings: navbar_enabled missing, defaulting to True")
            else:
                navbar_enabled = bool(raw_nav)
        except (AttributeError, TypeError, ValueError) as e:
            navbar_enabled = True
            if logger:
                logger.exception(
                    "_get_api_settings: failed to read navbar_enabled, defaulting to True: %s",
                    e,
                )

        try:
            raw_fmt = self._settings.get(["display_format"])
            if raw_fmt is None:
                display_format = _("full")
                if logger:
                    logger.debug("_get_api_settings: display_format missing, defaulting to 'full'")
            else:
                display_format = str(raw_fmt)
        except (AttributeError, TypeError, ValueError) as e:
            display_format = _("full")
            if logger:
                logger.exception(
                    "_get_api_settings: failed to read display_format, defaulting to 'full': %s",
                    e,
                )

        try:
            raw_poll = self._settings.get(["poll_interval_seconds"])
            if raw_poll is None or raw_poll == "":
                poll_interval = 5
                if logger:
                    logger.debug(
                        "_get_api_settings: poll_interval_seconds missing, defaulting to 5"
                    )
            else:
                try:
                    poll_interval = int(raw_poll)
                except (TypeError, ValueError):
                    poll_interval = 5
                    if logger:
                        logger.debug(
                            "_get_api_settings: poll_interval_seconds invalid (%r), "
                            "defaulting to 5",
                            raw_poll,
                        )

            if poll_interval < 1:
                if logger:
                    logger.debug(
                        "_get_api_settings: poll_interval_seconds %s < 1, clamping to 1",
                        poll_interval,
                    )
                poll_interval = 1
            elif poll_interval > 120:
                if logger:
                    logger.debug(
                        "_get_api_settings: poll_interval_seconds %s > 120, clamping to 120",
                        poll_interval,
                    )
                poll_interval = 120
        except (AttributeError, TypeError, ValueError) as e:
            poll_interval = 5
            if logger:
                logger.exception(
                    "_get_api_settings: failed to read poll_interval_seconds, defaulting to 5: %s",
                    e,
                )

        return navbar_enabled, display_format, poll_interval
