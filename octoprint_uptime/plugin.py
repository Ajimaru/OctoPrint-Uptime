"""OctoPrint-Uptime plugin module.

Provides uptime information for OctoPrint instances,
including API, navbar, and settings integration.
"""

import gettext
import importlib
import os
import shutil
import stat
import time
from typing import IO, Any, Dict, List, cast

try:
    from ._version import VERSION
except (ImportError, ModuleNotFoundError):
    VERSION = "0.0.0"
try:
    import flask as _flask
except ImportError:
    _flask = None

try:
    import subprocess
    from subprocess import TimeoutExpired
except ImportError:
    subprocess = None
    TimeoutExpired = None

PERM = None

try:
    _ = gettext.gettext
except (ImportError, AttributeError):

    def _(message):
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

    class _SettingsPluginBase(object):  # pragma: no cover - trivial fallback
        pass

    class _SimpleApiPluginBase(object):  # pragma: no cover - trivial fallback
        pass

    class _AssetPluginBase(object):  # pragma: no cover - trivial fallback
        pass

    class _TemplatePluginBase(object):  # pragma: no cover - trivial fallback
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
                "displayVersion": VERSION,
                "type": "github_release",
                "user": "Ajimaru",
                "repo": "OctoPrint-Uptime",
                "current": VERSION,
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
        """Attempts to retrieve system uptime using several strategies."""
        strategies = [
            self._get_uptime_from_proc,
            self._get_uptime_from_psutil,
            self._get_uptime_from_uptime_cmd,
        ]
        for strategy in strategies:
            uptime = strategy()
            if uptime is not None:
                return uptime
        return 0

    def _get_uptime_from_proc(self) -> float | None:
        """Get uptime from /proc/uptime if available."""
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r", encoding="utf-8") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
        except (ValueError, TypeError, OSError):
            return None
        return None

    def _get_uptime_from_psutil(self) -> float | None:
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
        except (AttributeError, TypeError, ValueError):
            return None
        return None

    def _get_uptime_from_uptime_cmd(self) -> float | None:
        """Get uptime using the 'uptime -s' command with refactored helpers."""
        if not subprocess:
            return None

        try:
            uptime_path = self._get_valid_uptime_path()
            if not uptime_path:
                return None

            exec_path = self._get_vetted_uptime_exec()
            if not exec_path:
                return None

            return self._run_uptime_and_parse(exec_path)
        except (ValueError, OSError, TypeError, UnicodeDecodeError):
            return None

    def _get_valid_uptime_path(self) -> str | None:
        """Return a valid absolute path to the uptime binary, or None.

        This performs a best-effort, more secure validation on POSIX systems by
        attempting to open the candidate path with O_NOFOLLOW and validating the
        resulting file descriptor (regular file, executable bit set). If that
        is not available or fails, it falls back to resolving the realpath and
        performing conservative checks. The function always returns a canonical
        path (via realpath) when it decides the candidate is acceptable.
        """
        uptime_path = shutil.which("uptime")
        if not uptime_path or not os.path.isabs(uptime_path):
            return None

        rp: str | None = None

        nofollow = getattr(os, "O_NOFOLLOW", 0)
        flags = os.O_RDONLY
        if nofollow:
            flags |= nofollow

        try:
            fd = os.open(uptime_path, flags)
        except OSError:
            try:
                rp = os.path.realpath(uptime_path)
            except (OSError, ValueError):
                return None
            if os.path.basename(rp) != "uptime":
                return None
            try:
                st = os.stat(rp)
            except OSError:
                return None
        else:
            try:
                st = os.fstat(fd)
                if not stat.S_ISREG(st.st_mode):
                    return None
                if not st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    return None
                try:
                    rp = os.path.realpath(uptime_path)
                except (OSError, ValueError):
                    rp = uptime_path
            finally:
                os.close(fd)

        if not rp:
            return None
        if os.path.basename(rp) != "uptime":
            return None
        return rp

    def _get_vetted_uptime_exec(self) -> str | None:
        """Return a vetted absolute path to the uptime binary, or None."""
        candidate_paths = [
            "/usr/bin/uptime",
            "/bin/uptime",
            "/sbin/uptime",
            "/usr/sbin/uptime",
        ]
        for p in candidate_paths:
            if os.path.isabs(p) and os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return None

    def _select_devnull(self):
        """Return a valid stderr sink (DEVNULL, PIPE, or file)."""
        if subprocess is not None and hasattr(subprocess, "DEVNULL"):
            return subprocess.DEVNULL, False
        if subprocess is not None and hasattr(subprocess, "PIPE"):
            return subprocess.PIPE, False
        return open(os.devnull, "wb"), True

    def _decode_output(self, out_bytes):
        """Decode bytes to string safely."""
        try:
            return out_bytes.decode("utf-8", errors="replace").strip()
        except (AttributeError, TypeError):
            return str(out_bytes).strip()

    def _run_uptime_and_parse(self, exec_path: str) -> float | None:
        """Run the uptime command and parse the output to get uptime in seconds."""

        if not os.path.isabs(exec_path):
            raise ValueError("exec_path must be an absolute path")

        if not os.access(exec_path, os.X_OK):
            raise ValueError("exec_path is not executable")

        devnull, must_close = self._select_devnull()

        try:
            # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
            completed = subprocess.run(
                [exec_path, "-s"],
                stdout=subprocess.PIPE,
                stderr=devnull,
                check=False,
                timeout=5,
                close_fds=True,
                env={"PATH": "/usr/bin:/bin"},
            )

            if completed.returncode != 0:
                return None

            out_str = self._decode_output(completed.stdout)
            boot = time.mktime(time.strptime(out_str, "%Y-%m-%d %H:%M:%S"))
            return time.time() - boot

        except (TimeoutExpired, OSError, ValueError, UnicodeDecodeError) as e:
            logger = getattr(self, "_logger", None)
            if logger:
                try:
                    logger.error("Exception in _run_uptime_and_parse: %s", str(e))
                except (AttributeError, TypeError, ValueError):
                    pass
            return None

        finally:
            if must_close:
                cast(IO[bytes], devnull).close()

    def on_after_startup(self) -> None:
        """
        Called after the OctoPrint server has started up.

        This method can be used to perform any initialization tasks or setup required
        after the server is fully running. Override this method to add custom startup logic.
        """
        return

    def on_settings_initialized(self) -> None:
        """
        Called when OctoPrint has initialized plugin settings.

        This updates the plugin's internal state from the settings store and
        calls a base implementation if provided by OctoPrint.
        """
        try:
            # Update internal state from settings if available
            self._update_internal_state()
        except (AttributeError, TypeError, ValueError):
            pass

        # If a base class provides an on_settings_initialized hook, call it safely
        method = getattr(SettingsPluginBase, "on_settings_initialized", None)
        if callable(method):
            try:
                method(self)
            except (AttributeError, TypeError, ValueError):
                pass

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
        self._debug_throttle_seconds = int(
            self._settings.get(["debug_throttle_seconds"]) or 60
        )

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

    def _fallback_uptime_response(self):
        """
        Return system uptime info as a JSON or dict response.

        If Flask is available, returns a JSON response with uptime details and settings.
        Otherwise, returns a basic dictionary. On error, returns 'unknown' uptime.
        """
        try:
            seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d = (
                self._get_uptime_info()
            )
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
        except (AttributeError, TypeError, ValueError):
            return {"uptime": _("unknown")}

    def on_api_get(self, _request: Any = None) -> Any:
        """
        Handle GET requests to the plugin's API endpoint.
        """
        try:
            if not self._check_permissions():
                try:
                    return self._abort_forbidden()
                except (AttributeError, TypeError, ValueError):
                    return self._fallback_uptime_response()
        except (AttributeError, TypeError, ValueError):
            pass

        seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d = self._get_uptime_info()
        self._log_debug(_("Uptime API requested, result=%s") % uptime_full)

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
        """
        Checks if the current user has the necessary system permissions.

        Returns:
            bool: True if the user has system permissions or if permissions are not enforced;
                  otherwise, returns the result of the permission check. If an exception occurs
                  during the check (AttributeError, TypeError, or ValueError), defaults to True.
        """
        try:
            if PERM is not None:
                return PERM.Permissions.SYSTEM.can()
            return True
        except (AttributeError, TypeError, ValueError):
            return True

    def _abort_forbidden(self):
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

    def _get_uptime_info(self):
        """
        Retrieve uptime information and formatted strings.

        Returns:
            Tuple: (seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d)
        """
        try:
            if hasattr(self, "get_uptime_seconds") and callable(
                self.get_uptime_seconds
            ):
                seconds = self.get_uptime_seconds()
            else:
                seconds = self._get_uptime_seconds()

            if isinstance(seconds, (int, float)):
                uptime_full = format_uptime(seconds)
                uptime_dhm = format_uptime_dhm(seconds)
                uptime_dh = format_uptime_dh(seconds)
                uptime_d = format_uptime_d(seconds)
            else:
                uptime_full = uptime_dhm = uptime_dh = uptime_d = str(seconds)
            return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d
        except (AttributeError, TypeError, ValueError):
            try:
                self._logger.exception(_("Error computing uptime"))
            except (AttributeError, TypeError, ValueError):
                pass
            uptime_full = uptime_dhm = uptime_dh = uptime_d = _("unknown")
            seconds = 0
            return seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d

    def _get_api_settings(self):
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
