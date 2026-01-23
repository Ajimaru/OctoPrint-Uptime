import gettext
import logging
import os
import subprocess
import time

# json not required at module level; remove unused import to satisfy linters
# datetime/timedelta are not used at module level; remove to satisfy linters
from typing import Any, Dict, List, Tuple, Type

try:
    _ = gettext.gettext
except Exception:

    def _(message):
        return message


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
        pass

    SimpleApiPluginBase = _SimpleApiPluginDummy
if AssetPluginBase is object:

    class _AssetPluginDummy:
        pass

    AssetPluginBase = _AssetPluginDummy
if StartupPluginBase is object:

    class _StartupPluginDummy:
        pass

    StartupPluginBase = _StartupPluginDummy


def _format_uptime(seconds: float) -> str:
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
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    if secs or not parts:
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

    def get_update_information(self):
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
        return True

    def get_assets(self) -> Dict[str, List[str]]:
        return dict(js=["js/uptime.js"])

    def get_template_configs(self) -> List[Dict[str, Any]]:
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
        return True

    def _get_uptime_seconds(self) -> float:
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
        except Exception:
            pass
        try:
            import psutil  # type: ignore

            return time.time() - psutil.boot_time()
        except Exception:
            pass
        try:
            args = ["uptime", "-s"]
            out = subprocess.check_output(args, stderr=subprocess.DEVNULL)
            out = out.decode().strip()
            boot = time.mktime(time.strptime(out, "%Y-%m-%d %H:%M:%S"))
            return time.time() - boot
        except Exception:
            return 0

    def get_uptime_seconds(self) -> float:
        """Public wrapper for `_get_uptime_seconds` for tests and external callers."""
        return self._get_uptime_seconds()

    def get_settings_defaults(self) -> Dict[str, Any]:
        return dict(
            debug=False,
            navbar_enabled=True,
            display_format="full",
            debug_throttle_seconds=60,
            poll_interval_seconds=5,
        )

    def on_settings_initialized(self) -> None:
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
                except Exception:
                    pass
        except Exception:
            pass

    def on_after_startup(self) -> None:
        return

    def on_settings_save(self, data: Dict[str, Any]) -> None:
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
                                val = 5 if key == "poll_interval_seconds" else 60
                            if val < 1:
                                val = 1
                            if val > 120:
                                val = 120
                            uptime_cfg[key] = val
        except Exception:
            pass
        try:
            if getattr(self, "_logger", None):
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
            except Exception:
                pass
        except Exception:
            pass

    def get_additional_systeminfo_files(self) -> List[Tuple[str, bytes]]:
        return []

    def on_api_get(self, request: Any) -> Any:
        try:
            try:
                import octoprint.access.permissions as _perm  # type: ignore

                if not _perm.Permissions.SYSTEM.can():
                    try:
                        import flask as _flask  # type: ignore

                        _flask.abort(403)
                    except Exception:
                        raise PermissionError(_("Forbidden"))
            except Exception:
                pass
            getter = getattr(self, "get_uptime_seconds", None)
            if callable(getter):
                seconds = getter()
            else:
                seconds = self._get_uptime_seconds()
            if isinstance(seconds, (int, float)):
                uptime_full = _format_uptime(seconds)
                uptime_dhm = _format_uptime_dhm(seconds)
                uptime_dh = _format_uptime_dh(seconds)
                uptime_d = _format_uptime_d(seconds)
            else:
                uptime_full = str(seconds)
                uptime_dhm = str(seconds)
                uptime_dh = str(seconds)
                uptime_d = str(seconds)
            self._log_debug(_("Uptime API requested, result=%s") % (uptime_full,))
        except Exception:
            try:
                self._logger.exception(_("Error computing uptime"))
            except Exception:
                pass
            uptime_full = _("unknown")
            uptime_dhm = _("unknown")
            uptime_dh = _("unknown")
            uptime_d = _("unknown")
            seconds = 0
        try:
            import flask as _flask  # type: ignore

            try:
                navbar_enabled = bool(self._settings.get(["navbar_enabled"]))
            except Exception:
                navbar_enabled = True
            try:
                display_format = str(self._settings.get(["display_format"]))
            except Exception:
                display_format = _("full")
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
            return dict(uptime=uptime_full)
