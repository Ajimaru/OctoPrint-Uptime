# -*- coding: utf-8 -*-
"""OctoPrint-Uptime plugin module.

Provides a small API endpoint that returns formatted system uptime.
This module avoids importing OctoPrint/Flask at import-time so it can be
packaged and unit-tested without the OctoPrint runtime present.
"""

import logging
import os
import subprocess
import time
from typing import Any, Type

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

    class _SettingsPluginDummy:  # pragma: no cover - trivial fallback
        pass

    SettingsPluginBase = _SettingsPluginDummy
if TemplatePluginBase is object:

    class _TemplatePluginDummy:  # pragma: no cover - trivial fallback
        pass

    TemplatePluginBase = _TemplatePluginDummy
if SimpleApiPluginBase is object:

    class _SimpleApiPluginDummy:  # pragma: no cover - trivial fallback
        pass

    SimpleApiPluginBase = _SimpleApiPluginDummy
if AssetPluginBase is object:

    class _AssetPluginDummy:  # pragma: no cover - trivial fallback
        pass

    AssetPluginBase = _AssetPluginDummy


def _format_uptime(seconds):
    """Format seconds into a full human-readable uptime string (default).

    Historically this function returned a string (the "full" format) and
    tests expect that behaviour. Return the full string here; callers that
    need the short form can use _format_uptime_short().
    """
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _format_uptime_short(seconds):
    """Return the 'short' uptime representation (days + hours)."""
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours}h")
    return " ".join(parts)


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

    def is_api_protected(self):
        """API is now public for debugging (no auth required)."""
        return False

    def get_assets(self):
        """Return JS assets for registration by OctoPrint."""
        return dict(js=["js/uptime.js"])

    def get_template_configs(self):
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

    def _get_uptime_seconds(self):
        """Retrieve system uptime in seconds using multiple fallbacks."""
        # 1) /proc/uptime (Linux)
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
        except Exception:
            pass

        # 2) psutil (falls verfügbar)
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

    def get_settings_defaults(self):
        """Return default plugin settings."""
        return dict(
            debug=False,
            navbar_enabled=True,
            display_format="full",
            debug_throttle_seconds=60,
        )

    def on_settings_initialized(self):
        """Initialize settings and throttling state."""
        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
        self._display_format = str(self._settings.get(["display_format"]))
        self._last_debug_time = 0
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

    def on_settings_save(self, data):
        """Update cached debug flag when settings change. Log for debug."""
        try:
            if getattr(self, "_logger", None):
                self._logger.info(
                    "on_settings_save called with data: %r",
                    data,
                )
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

        self._debug_enabled = bool(self._settings.get(["debug"]))
        self._navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
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
        except Exception:
            pass

    def _log_debug(self, message):
        """Throttled debug logger to avoid spam."""
        try:
            if not getattr(self, "_debug_enabled", False):
                return
            now = time.time()
            last_time = getattr(self, "_last_debug_time", 0)
            # Log at most once per throttle interval to avoid flooding the log
            if (now - last_time) < self._debug_throttle_seconds:
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

    def on_api_get(self, request):
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
                # compute both full and short representations
                uptime_full = _format_uptime(seconds)
                uptime_short = _format_uptime_short(seconds)
            else:
                uptime_full = uptime_short = str(seconds)

            # debug trace (throttled)
            self._log_debug("Uptime API requested, result=%s" % (uptime_full,))
        except Exception:
            try:
                self._logger.exception("Error computing uptime")
            except Exception:
                pass
            uptime_full = uptime_short = "unknown"
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

            return _flask.jsonify(
                uptime=uptime_full,
                uptime_short=uptime_short,
                seconds=seconds,
                navbar_enabled=navbar_enabled,
                display_format=display_format,
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
__plugin_version__ = "0.1.0rc51"
