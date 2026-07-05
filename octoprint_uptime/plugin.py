# pyright: reportGeneralTypeIssues=false
"""OctoPrint-Uptime plugin module.

Provides system and OctoPrint process uptime for OctoPrint instances,
including API, navbar, and settings integration.

OctoPrint and Flask are imported defensively so the module can be imported,
packaged, and unit-tested in environments where neither is installed.
"""

import gettext
import importlib
import inspect
import os
import time
from typing import Any, Optional

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
        PERM = importlib.import_module("octoprint.access.permissions")
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


_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400

# Sanity ceiling for uptime values: anything above ~10 years is treated as a
# clock artifact rather than a real uptime.
_MAX_UPTIME_SECONDS = 10 * 365 * _SECONDS_PER_DAY

# (default, minimum, maximum) for the integer settings that are sanitized on
# save and clamped when read back for the API.
_INT_SETTING_BOUNDS = {
    "debug_throttle_seconds": (60, 1, 120),
    "poll_interval_seconds": (5, 1, 120),
    "compact_toggle_interval_seconds": (5, 5, 60),
}


def _split_uptime(seconds: float) -> tuple[int, int, int, int]:
    """Split a duration in seconds into whole days, hours, minutes, seconds."""
    days, rem = divmod(int(seconds), _SECONDS_PER_DAY)
    hours, rem = divmod(rem, _SECONDS_PER_HOUR)
    minutes, secs = divmod(rem, _SECONDS_PER_MINUTE)
    return days, hours, minutes, secs


def format_uptime(seconds: float) -> str:
    """Format a duration as days, hours, minutes, and seconds.

    Args:
        seconds: The total number of seconds to format.

    Returns:
        The duration as e.g. ``'1d 2h 3m 4s'``. Leading zero units are
        omitted, so ``61`` becomes ``'1m 1s'``.
    """
    days, hours, minutes, secs = _split_uptime(seconds)
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
    """Format a duration as days, hours, and minutes.

    Args:
        seconds: The total number of seconds to format.

    Returns:
        ``'Xd Yh Zm'`` when days are present, otherwise ``'Yh Zm'``.
    """
    days, hours, minutes, _secs = _split_uptime(seconds)
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def format_uptime_dh(seconds: float) -> str:
    """Format a duration as days and hours.

    Args:
        seconds: The total number of seconds to format.

    Returns:
        ``'Xd Yh'`` when days are present, otherwise ``'Yh'``.
    """
    days, hours, _minutes, _secs = _split_uptime(seconds)
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h"


def format_uptime_d(seconds: float) -> str:
    """Format a duration as whole days.

    Args:
        seconds: The total number of seconds to format.

    Returns:
        The number of whole days followed by ``'d'``, e.g. ``'2d'``.
    """
    days, _hours, _minutes, _secs = _split_uptime(seconds)
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
        """Initialize internal state for debug, display format, and tracking.

        Args:
            *args: Positional arguments passed to the parent class.
            **kwargs: Keyword arguments passed to the parent class.
        """
        super().__init__(*args, **kwargs)
        self._debug_enabled: bool = False
        self._display_format: str = "full"
        self._last_debug_time: float = 0.0
        self._debug_throttle_seconds: int = 60
        self._last_uptime_source: Optional[str] = None

    def get_update_information(self) -> dict[str, Any]:
        """Return metadata for OctoPrint's software update mechanism.

        Returns:
            Update information dictionary keyed by plugin identifier.
        """
        return {
            "octoprint_uptime": {
                "displayName": "OctoPrint-Uptime",
                "displayVersion": VERSION,
                "type": "github_release",
                "user": "Ajimaru",
                "repo": "OctoPrint-Uptime",
                "current": VERSION,
                "pip": (
                    "https://github.com/Ajimaru/"
                    "OctoPrint-Uptime/archive/{target_version}.zip"
                ),
            }
        }

    def is_api_protected(self) -> bool:
        """Indicate that the plugin's API endpoint requires authentication.

        Returns:
            Always True; OctoPrint enforces authentication for the endpoint.
        """
        return True

    def get_assets(self) -> dict[str, list[str]]:
        """Return the plugin's static asset files.

        Returns:
            Dictionary mapping asset types to file lists.
        """
        return {"js": ["js/uptime.js"]}

    def get_template_configs(self) -> list[dict[str, Any]]:
        """Return template configurations for the navbar and settings panes.

        Returns:
            A list of template configuration dictionaries.
        """
        return [
            {
                "type": "navbar",
                "name": _("Uptime"),
                "template": "navbar.jinja2",
                "custom_bindings": True,
                # Use OctoPrint's default container id by omitting ``div``.
                # The plugin identifier is ``octoprint_uptime`` (see the
                # entry point), so the default navbar <li> id becomes
                # ``navbar_plugin_octoprint_uptime`` -- the JS selectors must
                # match that exact id. A custom div id breaks the core navbar
                # reordering feature: it persists order in
                # ``appearance.components.order.navbar`` keyed by
                # ``plugin_<identifier>`` and looks the element up by the
                # default id, so a non-standard id makes the item snap back to
                # its default position on reload. OctoPrint already wraps the
                # template in the navbar <li>, so the template must not add its
                # own.
            },
            {
                "type": "settings",
                "name": _("Uptime"),
                "template": "settings.jinja2",
                "custom_bindings": False,
            },
        ]

    def is_template_autoescaped(self) -> bool:
        """Indicate that the plugin's templates are autoescaped.

        Returns:
            Always True.
        """
        return True

    def _get_uptime_seconds(self) -> tuple[Optional[float], str]:
        """Retrieve system uptime, trying /proc first and psutil second.

        Returns:
            Tuple ``(seconds, source)`` where ``source`` is one of ``"proc"``,
            ``"psutil"`` or ``"none"``; ``seconds`` is None when unavailable.
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
        """Get system uptime from /proc/uptime if available."""
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", encoding="utf-8") as f:
                    return float(f.readline().split()[0])
        except (ValueError, TypeError, OSError, IndexError):
            pass
        return None

    def _get_uptime_from_psutil(self) -> Optional[float]:
        """Get system uptime from psutil's boot time if psutil is available."""
        try:
            _ps = importlib.import_module("psutil")
        except ImportError:
            return None
        try:
            uptime = time.time() - _ps.boot_time()
        except (AttributeError, TypeError, ValueError, OSError):
            return None
        if 0 <= uptime < _MAX_UPTIME_SECONDS:
            return uptime
        return None

    def _get_octoprint_uptime_from_proc(self) -> Optional[float]:
        """Get process uptime from /proc on Linux in a clock-jump-safe way."""
        try:
            if not (
                os.path.exists("/proc/uptime") and os.path.exists("/proc/self/stat")
            ):
                return None

            with open("/proc/uptime", encoding="utf-8") as f_uptime:
                system_uptime = float(f_uptime.readline().split()[0])

            with open("/proc/self/stat", encoding="utf-8") as f_stat:
                stat_line = f_stat.readline().strip()

            # /proc/self/stat contains "pid (comm) ..." where comm can include
            # spaces, so split only after the closing parenthesis. Field 22
            # (starttime, in clock ticks since boot) is then at index 19.
            rparen = stat_line.rfind(")")
            if rparen == -1:
                return None
            stat_fields = stat_line[rparen + 2 :].split()
            if len(stat_fields) <= 19:
                return None

            start_ticks = float(stat_fields[19])
            clk_tck = float(os.sysconf("SC_CLK_TCK"))
            if clk_tck <= 0:
                return None

            process_uptime = system_uptime - (start_ticks / clk_tck)
            if 0 <= process_uptime < _MAX_UPTIME_SECONDS:
                return process_uptime
        except (ValueError, TypeError, OSError):
            return None
        return None

    def _get_octoprint_uptime(self) -> Optional[float]:
        """Get OctoPrint process uptime, preferring /proc and then psutil."""
        proc_uptime = self._get_octoprint_uptime_from_proc()
        if proc_uptime is not None:
            return proc_uptime

        try:
            _ps = importlib.import_module("psutil")
        except ImportError:
            return None

        handled = (AttributeError, TypeError, ValueError, OSError)
        psutil_error = getattr(_ps, "Error", None)
        if isinstance(psutil_error, type) and issubclass(psutil_error, BaseException):
            handled += (psutil_error,)

        try:
            create_time = _ps.Process(os.getpid()).create_time()
            uptime = time.time() - create_time
        except handled:
            return None
        if 0 <= uptime < _MAX_UPTIME_SECONDS:
            return uptime
        return None

    def on_settings_initialized(self) -> None:
        """Update internal state once OctoPrint has initialized settings.

        Also calls a base implementation if OctoPrint provides one.
        """
        self._safe_update_internal_state()

        hook = getattr(super(), "on_settings_initialized", None)
        if not callable(hook):
            hook = getattr(SettingsPluginBase, "on_settings_initialized", None)

        if callable(hook):
            self._invoke_settings_hook(hook)

    def on_settings_save(self, data: dict[str, Any]) -> None:
        """Sanitize, persist, and apply the plugin settings.

        Args:
            data: Settings data to save.
        """
        self._validate_and_sanitize_settings(data)
        self._log_settings_save_data(data)
        self._call_base_on_settings_save(data)
        self._update_internal_state()
        self._log_settings_after_save()

    def _safe_update_internal_state(self) -> None:
        """Update internal state, logging expected failures instead of raising."""
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
        """Return the number of positional params a callable accepts.

        Args:
            hook: The callable to inspect.

        Returns:
            The positional parameter count, or None when the signature cannot
            be inspected (logged as info).
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
                    "_get_hook_positional_param_count: "
                    "unable to inspect signature for %r: %s",
                    hook,
                    e,
                )
            return None

    def _safe_invoke_hook(self, hook: Any, param_count: int) -> None:
        """Invoke a hook with zero or one positional parameter, logging failures.

        Args:
            hook: The callable to invoke.
            param_count: 0 or 1; any exception raised by the hook is logged
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
        """Invoke a settings hook using signature inspection.

        Skips the call (with a warning) when the hook expects an unexpected
        number of positional parameters or its signature cannot be inspected.

        Args:
            hook: The callable to invoke.
        """
        logger = getattr(self, "_logger", None)

        param_count = self._get_hook_positional_param_count(hook)
        if param_count is None:
            return
        if param_count not in (0, 1):
            if logger:
                logger.warning(
                    "_invoke_settings_hook: unexpected parameter count "
                    "%s for %r; skipping",
                    param_count,
                    hook,
                )
            return

        self._safe_invoke_hook(hook, param_count)

    def _validate_and_sanitize_settings(self, data: dict[str, Any]) -> None:
        """Coerce and clamp integer settings in the provided save payload.

        Missing or non-integer values are replaced with their defaults, valid
        values are clamped to the allowed range (see ``_INT_SETTING_BOUNDS``).

        Args:
            data: The settings payload passed to ``on_settings_save``.
        """
        plugins = data.get("plugins") if isinstance(data, dict) else None
        if not isinstance(plugins, dict):
            return
        uptime_cfg = plugins.get("octoprint_uptime")
        if not isinstance(uptime_cfg, dict):
            return
        for key, (default, lo, hi) in _INT_SETTING_BOUNDS.items():
            if key not in uptime_cfg:
                continue
            raw = uptime_cfg.get(key)
            try:
                val = default if raw is None else int(raw)
            except (ValueError, TypeError):
                val = default
            uptime_cfg[key] = max(lo, min(val, hi))

    def _log_settings_save_data(self, data: dict[str, Any]) -> None:
        """Log the payload passed to the settings save event for debugging.

        Args:
            data: The data being saved to the settings.
        """
        logger = getattr(self, "_logger", None)
        if logger:
            try:
                logger.debug("on_settings_save data: %r", data)
            except (AttributeError, TypeError, ValueError):
                pass

    def _call_base_on_settings_save(self, data: dict[str, Any]) -> None:
        """Call the base class ``on_settings_save``, if available.

        Args:
            data: The settings data to be saved.
        """
        method = getattr(SettingsPluginBase, "on_settings_save", None)
        if callable(method):
            try:
                method(self, data)
            except (AttributeError, TypeError, ValueError):
                pass

    def get_settings_defaults(self) -> dict[str, Any]:
        """Return default settings for the plugin.

        OctoPrint populates ``settings.plugins.<identifier>`` from this mapping
        so the frontend can safely bind to
        ``settings.plugins.octoprint_uptime.*``.

        Returns:
            Mapping of setting names to default values.
        """
        return {
            "debug": False,
            "show_system_uptime": True,
            "show_octoprint_uptime": True,
            "compact_display": False,
            "compact_toggle_interval_seconds": 5,
            "display_format": "full",
            "debug_throttle_seconds": 60,
            "poll_interval_seconds": 5,
        }

    def _update_internal_state(self) -> None:
        """Refresh cached debug, display format, and throttle values."""
        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._debug_throttle_seconds = int(
            self._settings.get(["debug_throttle_seconds"]) or 60
        )

    def _log_settings_after_save(self) -> None:
        """Log the effective settings after they have been saved."""
        logger = getattr(self, "_logger", None)
        if not logger:
            return
        try:
            logger.info(
                "UptimePlugin: settings after save: debug=%s, "
                "display_format=%s, "
                "debug_throttle_seconds=%s",
                self._debug_enabled,
                self._display_format,
                self._debug_throttle_seconds,
            )
        except (AttributeError, TypeError, ValueError):
            pass

    def _log_debug(self, message: str) -> None:
        """Log a debug message when enabled, throttled to avoid log spam.

        Messages are dropped while ``_debug_throttle_seconds`` has not elapsed
        since the last logged message. Logging errors are silently ignored.

        Args:
            message: The debug message to log.
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
        """Build a system-uptime-only response as a JSON or dict payload.

        Defensive fallback used when the full API response cannot be built.
        Returns a Flask JSON response when Flask is available, a plain dict
        otherwise; on error the uptime is reported as unknown.
        """
        logger = getattr(self, "_logger", None)
        try:
            seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d = (
                self._get_uptime_info()
            )
            uptime_available = (
                isinstance(seconds, (int, float))
                and seconds >= 0
                and uptime_full != _("unknown")
            )
            if _flask is None:
                resp = {"uptime": uptime_full, "uptime_available": uptime_available}
                if not uptime_available:
                    resp["uptime_note"] = _(
                        "Uptime could not be determined on this system."
                    )
                return resp

            display_format, poll_interval = self._get_api_settings()
            resp = {
                "uptime": uptime_full,
                "uptime_dhm": uptime_dhm,
                "uptime_dh": uptime_dh,
                "uptime_d": uptime_d,
                "seconds": seconds,
                "display_format": display_format,
                "poll_interval_seconds": poll_interval,
                "uptime_available": uptime_available,
            }
            if not uptime_available:
                resp["uptime_note"] = _(
                    "Uptime could not be determined on this system."
                )
            try:
                return _flask.jsonify(**resp)
            except (TypeError, ValueError, RuntimeError):
                if logger:
                    logger.exception(
                        "_fallback_uptime_response: flask.jsonify failed, "
                        "falling back to dict"
                    )
                return resp
        except (AttributeError, TypeError, ValueError):
            if logger:
                try:
                    logger.exception(
                        "_fallback_uptime_response: unexpected error while "
                        "building response"
                    )
                except (AttributeError, TypeError, ValueError):
                    pass
            return {"uptime": _("unknown"), "uptime_available": False}

    def on_api_get(self, _request: Any = None) -> Any:
        """Handle GET requests to the plugin's API endpoint.

        Args:
            _request: The incoming request (unused).

        Returns:
            A Flask JSON response with all uptime variants when Flask is
            available, a reduced plain dict otherwise, or an error response
            when the permission check fails.
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
            display_format, poll_interval = self._get_api_settings()
            # The frontend (navbar widget and settings note) keys off
            # ``uptime_available`` to show its "Unavailable" fallback state.
            uptime_available = (
                isinstance(seconds, (int, float))
                and seconds >= 0
                and uptime_full != _("unknown")
            )
            payload: dict[str, Any] = {
                "uptime": uptime_full,
                "uptime_dhm": uptime_dhm,
                "uptime_dh": uptime_dh,
                "uptime_d": uptime_d,
                "seconds": seconds,
                "octoprint_uptime": octoprint_uptime_full,
                "octoprint_uptime_dhm": octoprint_uptime_dhm,
                "octoprint_uptime_dh": octoprint_uptime_dh,
                "octoprint_uptime_d": octoprint_uptime_d,
                "octoprint_seconds": octoprint_seconds,
                "display_format": display_format,
                "poll_interval_seconds": poll_interval,
                "uptime_available": uptime_available,
            }
            if not uptime_available:
                payload["uptime_note"] = _(
                    "Uptime could not be determined on this system."
                )
            return _flask.jsonify(**payload)

        return {"uptime": uptime_full, "octoprint_uptime": octoprint_uptime_full}

    def _handle_permission_check(self) -> Optional[Any]:
        """Check permissions for API GET requests, handling errors.

        Returns:
            A forbidden/fallback response when permission is denied or the
            check errors out, otherwise None when permission is granted.
        """
        try:
            if not self._check_permissions():
                try:
                    return self._abort_forbidden()
                except (AttributeError, TypeError, ValueError, RuntimeError, OSError):
                    return {"error": _("Forbidden"), "uptime_available": False}
        except (AttributeError, TypeError, ValueError):
            if getattr(self, "_logger", None) is not None:
                self._logger.exception(
                    "on_api_get: unexpected error while checking permissions"
                )
            try:
                return self._abort_forbidden()
            except (AttributeError, TypeError, ValueError, RuntimeError, OSError):
                return {"error": _("Forbidden"), "uptime_available": False}
        return None

    def _check_permissions(self) -> bool:
        """Check whether the current user may query the uptime API.

        Returns:
            Always True for now: fine-grained permission enforcement is not
            implemented; OctoPrint's API authentication already gates access.
            Replace with real checks when needed.
        """
        return True

    def _abort_forbidden(self) -> dict[str, str]:
        """Abort with HTTP 403 when Flask is available.

        Returns:
            An error dict when Flask is unavailable (otherwise Flask's abort
            raises before the return).
        """
        if _flask is not None:
            _flask.abort(403)
        return {"error": _("Forbidden")}

    def _get_uptime_info(self) -> tuple[Optional[float], str, str, str, str]:
        """Retrieve system uptime and its formatted display strings.

        Honors a ``get_uptime_seconds`` attribute when one has been injected
        (e.g. by tests or subclasses), otherwise uses the built-in sources.

        Returns:
            Tuple ``(seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d)``.
        """
        try:
            if hasattr(self, "get_uptime_seconds") and callable(
                self.get_uptime_seconds
            ):
                res = self.get_uptime_seconds()
                if isinstance(res, tuple) and len(res) == 2:
                    seconds, _source = res
                    self._last_uptime_source = _source
                else:
                    seconds = res
                    self._last_uptime_source = "custom"
            else:
                seconds, _source = self._get_uptime_seconds()
            uptime_seconds: Optional[float] = (
                seconds if isinstance(seconds, (int, float, type(None))) else None
            )
            return self._format_uptime_tuple(uptime_seconds)
        except (AttributeError, TypeError, ValueError):
            try:
                self._logger.exception(_("Error computing uptime"))
            except (AttributeError, TypeError, ValueError):
                pass
            return self._format_uptime_tuple(None)

    def _format_uptime_tuple(
        self, seconds: Optional[float]
    ) -> tuple[Optional[float], str, str, str, str]:
        """Normalize and format an uptime value into display strings.

        Args:
            seconds: The uptime in seconds, or None/invalid when unknown.

        Returns:
            Tuple ``(seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d)``;
            all strings are the localized "unknown" when seconds is invalid.
        """
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

    def _get_octoprint_uptime_info(self) -> tuple[Optional[float], str, str, str, str]:
        """Retrieve OctoPrint process uptime and its formatted display strings.

        Returns:
            Tuple ``(seconds, uptime_full, uptime_dhm, uptime_dh, uptime_d)``.
        """
        try:
            seconds = self._get_octoprint_uptime()
            return self._format_uptime_tuple(seconds)
        except (AttributeError, TypeError, ValueError):
            try:
                self._logger.exception(_("Error computing OctoPrint uptime"))
            except (AttributeError, TypeError, ValueError):
                pass
            return self._format_uptime_tuple(None)

    def _get_api_settings(self) -> tuple[str, int]:
        """Read the display format and poll interval for API responses.

        Returns:
            Tuple ``(display_format, poll_interval_seconds)``.
            ``display_format`` falls back to ``"full"`` and the poll interval
            is defaulted and clamped to its allowed range when missing or
            invalid.
        """
        logger = getattr(self, "_logger", None)

        display_format = "full"
        try:
            raw_fmt = self._settings.get(["display_format"])
            if raw_fmt is None:
                if logger:
                    logger.debug(
                        "_get_api_settings: display_format missing, "
                        "defaulting to 'full'"
                    )
            else:
                display_format = str(raw_fmt)
        except (AttributeError, TypeError, ValueError):
            if logger:
                logger.exception(
                    "_get_api_settings: failed to read display_format, "
                    "defaulting to 'full'"
                )

        default_poll, poll_min, poll_max = _INT_SETTING_BOUNDS["poll_interval_seconds"]
        poll_interval = default_poll
        try:
            raw_poll = self._settings.get(["poll_interval_seconds"])
            if raw_poll is None or raw_poll == "":
                if logger:
                    logger.debug(
                        "_get_api_settings: poll_interval_seconds missing, "
                        "defaulting to %s",
                        default_poll,
                    )
            else:
                try:
                    poll_interval = int(raw_poll)
                except (TypeError, ValueError):
                    if logger:
                        logger.debug(
                            "_get_api_settings: poll_interval_seconds invalid "
                            "(%r), defaulting to %s",
                            raw_poll,
                            default_poll,
                        )
            clamped = max(poll_min, min(poll_interval, poll_max))
            if clamped != poll_interval and logger:
                logger.debug(
                    "_get_api_settings: poll_interval_seconds %s out of range, "
                    "clamping to %s",
                    poll_interval,
                    clamped,
                )
            poll_interval = clamped
        except (AttributeError, TypeError, ValueError):
            poll_interval = default_poll
            if logger:
                logger.exception(
                    "_get_api_settings: failed to read poll_interval_seconds, "
                    "defaulting to %s",
                    default_poll,
                )

        return display_format, poll_interval
