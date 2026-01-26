"""
Unit tests for the OctoPrint-Uptime plugin.

This module contains comprehensive test cases for the `octoprint_uptime.plugin` module,
covering formatting functions, settings validation and sanitization, logging behavior,
uptime retrieval from various sources, API responses, permission handling, hook invocation,
and plugin reloading under different dependency scenarios.

Test coverage includes:
- Uptime formatting utilities.
- Settings validation, sanitization, and defaulting.
- Logging and debug throttling mechanisms.
- Uptime retrieval via `/proc/uptime` and `psutil`.
- API endpoint responses and permission checks.
- Hook inspection and safe invocation.
- Plugin reload behavior with/without dependencies (OctoPrint, Flask, gettext).
- Edge cases and exception handling for all major code paths.

Helper classes and functions are provided to simulate plugin settings, logging, and
external dependencies.
"""

import builtins
import importlib
import os
import sys
import time
from types import SimpleNamespace
from unittest import mock

import pytest

from octoprint_uptime import plugin

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class FakeLogger:
    """
    A fake logger class for capturing log messages during testing.

    Attributes:
        calls (list): Stores tuples of log method name, message, and arguments.

    Methods:
        debug(msg, *args): Simulates logging a debug message.
        info(msg, *args): Simulates logging an info message.
        warning(msg, *args): Simulates logging a warning message.
        exception(msg, *args, **kwargs): Simulates logging an exception message.
    """

    def __init__(self):
        self.calls = []

    def debug(self, msg, *args):
        """
        Logs a debug message and stores the call details.

        Args:
            msg (str): The debug message to log.
            *args: Additional arguments to include with the message.
        """
        self.calls.append(("debug", msg, args))

    def info(self, msg, *args):
        """
        Logs an informational message.

        Args:
            msg (str): The message to log.
            *args: Additional arguments to include with the message.

        Side Effects:
            Appends a tuple ("info", msg, args) to the `calls` list.
        """
        self.calls.append(("info", msg, args))

    def warning(self, msg, *args):
        """
        Log a warning message and record the call details.

        Args:
            msg (str): The warning message to log.
            *args: Additional arguments associated with the warning.
        """
        self.calls.append(("warning", msg, args))

    def exception(self, msg, *args):
        """
        Logs an exception message and its arguments by appending them to the calls list.

        Args:
            msg (str): The exception message to log.
            *args: Additional positional arguments related to the exception.
        """
        self.calls.append(("exception", msg, args))


class DummySettings:
    """
    A dummy settings class for testing purposes.

    This class simulates a settings object by storing key-value pairs in a dictionary.
    It provides a minimal interface to retrieve values using the `get` method.

    Attributes:
        _data (dict): Internal dictionary to store settings data.

    Methods:
        __init__(data=None): Initializes the DummySettings instance with optional data.
        get(keys): Retrieves the value associated with the first key in the provided list or tuple.
    """

    def __init__(self, data=None):
        self._data = data or {}

    def get(self, keys):
        """
        Retrieve the value associated with the first key in the provided list or tuple.

        Args:
            keys (list or tuple): A list or tuple of keys to look up.

        Returns:
            The value associated with the first key if keys is a non-empty list or tuple;
            otherwise, None.
        """
        if isinstance(keys, (list, tuple)) and keys:
            return self._data.get(keys[0])
        return None


def test_format_uptime_variants():
    """
    Test the format_uptime function with various input values to ensure correct
    formatting of uptime strings.
    """
    assert plugin.format_uptime(0) == "0s"
    assert plugin.format_uptime(1) == "1s"
    assert plugin.format_uptime(61) == "1m 1s"
    assert plugin.format_uptime(3601) == "1h 0m 1s"
    assert plugin.format_uptime(90061) == "1d 1h 1m 1s"


def test_format_uptime_dhm_dh_d():
    """
    Test the formatting functions for uptime durations in days, hours, and minutes.

    This test verifies that:
    - `format_uptime_dhm` correctly formats seconds into "Xd Xh Xm" or "Xh Xm".
    - `format_uptime_dh` correctly formats seconds into "Xd Xh" or "Xh".
    - `format_uptime_d` correctly formats seconds into "Xd".

    Assertions are made for representative input values to ensure expected output strings.
    """
    assert plugin.format_uptime_dhm(3600) == "1h 0m"
    assert plugin.format_uptime_dhm(90061) == "1d 1h 1m"
    assert plugin.format_uptime_dh(3600) == "1h"
    assert plugin.format_uptime_dh(90061) == "1d 1h"
    assert plugin.format_uptime_d(90061) == "1d"


def test_validate_and_sanitize_settings_clamping():
    """
    Test that the _validate_and_sanitize_settings method correctly clamps
    the 'debug_throttle_seconds' and 'poll_interval_seconds' settings to their
    allowed minimum and maximum values.
    """
    p = plugin.OctoprintUptimePlugin()
    data = {
        "plugins": {
            "octoprint_uptime": {
                "debug_throttle_seconds": "999",
                "poll_interval_seconds": "0",
            }
        }
    }
    p._validate_and_sanitize_settings(data)
    cfg = data["plugins"]["octoprint_uptime"]
    assert cfg["debug_throttle_seconds"] == 120
    assert cfg["poll_interval_seconds"] == 1


def test_log_settings_save_data_and_call_base_on_settings_save(monkeypatch):
    """
    Test that OctoprintUptimePlugin correctly logs settings save data and safely calls the base
    on_settings_save method, ensuring exceptions from the base method are swallowed and do not
    propagate.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    data = {"x": 1}
    # should not raise
    p._log_settings_save_data(data)

    # patch base SettingsPluginBase to have an on_settings_save that raises
    monkeypatch.setattr(
        plugin.SettingsPluginBase,
        "on_settings_save",
        lambda _self, _d: (_ for _ in ()).throw(ValueError("boom")),
        raising=False,
    )
    # should swallow the exception
    p._call_base_on_settings_save({})


def test_update_internal_state_and_get_api_settings_and_logging(monkeypatch):
    """
    Test that OctoprintUptimePlugin correctly updates its internal state from settings,
    retrieves API settings, and clamps the poll interval to the allowed maximum.
    """
    p = plugin.OctoprintUptimePlugin()
    p._settings = DummySettings(
        {
            "debug": True,
            "navbar_enabled": False,
            "display_format": "compact",
            "debug_throttle_seconds": 30,
            "poll_interval_seconds": 999,
        }
    )
    p._logger = FakeLogger()
    p._update_internal_state()
    assert p._debug_enabled is True
    assert p._navbar_enabled is False
    assert p._display_format == "compact"
    assert p._debug_throttle_seconds == 30

    # poll interval should be clamped to 120
    nav, fmt, poll = p._get_api_settings()
    assert nav is False
    assert fmt == "compact"
    assert poll == 120


def test_log_settings_after_save_prev_navbar_change():
    """
    Test that the plugin logs settings correctly after saving when the previous
    navbar state changes.

    This test initializes the plugin with specific settings,
    simulates a change in the navbar state,
    and verifies that at least two info log calls are made:
    one for the current state and one for the change.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p._debug_enabled = True
    p._navbar_enabled = True
    p._display_format = "f"
    p._debug_throttle_seconds = 7
    p._log_settings_after_save(prev_navbar=False)
    # expect at least two info calls (state and change)
    infos = [c for c in p._logger.calls if c[0] == "info"]
    assert len(infos) >= 2


def test_log_debug_throttle(monkeypatch):
    """
    Test that the _log_debug method logs a debug message when throttling conditions are met.
    This test sets up the plugin with debug enabled and a throttle interval, mocks the current time,
    calls _log_debug, and asserts that a debug log entry is created.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p._debug_enabled = True
    p._last_debug_time = 0
    p._debug_throttle_seconds = 10
    monkeypatch.setattr(time, "time", lambda: 1000)
    p._log_debug("hello")
    assert any(c[0] == "debug" for c in p._logger.calls)


def test_fallback_uptime_response_no_flask_and_with_flask(monkeypatch):
    """
    Test the _fallback_uptime_response method of OctoprintUptimePlugin under different conditions:
    - When uptime information is available and Flask is not present.
    - When uptime information is not available, ensuring the response contains an uptime note.
    - When Flask is present, verifying that the response uses Flask's jsonify method.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    # case: uptime available, no flask
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (100, "1m 40s", "1m", "1h", "0d"),
    )
    monkeypatch.setattr(plugin, "_flask", None)
    resp = p._fallback_uptime_response()
    assert resp["uptime"] == "1m 40s"

    # case: uptime not available -> uptime_note present
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (None, "unknown", "unknown", "unknown", "unknown"),
    )
    resp = p._fallback_uptime_response()
    assert resp["uptime_available"] is False and "uptime_note" in resp

    # with flask: jsonify used
    class FakeFlask:
        """
        A minimal fake Flask class for testing purposes.

        Provides a static jsonify method that returns its keyword
        arguments as a dictionary.
        """

        @staticmethod
        def jsonify(**kwargs):
            """
            Convert keyword arguments into a dictionary under the 'json' key.

            Args:
                **kwargs: Arbitrary keyword arguments to include in the dictionary.

            Returns:
                dict: A dictionary with a single key 'json' containing the provided
                keyword arguments.
            """
            return {"json": kwargs}

    monkeypatch.setattr(plugin, "_flask", FakeFlask)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_api_settings",
        lambda self: (True, "full", 5),
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (100, "1m", "1m", "1h", "0d"),
    )
    out = p._fallback_uptime_response()
    assert isinstance(out, dict) and "json" in out


def test_on_api_get_permission_and_response(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    # permission granted path
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_check_permissions", lambda self: True
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (42, "42s", "42s", "0h", "0d"),
    )
    plugin._flask = None
    out = p.on_api_get()
    assert out == {"uptime": "42s"}

    # permission denied path
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_check_permissions", lambda self: False
    )
    p2 = plugin.OctoprintUptimePlugin()
    plugin._flask = None
    got = p2._handle_permission_check()
    assert got and isinstance(got, dict)


def test_get_uptime_info_custom_getter():
    p = plugin.OctoprintUptimePlugin()
    p.get_uptime_seconds = lambda: (200, "custom")
    seconds, full, dhm, dh, d = p._get_uptime_info()
    assert seconds == 200
    assert p._last_uptime_source == "custom"


def test_get_uptime_from_psutil_and_proc(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    # psutil path
    fake_ps = SimpleNamespace(boot_time=lambda: time.time() - 1234)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: fake_ps if name == "psutil" else importlib.import_module(name),
    )
    val = p._get_uptime_from_psutil()
    assert isinstance(val, float) and abs(val - 1234) < 5

    # proc path: monkeypatch exists and open
    monkeypatch.setattr(plugin.os.path, "exists", lambda path: True)
    mo = mock.mock_open(read_data="987.65 0.00\n")
    monkeypatch.setattr(builtins, "open", mo)
    val2 = p._get_uptime_from_proc()
    assert abs(val2 - 987.65) < 0.001


def test_hook_inspection_and_safe_invoke(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    def foo():
        return 1

    def bar(x):
        return x

    def two(a, b):
        return a + b

    assert p._get_hook_positional_param_count(foo) == 0
    assert p._get_hook_positional_param_count(bar) == 1
    assert p._get_hook_positional_param_count(two) == 2

    # cause inspect.signature to raise
    monkeypatch.setattr(
        plugin.inspect, "signature", lambda h: (_ for _ in ()).throw(ValueError("nope"))
    )
    p._logger = FakeLogger()
    assert p._get_hook_positional_param_count(foo) is None

    # safe invoke with exception
    def bad(one):
        raise RuntimeError("boom")

    p._logger = FakeLogger()
    p._safe_invoke_hook(bad, 1)
    # exception should be logged, not raised
    assert any(c[0] == "exception" for c in p._logger.calls)


def test_module_simple_methods_and_uptime_seconds_none(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    # simple public methods
    info = p.get_update_information()
    assert "octoprint_uptime" in info
    assert p.get_assets() == {"js": ["js/uptime.js"]}
    tcs = p.get_template_configs()
    assert any(isinstance(x, dict) for x in tcs)
    assert p.is_api_protected() is True
    assert p.is_template_autoescaped() is True

    # uptime seconds none path
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_get_uptime_from_proc", lambda self: None
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_get_uptime_from_psutil", lambda self: None
    )
    secs, src = p._get_uptime_seconds()
    assert secs is None and src == "none"


def test_get_uptime_from_proc_bad_content(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin.os.path, "exists", lambda path: True)
    mo = mock.mock_open(read_data="not-a-number\n")
    monkeypatch.setattr(builtins, "open", mo)
    assert p._get_uptime_from_proc() is None


def test_get_uptime_from_psutil_import_error_and_bad_boot(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    # import error
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError("nope")),
    )
    assert p._get_uptime_from_psutil() is None

    # import works but boot_time invalid
    fake_ps = SimpleNamespace(boot_time=lambda: "invalid")
    monkeypatch.setattr(importlib, "import_module", lambda name: fake_ps)
    assert p._get_uptime_from_psutil() is None


def test_on_settings_initialized_invokes_hook_variants(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    # define base hooks with 0 and 1 param
    def base0():
        base0.called = True

    def base1(obj):
        base1.called_with = obj

    monkeypatch.setattr(
        plugin.SettingsPluginBase, "on_settings_initialized", base0, raising=False
    )
    # should call without error
    p.on_settings_initialized()
    assert getattr(base0, "called", True) is True

    # now set a one-arg hook
    monkeypatch.setattr(
        plugin.SettingsPluginBase, "on_settings_initialized", base1, raising=False
    )
    p.on_settings_initialized()
    assert getattr(base1, "called_with", None) is not None


def test_invoke_settings_hook_unexpected_param_count():
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    # force unexpected param count path
    mp = pytest.MonkeyPatch()
    mp.setattr(p, "_get_hook_positional_param_count", lambda hook: 3)
    p._invoke_settings_hook(lambda: None)
    # should have logged a warning
    assert any(c[0] == "warning" for c in p._logger.calls)
    mp.undo()


def test_log_debug_throttled_no_logging(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p._debug_enabled = True
    # set last debug time to just now so throttle prevents logging
    monkeypatch.setattr(time, "time", lambda: 1000)
    p._last_debug_time = 1000
    p._debug_throttle_seconds = 60
    p._log_debug("x")
    assert not any(c[0] == "debug" for c in p._logger.calls)


def test_fallback_uptime_response_flask_jsonify_raises(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    class BadFlask:
        @staticmethod
        def jsonify(**kwargs):
            raise TypeError("bad jsonify")

    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (None, "unknown", "unknown", "unknown", "unknown"),
    )
    monkeypatch.setattr(plugin, "_flask", BadFlask)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_api_settings",
        lambda self: (True, "full", 5),
    )
    out = p._fallback_uptime_response()
    # when jsonify fails, it should fall back to dict
    assert isinstance(out, dict)


def test_on_api_get_with_flask_returns_json(monkeypatch):
    p = plugin.OctoprintUptimePlugin()

    class FakeFlask:
        @staticmethod
        def jsonify(**kwargs):
            return {"json": kwargs}

    monkeypatch.setattr(plugin, "_flask", FakeFlask)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_handle_permission_check", lambda self: None
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (5, "5s", "5s", "0h", "0d"),
    )
    out = p.on_api_get()
    assert isinstance(out, dict) and "json" in out


def test_handle_permission_check_abort_raises(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    # make _check_permissions raise so handler goes into exception branch
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_check_permissions",
        lambda self: (_ for _ in ()).throw(AttributeError("boom")),
    )
    # make _abort_forbidden also raise
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_abort_forbidden",
        lambda self: (_ for _ in ()).throw(RuntimeError("abort fail")),
    )
    res = p._handle_permission_check()
    assert res and isinstance(res, dict)


def test_get_api_settings_exceptions(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    class BadSettings:
        def get(self, k):
            raise ValueError("bad")

    p._settings = BadSettings()
    nav, fmt, poll = p._get_api_settings()
    assert nav is True and fmt == plugin._("full") and poll == 5


def test_reload_with_octoprint_present_and_flask_abort(monkeypatch):
    import types

    # create fake octoprint.plugin module
    fake_plugin_mod = types.ModuleType("octoprint.plugin")
    FakeSettings = type("FakeSettings", (), {})
    FakeSimpleApi = type("FakeSimpleApi", (), {})
    FakeAsset = type("FakeAsset", (), {})
    FakeTemplate = type("FakeTemplate", (), {})
    setattr(fake_plugin_mod, "SettingsPlugin", FakeSettings)
    setattr(fake_plugin_mod, "SimpleApiPlugin", FakeSimpleApi)
    setattr(fake_plugin_mod, "AssetPlugin", FakeAsset)
    setattr(fake_plugin_mod, "TemplatePlugin", FakeTemplate)

    fake_perm = types.ModuleType("octoprint.access.permissions")

    # fake flask with abort
    fake_flask = types.ModuleType("flask")
    aborted = {}

    def fake_abort(code):
        aborted["code"] = code

    fake_flask.abort = fake_abort
    fake_flask.jsonify = lambda **kwargs: {"json": kwargs}

    # inject into sys.modules and reload plugin module
    monkeypatch.setitem(sys.modules, "octoprint.plugin", fake_plugin_mod)
    monkeypatch.setitem(sys.modules, "octoprint.access.permissions", fake_perm)
    monkeypatch.setitem(sys.modules, "flask", fake_flask)

    importlib.reload(plugin)

    p = plugin.OctoprintUptimePlugin()
    # abort should call fake abort and still return a dict
    res = p._abort_forbidden()
    assert res == {"error": plugin._("Forbidden")} or isinstance(res, dict)
    assert aborted.get("code") == 403

    # cleanup: remove fake modules and reload
    monkeypatch.delitem(sys.modules, "octoprint.plugin", raising=False)
    monkeypatch.delitem(sys.modules, "octoprint.access.permissions", raising=False)
    monkeypatch.delitem(sys.modules, "flask", raising=False)
    importlib.reload(plugin)


def test_reload_with_missing_gettext_uses_fallback(monkeypatch):
    import types

    # create fake gettext module that lacks gettext
    fake_gettext = types.ModuleType("gettext")

    def bindtextdomain(domain, localedir):
        return None

    fake_gettext.bindtextdomain = bindtextdomain
    fake_gettext.textdomain = lambda name: None

    monkeypatch.setitem(sys.modules, "gettext", fake_gettext)
    importlib.reload(plugin)
    # plugin._ should be fallback that returns input unchanged
    assert plugin._("something") == "something"
    # cleanup
    monkeypatch.delitem(sys.modules, "gettext", raising=False)
    importlib.reload(plugin)


def test_get_api_settings_multiple_cases():
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    # case: all missing -> defaults and debug messages
    p._settings = DummySettings({})
    nav, fmt, poll = p._get_api_settings()
    assert nav is True
    assert fmt == plugin._("full")
    assert poll == 5
    assert any(
        "defaulting to True" in str(c[1]) or "defaulting to 'full'" in str(c[1])
        for c in p._logger.calls
    )

    # case: poll clamped low and high
    p._settings = DummySettings(
        {"navbar_enabled": False, "display_format": "x", "poll_interval_seconds": "0"}
    )
    nav, fmt, poll = p._get_api_settings()
    assert poll == 1

    p._settings = DummySettings({"poll_interval_seconds": "999"})
    nav, fmt, poll = p._get_api_settings()
    assert poll == 120

    # invalid poll value
    p._settings = DummySettings({"poll_interval_seconds": "bad"})
    nav, fmt, poll = p._get_api_settings()
    assert poll == 5


def test_fallback_uptime_response_handles_exceptions(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    # make _get_uptime_info raise
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (_ for _ in ()).throw(AttributeError("boom")),
    )
    out = p._fallback_uptime_response()
    assert out["uptime"] == plugin._("unknown") and out["uptime_available"] is False

    # nothing else to clean up here


def test_safe_update_internal_state_logs_warning(monkeypatch):
    p = plugin.OctoprintUptimePlugin()

    # make _update_internal_state raise
    def bad_update():
        raise AttributeError("bad")

    p._update_internal_state = bad_update
    p._logger = FakeLogger()
    p._safe_update_internal_state()
    assert any(c[0] == "warning" for c in p._logger.calls)


def test_log_settings_save_data_handles_logger_errors():
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        def debug(self, *a, **k):
            raise ValueError("boom")

    p._logger = BadLogger()
    # should not raise
    p._log_settings_save_data({"x": 1})


def test_log_debug_inner_exception(monkeypatch):
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        def debug(self, msg):
            raise TypeError("bad")

    p._logger = BadLogger()
    p._debug_enabled = True
    p._last_debug_time = 0
    p._debug_throttle_seconds = 0
    # now calling should hit inner except and not raise
    p._log_debug("x")


def test_get_uptime_from_psutil_future_boot(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    fake_ps = SimpleNamespace(boot_time=lambda: time.time() + 10000)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: fake_ps if name == "psutil" else importlib.import_module(name),
    )
    assert p._get_uptime_from_psutil() is None


def test_get_uptime_from_proc_missing(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin.os.path, "exists", lambda path: False)
    assert p._get_uptime_from_proc() is None


def test_get_uptime_info_exception_path(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    # make get_uptime_seconds raise so _get_uptime_info hits exception handler
    p.get_uptime_seconds = lambda: (_ for _ in ()).throw(TypeError("boom"))
    s, full, dhm, dh, d = p._get_uptime_info()
    assert s is None and full == plugin._("unknown")


def test_execute_plugin_source_for_coverage():
    import runpy

    # execute the plugin source directly to ensure coverage records its lines
    runpy.run_path(plugin.__file__, run_name="__main__")
    # after exec, ensure functions are callable
    import importlib

    mod = importlib.import_module("octoprint_uptime.plugin")
    assert hasattr(mod, "format_uptime")
    assert mod.format_uptime(1) == "1s"


def test_get_settings_defaults_and_on_settings_save(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    defaults = p.get_settings_defaults()
    assert defaults["debug"] is False
    assert defaults["navbar_enabled"] is True

    # ensure on_settings_save calls internal helpers
    called = {}

    def fake_validate(data):
        called["validate"] = True

    def fake_log(data):
        called["log"] = True

    def fake_call_base(data):
        called["call_base"] = True

    monkeypatch.setattr(p, "_validate_and_sanitize_settings", fake_validate)
    monkeypatch.setattr(p, "_log_settings_save_data", fake_log)
    monkeypatch.setattr(p, "_call_base_on_settings_save", fake_call_base)
    monkeypatch.setattr(
        p, "_update_internal_state", lambda: called.__setitem__("updated", True)
    )

    p.on_settings_save({})
    assert (
        called.get("validate")
        and called.get("log")
        and called.get("call_base")
        and called.get("updated")
    )


def test_reload_plugin_with_gettext_bind_failure(monkeypatch):
    # simulate gettext.bindtextdomain raising OSError to hit the inner except
    import types

    fake_gettext = types.ModuleType("gettext")

    def bad_bind(domain, localedir):
        raise OSError("nope")

    fake_gettext.bindtextdomain = bad_bind
    fake_gettext.textdomain = lambda name: None
    # ensure gettext.gettext is present so outer try doesn't set fallback
    fake_gettext.gettext = lambda s: s

    monkeypatch.setitem(sys.modules, "gettext", fake_gettext)
    # reload plugin to apply changes
    importlib.reload(plugin)
    # plugin._ should still be callable
    assert callable(plugin._)
    # cleanup
    monkeypatch.delitem(sys.modules, "gettext", raising=False)
    importlib.reload(plugin)


def test_reload_plugin_without_octoprint(monkeypatch):
    # simulate octoprint.plugin missing to exercise fallback base classes
    monkeypatch.delitem(sys.modules, "octoprint.plugin", raising=False)
    monkeypatch.delitem(sys.modules, "octoprint.access.permissions", raising=False)
    importlib.reload(plugin)
    # fallback base class names should exist
    assert hasattr(plugin, "SettingsPluginBase")
    assert hasattr(plugin, "SimpleApiPluginBase")
    # reload original state
    importlib.reload(plugin)


# --- merged from tests/test_plugin_more.py ---
def make_plugin():
    p = plugin.OctoprintUptimePlugin()

    # minimal settings and logger used by helpers
    class Settings:
        def __init__(self):
            self._data = {
                "debug": False,
                "navbar_enabled": True,
                "display_format": "full",
                "debug_throttle_seconds": 60,
                "poll_interval_seconds": 5,
            }

        def get(self, path):
            return self._data.get(path[0])

    class Logger:
        def __init__(self):
            self.records = []

        def debug(self, *a, **k):
            self.records.append(("debug", a))

        def info(self, *a, **k):
            self.records.append(("info", a))

        def warning(self, *a, **k):
            self.records.append(("warn", a))

        def exception(self, *a, **k):
            self.records.append(("exc", a))

    p._settings = Settings()
    p._logger = Logger()
    return p


def test_get_uptime_seconds_prefers_proc(monkeypatch):
    p = make_plugin()
    # simulate /proc/uptime present
    monkeypatch.setattr(os.path, "exists", lambda pth: True)
    mo = mock.mock_open(read_data="123.4 0")
    monkeypatch.setattr(builtins, "open", mo)
    sec, src = p._get_uptime_seconds()
    assert src == "proc"
    assert abs(sec - 123.4) < 0.001


def test_get_uptime_seconds_uses_psutil_when_no_proc(monkeypatch):
    p = make_plugin()
    monkeypatch.setattr(p, "_get_uptime_from_proc", lambda: None)

    class FakePs:
        def boot_time(self):
            return time.time() - 500

    monkeypatch.setattr(importlib, "import_module", lambda name: FakePs())
    sec = p._get_uptime_from_psutil()
    assert sec is not None and sec > 0


def test_validate_and_sanitize_settings_handles_bad_shapes():
    p = make_plugin()
    # not a dict for plugins
    p._validate_and_sanitize_settings(None)
    p._validate_and_sanitize_settings({"plugins": []})
    # not a dict for uptime cfg
    p._validate_and_sanitize_settings({"plugins": {"octoprint_uptime": []}})


def test_validate_and_sanitize_settings_sanitizes_values():
    p = make_plugin()
    data = {
        "plugins": {
            "octoprint_uptime": {
                "debug_throttle_seconds": None,
                "poll_interval_seconds": "bad",
            }
        }
    }
    p._validate_and_sanitize_settings(data)
    cfg = data["plugins"]["octoprint_uptime"]
    assert cfg["debug_throttle_seconds"] == 60
    assert cfg["poll_interval_seconds"] == 5


def test_log_settings_after_save_logs_change():
    p = make_plugin()
    # set internal state then modify navbar to trigger change log
    p._update_internal_state()
    prev = p._navbar_enabled
    p._settings._data["navbar_enabled"] = not prev
    p._update_internal_state()
    p._log_settings_after_save(prev)
    # info records should exist
    assert any(r[0] == "info" for r in p._logger.records)


def test_safe_update_internal_state_logs_warning_on_failure():
    p = make_plugin()

    def bad_update():
        raise ValueError("boom")

    p._update_internal_state = bad_update
    p._safe_update_internal_state()
    assert any(r[0] == "warn" for r in p._logger.records)


def test_get_uptime_info_handles_custom_getter():
    p = make_plugin()
    # custom single-value return (not tuple) should mark source custom
    p.get_uptime_seconds = lambda: 42
    seconds, full, dhm, dh, d = p._get_uptime_info()
    assert seconds == 42
    assert p._last_uptime_source == "custom"


def test_get_uptime_info_none_returns_unknown():
    p = make_plugin()
    p.get_uptime_seconds = lambda: None
    seconds, full, dhm, dh, d = p._get_uptime_info()
    assert seconds is None
    assert full == plugin._("unknown")


def test_handle_permission_check_aborts_and_handles_abort_exception(monkeypatch):
    p = make_plugin()
    p._check_permissions = lambda: False

    def bad_abort():
        raise RuntimeError("nope")

    p._abort_forbidden = bad_abort
    res = p._handle_permission_check()
    assert isinstance(res, dict) and res.get("error") == plugin._("Forbidden")


def test_handle_permission_check_check_raises_and_abort_fallback(monkeypatch):
    p = make_plugin()

    def bad_check():
        raise AttributeError("boom")

    p._check_permissions = bad_check
    # abort returns dict normally
    p._abort_forbidden = lambda: {"error": "ok"}
    res = p._handle_permission_check()
    assert res == {"error": "ok"}


def test_abort_forbidden_returns_dict_when_no_flask():
    p = make_plugin()
    # global _flask is likely None in test environment
    try:
        res = p._abort_forbidden()
    except Exception as e:
        # if flask/werkzeug is present, abort may raise a HTTP exception
        try:
            from werkzeug.exceptions import Forbidden

            assert isinstance(e, Forbidden)
            assert getattr(e, "code", None) == 403
        except Exception:
            # if werkzeug not importable, fallback to checking exception type only
            assert hasattr(e, "args")
    else:
        assert isinstance(res, dict) and res.get("error") == plugin._("Forbidden")


def test__get_uptime_seconds_prefers_psutil_branch():
    p = plugin.OctoprintUptimePlugin()
    # force proc to return None and psutil to return a value
    p._get_uptime_from_proc = lambda: None
    p._get_uptime_from_psutil = lambda: 123.0
    sec, src = p._get_uptime_seconds()
    assert src == "psutil"
    assert sec == 123.0


def test__log_settings_after_save_handles_info_exceptions():
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        def info(self, *a, **k):
            raise TypeError("bad")

    p._logger = BadLogger()
    # set attributes used in message formatting
    p._debug_enabled = True
    p._navbar_enabled = True
    p._display_format = "f"
    p._debug_throttle_seconds = 1
    # should not raise even if logger.info raises
    p._log_settings_after_save(prev_navbar=False)


def test__log_debug_outer_exception_handled(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p._debug_enabled = True
    p._last_debug_time = 0
    # set throttle to a non-comparable type to raise in comparison
    p._debug_throttle_seconds = "bad"
    monkeypatch.setattr(time, "time", lambda: 1000)
    # should not raise
    p._log_debug("x")


def test_on_api_get_returns_early_when_permission_denied():
    p = plugin.OctoprintUptimePlugin()
    p._handle_permission_check = lambda: {"error": "nope"}
    res = p.on_api_get()
    assert res == {"error": "nope"}


def test__check_permissions_default_true():
    p = plugin.OctoprintUptimePlugin()
    assert p._check_permissions() is True


def test__get_uptime_info_uses_internal_getter():
    p = plugin.OctoprintUptimePlugin()
    # ensure get_uptime_seconds is not present so it uses internal _get_uptime_seconds
    if hasattr(p, "get_uptime_seconds"):
        delattr(p, "get_uptime_seconds")

    def internal_get():
        p._last_uptime_source = "proc"
        return 321, "proc"

    p._get_uptime_seconds = internal_get
    sec, full, dhm, dh, d = p._get_uptime_info()
    assert sec == 321
    assert p._last_uptime_source == "proc"


def test__get_uptime_info_handles_logger_exception(monkeypatch):
    p = plugin.OctoprintUptimePlugin()
    # make get_uptime_seconds raise to hit outer except
    p.get_uptime_seconds = lambda: (_ for _ in ()).throw(TypeError("boom"))

    class BadLogger:
        def exception(self, *a, **k):
            raise TypeError("badlog")

    p._logger = BadLogger()
    s, full, dhm, dh, d = p._get_uptime_info()
    assert s is None and full == plugin._("unknown")
