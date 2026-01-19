# -*- coding: utf-8 -*-
"""OctoPrint-Uptime plugin module.

Provides a small API endpoint that returns formatted system uptime.
This module avoids importing OctoPrint/Flask at import-time so it can be
packaged and unit-tested without the OctoPrint runtime present.
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Type

try:
    import octoprint.plugin  # type: ignore
except ModuleNotFoundError:

    class _OctoPrintPluginStubs:
        class SettingsPlugin:
            def on_settings_save(self: Any, data: dict) -> dict:
                return data

        class SimpleApiPlugin:
            pass

        class AssetPlugin:
            pass

        class TemplatePlugin:
            pass

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
        pass

    SimpleApiPluginBase = _SimpleApiPluginDummy
if AssetPluginBase is object:

    class _AssetPluginDummy:
        pass

    AssetPluginBase = _AssetPluginDummy


def _format_uptime(seconds: float) -> str:
    """Format seconds into a full human-readable uptime string (default).
    Historically this function returned a string (the "full" format) and
    tests expect that behaviour. Return the full string here; callers that
    need the short form can use _format_uptime_short().
    """
    seconds = int(seconds)
    days = seconds // 86400
    rem = seconds - days * 86400
    hours = rem // 3600
    rem = rem - hours * 3600
    minutes = rem // 60
    secs = rem - minutes * 60

    parts = []
    if days:
        parts.append(f"{days}d")
    # include hours when present or when days are shown for consistency
    if hours or days:
        parts.append(f"{hours}h")
    # include minutes when present or when hours/days are shown
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    # always include seconds if nothing else was added,
    # otherwise include if non-zero
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _format_uptime_dhm(seconds: float) -> str:
    """Return days + hours + minutes representation.

    This returns "D H M" when days are present, otherwise "H M" for
    durations less than a day. Hours and minutes are always included so
    the representation is consistent across formats.
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


def _format_uptime_dh(seconds: float) -> str:
    """Return days + hours representation.

    Returns "D H" when days are present, otherwise "H" for durations
    less than a day. Hours are always included (0h when appropriate).
    """
    seconds = int(seconds)
    days = seconds // 86400
    rem = seconds - days * 86400
    hours = rem // 3600

    if days:
        return f"{days}d {hours}h"
    return f"{hours}h"


def _format_uptime_d(seconds: float) -> str:
    """Return days-only representation (0d if less than a day)."""
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

    def is_api_protected(self) -> bool:
        """Require authentication for API access (secure by default)."""
        return True

    def get_assets(self) -> Dict[str, List[str]]:
        """Return JS assets for registration by OctoPrint."""
        return dict(js=["js/uptime.js"])

    def get_template_configs(self) -> List[Dict[str, Any]]:
        """Return template configurations for OctoPrint."""

        return [
            {
                "type": "navbar",
                "name": "navbar_uptime",
                "template": "navbar.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "settings",
                "name": "OctoPrint Uptime",
                "template": "settings.jinja2",
                "custom_bindings": False,
            },
        ]

    def is_template_autoescaped(self):
        """Opt into OctoPrint's template autoescaping.
        Returning True signals OctoPrint to render this plugin's templates
        with autoescaping enabled by default (safer). Use the `|safe` filter
        in templates for any controlled HTML you intentionally want to allow.
        """
        return True

    def _get_uptime_seconds(self) -> float:
        """Retrieve system uptime in seconds using multiple fallbacks."""
        # 1) /proc/uptime (Linux)
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
        except Exception:
            pass

        # 2) psutil (if available)
        try:
            import psutil  # type: ignore

            return time.time() - psutil.boot_time()
        except Exception:
            pass

        # 3) fallback: `uptime -s` -> parse boot timestamp
        try:
            args = ["uptime", "-s"]
            out = subprocess.check_output(args, stderr=subprocess.DEVNULL)
            out = out.decode().strip()
            boot = time.mktime(time.strptime(out, "%Y-%m-%d %H:%M:%S"))
            return time.time() - boot
        except Exception:
            return 0

    def get_settings_defaults(self) -> Dict[str, Any]:
        """Return default plugin settings."""
        return dict(
            debug=False,
            navbar_enabled=True,
            display_format="full",
            debug_throttle_seconds=60,
            bundle_enabled=False,
            poll_interval_seconds=5,
        )

    def on_settings_initialized(self) -> None:
        """Initialize settings and throttling state."""
        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        self._bundle_enabled = bool(self._settings.get(["bundle_enabled"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._last_debug_time = 0
        # track when we last warned about throttled logging
        self._last_throttle_notice = 0
        # throttle debug messages (seconds)
        self._debug_throttle_seconds = int(
            self._settings.get(["debug_throttle_seconds"]) or 60
        )
        # Ensure plugin logger emits DEBUG when debug is enabled so toggle
        # events are visible in octoprint.log during troubleshooting.
        try:
            if getattr(self, "_logger", None) and self._debug_enabled:
                try:
                    self._logger.setLevel(logging.DEBUG)
                    self._logger.debug(
                        "UptimePlugin: debug logging enabled (level DEBUG)"
                    )
                except Exception:
                    # Not critical if logger cannot be adjusted
                    pass
        except Exception:
            pass

    def on_after_startup(self) -> None:
        """Called after OctoPrint startup — log plugin enabled at INFO level.

        This runs regardless of the plugin `debug` setting so the restart
        helper script can reliably detect the plugin has initialized.
        """
        try:
            translator = getattr(self, "_", None)
            if callable(translator):
                msg = translator("Uptime plugin enabled/loaded")
            else:
                msg = "Uptime plugin enabled/loaded"
            try:
                # Always log as INFO so restart verification sees it.
                if getattr(self, "_logger", None):
                    self._logger.info(msg)
            except Exception:
                pass
        except Exception:
            # Never raise during startup logging
            pass

    def on_settings_save(self, data: Dict[str, Any]) -> None:
        """Update cached debug flag when settings change. Log for debug."""
        # Validate and clamp numeric plugin settings before saving to avoid
        # storing out-of-range values. Expect data to include plugin values
        # under the `plugins -> octoprint_uptime` path when saving from UI.
        try:
            plugins = data.get("plugins") if isinstance(data, dict) else None
            if isinstance(plugins, dict):
                uptime_cfg = plugins.get("octoprint_uptime")
                if isinstance(uptime_cfg, dict):
                    keys = (
                        "debug_throttle_seconds",
                        "poll_interval_seconds",
                    )
                    for key in keys:
                        if key in uptime_cfg:
                            try:
                                raw = uptime_cfg.get(key)
                                if raw is None:
                                    raise ValueError()
                                val = int(raw)
                            except Exception:
                                # replace invalid values with sensible defaults
                                if key == "poll_interval_seconds":
                                    val = 5
                                else:
                                    val = 60
                            # clamp to 1..120
                            if val < 1:
                                val = 1
                            if val > 120:
                                val = 120
                            uptime_cfg[key] = val
        except Exception:
            pass
        try:
            if getattr(self, "_logger", None):
                # Log at debug level to avoid noisy info logs in production
                self._logger.debug("on_settings_save data: %r", data)
        except Exception:
            pass
        try:
            method = getattr(SettingsPluginBase, "on_settings_save", None)
            if callable(method):
                method(self, data)
        except Exception:
            pass
        try:
            prev_navbar = getattr(self, "_navbar_enabled", None)
        except Exception:
            prev_navbar = None
        try:
            prev_bundle = getattr(self, "_bundle_enabled", None)
        except Exception:
            prev_bundle = None

        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        self._bundle_enabled = bool(self._settings.get(["bundle_enabled"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._debug_throttle_seconds = int(
            self._settings.get(["debug_throttle_seconds"]) or 60
        )

        try:
            if getattr(self, "_logger", None):
                msg = (
                    "UptimePlugin: settings after save: debug=%s, "
                    "navbar_enabled=%s, display_format=%s, "
                    "debug_throttle_seconds=%s"
                )
                self._logger.info(
                    msg,
                    self._debug_enabled,
                    self._navbar_enabled,
                    self._display_format,
                    self._debug_throttle_seconds,
                )
        except Exception:
            pass
        try:
            logger = getattr(self, "_logger", None)
            if (
                logger
                and prev_navbar is not None
                and prev_navbar != self._navbar_enabled
            ):
                logger.info(
                    "UptimePlugin: navbar_enabled changed from %s to %s",
                    prev_navbar,
                    self._navbar_enabled,
                )
            try:
                if (
                    logger
                    and prev_bundle is not None
                    and prev_bundle != self._bundle_enabled
                ):
                    logger.info(
                        "UptimePlugin: bundle_enabled changed from %s to %s",
                        prev_bundle,
                        self._bundle_enabled,
                    )
            except Exception:
                pass
        except Exception:
            pass

    def _log_debug(self, message: str) -> None:
        """Throttled debug logger to avoid spam."""
        try:
            if not getattr(self, "_debug_enabled", False):
                return
            now = time.time()
            last_time = getattr(self, "_last_debug_time", 0)
            # Log at most once per throttle interval to avoid flooding the log
            if (now - last_time) < self._debug_throttle_seconds:
                # suppressed; emit a single informational notice at most
                # once per throttle interval so the operator knows logging
                # is being throttled instead of flooding octoprint.log
                last_notice = getattr(self, "_last_throttle_notice", 0)
                if (now - last_notice) >= self._debug_throttle_seconds:
                    try:
                        # prefer plugin translation when available
                        translator = getattr(self, "_", None)
                        if callable(translator):
                            notice = translator(
                                "Logging throttled to avoid flooding " "octoprint.log"
                            )
                        else:
                            notice = (
                                "Logging throttled to avoid flooding " "octoprint.log"
                            )
                        try:
                            self._logger.info(notice)
                        except Exception:
                            pass
                        self._last_throttle_notice = now
                    except Exception:
                        pass
                return
            self._last_debug_time = now
            try:
                self._logger.debug(message)
            except Exception:
                # ensure debug logging doesn't raise
                pass
        except Exception:
            # Never raise from debug logging
            pass

    def get_additional_systeminfo_files(self) -> List[Tuple[str, bytes]]:
        """Return additional files for OctoPrint's systeminfo bundle.

        Returns a list of (filename, content_bytes). If the bundle inclusion
        setting is disabled this returns an empty list.
        """
        try:
            if not getattr(self, "_bundle_enabled", False):
                return []

            seconds = self._get_uptime_seconds()
            if not isinstance(seconds, (int, float)):
                return []

            started = datetime.now() - timedelta(seconds=int(seconds))
            payload = {
                "started": started.isoformat(sep=" ", timespec="seconds"),
                "uptime_seconds": int(seconds),
                "uptime_human": _format_uptime(seconds),
            }
            content = json.dumps(payload, ensure_ascii=False, indent=2)
            content = content.encode("utf-8")
            return [("uptime.json", content)]
        except Exception:
            try:
                if getattr(self, "_logger", None):
                    self._logger.exception("Failed to build uptime bundle " "file")
            except Exception:
                pass
            return []

    def on_api_get(self, request: Any) -> Any:
        """Handle API GET request for uptime."""
        # Perform permissions check lazily; if OctoPrint isn't available
        # (e.g. during packaging/tests) skip the check and return a simple
        # python dict. Use Flask's abort/jsonify when available at runtime.
        try:
            try:
                import octoprint.access.permissions as _perm  # type: ignore

                if not _perm.Permissions.SYSTEM.can():
                    try:
                        import flask as _flask  # type: ignore

                        _flask.abort(403)
                    except Exception:
                        raise PermissionError("Forbidden")
            except Exception:
                # octoprint or permissions not available — skip check
                pass

            seconds = self._get_uptime_seconds()
            if isinstance(seconds, (int, float)):
                # compute multiple representations used by frontend
                uptime_full = _format_uptime(seconds)
                uptime_dhm = _format_uptime_dhm(seconds)
                uptime_dh = _format_uptime_dh(seconds)
                uptime_d = _format_uptime_d(seconds)
            else:
                uptime_full = str(seconds)
                uptime_dhm = str(seconds)
                uptime_dh = str(seconds)
                uptime_d = str(seconds)

            # debug trace (throttled)
            self._log_debug("Uptime API requested, result=%s" % (uptime_full,))
        except Exception:
            try:
                self._logger.exception("Error computing uptime")
            except Exception:
                pass
            uptime_full = "unknown"
            uptime_dhm = "unknown"
            uptime_dh = "unknown"
            uptime_d = "unknown"
            seconds = 0

        try:
            import flask as _flask  # type: ignore

            # Include current relevant settings so the frontend can react
            try:
                navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
            except Exception:
                navbar_enabled = True
            try:
                display_format = str(self._settings.get(["display_format"]))
            except Exception:
                display_format = "full"
            try:
                poll_interval = int(self._settings.get(["poll_interval_seconds"]) or 5)
            except Exception:
                poll_interval = 5

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
        except Exception:
            # Fallback for test environments: return a plain dict
            return dict(uptime=uptime_full)


# Backwards-compatible alias expected by tests
UptimePlugin = OctoprintUptimePlugin

__plugin_name__ = "OctoPrint-Uptime"
__plugin_pythoncompat__ = ">=3.10,<4"
__plugin_implementation__ = OctoprintUptimePlugin()
__plugin_description__ = (
    "Adds system uptime to the navbar and exposes a small uptime API."
)
__plugin_version__ = "0.1.0rc66"
