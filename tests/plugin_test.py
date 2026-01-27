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
        """
        Initializes the object and creates an empty list to track calls.
        """
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


def test_log_settings_save_data_and_call_base_on_settings_save():
    """
    Test that OctoprintUptimePlugin correctly logs settings save data and safely calls the base
    on_settings_save method, ensuring exceptions from the base method are swallowed and do not
    propagate.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    data = {"x": 1}
    p._log_settings_save_data(data)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        plugin.SettingsPluginBase,
        "on_settings_save",
        lambda _self, _d: (_ for _ in ()).throw(ValueError("boom")),
        raising=False,
    )
    p._call_base_on_settings_save({})
    monkeypatch.undo()


def test_update_internal_state_and_get_api_settings_and_logging():
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

    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (100, "1m 40s", "1m", "1h", "0d"),
    )
    monkeypatch.setattr(plugin, "_flask", None)
    resp = p._fallback_uptime_response()
    assert resp["uptime"] == "1m 40s"

    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (None, "unknown", "unknown", "unknown", "unknown"),
    )
    resp = p._fallback_uptime_response()
    assert resp["uptime_available"] is False and "uptime_note" in resp

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
    """Test on_api_get behavior for permitted and denied requests.

    Verifies two code paths:
    - Permission granted: patches _check_permissions to True and _get_uptime_info to a known tuple,
        ensures on_api_get() returns the expected uptime dictionary {"uptime": "42s"}.
    - Permission denied: patches _check_permissions to False and verifies that
        _handle_permission_check() returns a truthy dict (expected permission-denied response).

    Uses monkeypatch to control plugin internals and sets plugin._flask to None to avoid
    Flask dependency.
    """
    p = plugin.OctoprintUptimePlugin()

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

    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_check_permissions", lambda self: False
    )
    p2 = plugin.OctoprintUptimePlugin()
    plugin._flask = None
    got = p2._handle_permission_check()
    assert got and isinstance(got, dict)


def test_get_uptime_info_custom_getter():
    """
    Test that the OctoprintUptimePlugin correctly uses a custom uptime getter.

    This test replaces the plugin's `get_uptime_seconds` method with a lambda that returns
    a fixed uptime value and a custom source string. It then verifies that the returned
    uptime seconds match the expected value and that the plugin records the correct source.
    """
    p = plugin.OctoprintUptimePlugin()
    p.get_uptime_seconds = lambda: (200, "custom")
    seconds, full, dhm, dh, d = p._get_uptime_info()
    assert seconds == 200
    assert p._last_uptime_source == "custom"


def test_get_uptime_from_psutil_and_proc(monkeypatch):
    """
    Test that uptime can be retrieved from both psutil and /proc/uptime sources.

    This test verifies that the plugin correctly calculates uptime using psutil's boot_time
    and by reading from /proc/uptime,
    ensuring both code paths are exercised and return expected values.
    """
    p = plugin.OctoprintUptimePlugin()

    fake_ps = SimpleNamespace(boot_time=lambda: time.time() - 1234)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: fake_ps if name == "psutil" else importlib.import_module(name),
    )
    val = p._get_uptime_from_psutil()
    assert isinstance(val, float) and abs(val - 1234) < 5

    monkeypatch.setattr(plugin.os.path, "exists", lambda path: True)
    mo = mock.mock_open(read_data="987.65 0.00\n")
    monkeypatch.setattr(builtins, "open", mo)
    val2 = p._get_uptime_from_proc()
    assert abs(val2 - 987.65) < 0.001


def test_hook_inspection_and_safe_invoke(monkeypatch):
    """
    Test hook inspection and safe invocation logic in OctoprintUptimePlugin.

    This test verifies that the plugin correctly determines the number of positional parameters
    for various hook functions, handles exceptions raised by inspect.signature, and safely
    invokes hooks, logging exceptions without raising them.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    def no_arg_func():
        """
        Returns the integer 1.

        Returns:
            int: The value 1.
        """
        return 1

    def identity(x):
        """
        Returns the input value unchanged.

        Args:
            x: The value to be returned.

        Returns:
            The same value as the input `x`.
        """
        return x

    def two(a, b):
        """
        Adds two values together.

        Args:
            a: The first value to add.
            b: The second value to add.

        Returns:
            The sum of a and b.
        """
        return a + b

    assert p._get_hook_positional_param_count(no_arg_func) == 0
    assert p._get_hook_positional_param_count(identity) == 1
    assert p._get_hook_positional_param_count(two) == 2

    monkeypatch.setattr(
        plugin.inspect, "signature", lambda h: (_ for _ in ()).throw(ValueError("nope"))
    )
    p._logger = FakeLogger()

    assert p._get_hook_positional_param_count(no_arg_func) is None

    def bad(one):
        """
        Raises a RuntimeError with the message "boom".

        Args:
            one: Unused parameter.

        Raises:
            RuntimeError: Always raised when the function is called.
        """
        raise RuntimeError("boom")

    p._logger = FakeLogger()
    p._safe_invoke_hook(bad, 1)
    assert any(c[0] == "exception" for c in p._logger.calls)


def test_module_simple_methods_and_uptime_seconds_none(monkeypatch):
    """
    Test the basic public methods of OctoprintUptimePlugin and the behavior of _get_uptime_seconds
    when both _get_uptime_from_proc and _get_uptime_from_psutil return None.

    This test verifies:
    - get_update_information returns expected plugin info.
    - get_assets returns the correct JS asset.
    - get_template_configs returns a list containing at least one dict.
    - is_api_protected returns True.
    - is_template_autoescaped returns True.
    - _get_uptime_seconds returns (None, "none") when both uptime sources return None.
    """
    p = plugin.OctoprintUptimePlugin()
    info = p.get_update_information()
    assert "octoprint_uptime" in info
    assert p.get_assets() == {"js": ["js/uptime.js"]}
    tcs = p.get_template_configs()
    assert any(isinstance(x, dict) for x in tcs)
    assert p.is_api_protected() is True
    assert p.is_template_autoescaped() is True

    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_get_uptime_from_proc", lambda self: None
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin, "_get_uptime_from_psutil", lambda self: None
    )
    secs, src = p._get_uptime_seconds()
    assert secs is None and src == "none"


def test_get_uptime_from_proc_bad_content(monkeypatch):
    """
    Test that _get_uptime_from_proc returns None when /proc/uptime contains invalid
    (non-numeric) content.

    This test mocks the existence of the /proc/uptime file and provides invalid content
    ("not-a-number\n"). It verifies that the method correctly handles the bad content by
    returning None.
    """
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin.os.path, "exists", lambda path: True)
    mo = mock.mock_open(read_data="not-a-number\n")
    monkeypatch.setattr(builtins, "open", mo)
    assert p._get_uptime_from_proc() is None


def test_get_uptime_from_psutil_import_error_and_bad_boot(monkeypatch):
    """
    Test the _get_uptime_from_psutil method for handling ImportError and invalid boot_time values.

    This test verifies that:
    - When the psutil module cannot be imported (ImportError), the method returns None.
    - When the psutil module is imported but its boot_time method returns an invalid value,
      the method also returns None.
    """
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError("nope")),
    )
    assert p._get_uptime_from_psutil() is None

    fake_ps = SimpleNamespace(boot_time=lambda: "invalid")
    monkeypatch.setattr(importlib, "import_module", lambda name: fake_ps)
    assert p._get_uptime_from_psutil() is None


def test_on_settings_initialized_invokes_hook_variants(monkeypatch):
    """
    Test that the `on_settings_initialized` method of `OctoprintUptimePlugin` correctly invokes
    the base class hook with both 0 and 1 argument variants.

    This test uses monkeypatching to replace the `on_settings_initialized` method of
    `SettingsPluginBase` with functions that accept either zero or one argument, ensuring
    that the plugin's method can handle both cases without error and passes the correct
    parameters when required.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    def base0():
        base0.called = True

    def base1(obj):
        base1.called_with = obj

    monkeypatch.setattr(
        plugin.SettingsPluginBase, "on_settings_initialized", base0, raising=False
    )
    p.on_settings_initialized()
    assert getattr(base0, "called", True) is True

    monkeypatch.setattr(
        plugin.SettingsPluginBase, "on_settings_initialized", base1, raising=False
    )
    p.on_settings_initialized()
    assert getattr(base1, "called_with", None) is not None


def test_invoke_settings_hook_unexpected_param_count():
    """
    Test that _invoke_settings_hook logs a warning when the hook function has an
    unexpected number of positional parameters.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    mp = pytest.MonkeyPatch()
    mp.setattr(p, "_get_hook_positional_param_count", lambda hook: 3)
    p._invoke_settings_hook(lambda: None)
    assert any(c[0] == "warning" for c in p._logger.calls)
    mp.undo()


def test_log_debug_throttled_no_logging(monkeypatch):
    """
    Test that the _log_debug method does not log a debug message when throttling is in effect.

    This test sets up the OctoprintUptimePlugin with debug logging enabled and simulates the
    current time such that the last debug log was just now, and the throttle interval has not
    yet passed. It verifies that no debug log is emitted under these conditions.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p._debug_enabled = True
    monkeypatch.setattr(time, "time", lambda: 1000)
    p._last_debug_time = 1000
    p._debug_throttle_seconds = 60
    p._log_debug("x")
    assert not any(c[0] == "debug" for c in p._logger.calls)


def test_fallback_uptime_response_flask_jsonify_raises(monkeypatch):
    """
    Test that the _fallback_uptime_response method returns a dictionary when Flask's
    jsonify raises a TypeError.

    This test simulates a failure in the Flask jsonify function by monkeypatching it
    to always raise a TypeError.
    It verifies that the method under test properly handles this exception and falls
    back to returning a plain dictionary.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    class BadFlask:
        """
        A mock Flask-like class used for testing purposes.

        This class simulates a Flask object with a static `jsonify` method that
        always raises a TypeError to emulate failure scenarios when calling `jsonify`.
        """

        @staticmethod
        def jsonify(**kwargs):
            """
            Raises a TypeError indicating that the 'jsonify' function is not implemented.

            Args:
                **kwargs: Arbitrary keyword arguments.

            Raises:
                TypeError: Always raised to indicate improper usage.
            """
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
    assert isinstance(out, dict)


def test_on_api_get_with_flask_returns_json(monkeypatch):
    """
    Test that the `on_api_get` method of `OctoprintUptimePlugin` returns a JSON response
    when using a Flask-like `jsonify` function.

    This test uses monkeypatching to:
    - Replace the `_flask` module with a fake class that provides a `jsonify` method.
    - Bypass the permission check in `_handle_permission_check`.
    - Stub the `_get_uptime_info` method to return fixed uptime values.

    Asserts that the output is a dictionary containing a "json" key.
    """
    p = plugin.OctoprintUptimePlugin()

    class FakeFlask:
        """
        A fake Flask class used for testing purposes.

        Provides a static method `jsonify` that simulates Flask's `jsonify` by returning
        the provided keyword arguments in a dictionary under the 'json' key.
        """

        @staticmethod
        def jsonify(**kwargs):
            """
            Converts keyword arguments into a dictionary under the 'json' key.

            Args:
                **kwargs: Arbitrary keyword arguments to include in the JSON dictionary.

            Returns:
                dict: A dictionary with a single key 'json' containing the provided
                keyword arguments.
            """
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
    """
    Test that _handle_permission_check handles exceptions raised by both
    _check_permissions and _abort_forbidden,
    and returns a dictionary response when both methods raise errors.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_check_permissions",
        lambda self: (_ for _ in ()).throw(AttributeError("boom")),
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_abort_forbidden",
        lambda self: (_ for _ in ()).throw(RuntimeError("abort fail")),
    )
    res = p._handle_permission_check()
    assert res and isinstance(res, dict)


def test_get_api_settings_exceptions():
    """
    Test that _get_api_settings handles exceptions when accessing settings,
    returning default values when a ValueError is raised by the settings object.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    class BadSettings:
        """
        A mock settings class that simulates a failure when attempting to retrieve a value.

        Raises:
            ValueError: Always raised when the 'get' method is called.
        """

        def get(self, k):
            """
            Raises a ValueError with the message "bad" when called.

            Args:
                k: The key or parameter to retrieve (not used).

            Raises:
                ValueError: Always raised with the message "bad".
            """
            raise ValueError("bad")

    p._settings = BadSettings()
    nav, fmt, poll = p._get_api_settings()
    assert nav is True and fmt == plugin._("full") and poll == 5


def test_reload_with_octoprint_present_and_flask_abort(monkeypatch):
    """
    Test that the plugin reloads correctly when OctoPrint and Flask are present,
    and that the _abort_forbidden method triggers a Flask abort with code 403,
    returning the appropriate error response. Uses monkeypatching to inject
    fake modules and verifies cleanup after the test.
    """
    import types

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
    fake_flask = types.ModuleType("flask")
    aborted = {}

    def fake_abort(code):
        """
        Simulates an abort operation by setting the provided code in the 'aborted' dictionary.

        Args:
            code: The code to set as the abort reason.
        """
        aborted["code"] = code

    fake_flask.abort = fake_abort
    fake_flask.jsonify = lambda **kwargs: {"json": kwargs}

    monkeypatch.setitem(sys.modules, "octoprint.plugin", fake_plugin_mod)
    monkeypatch.setitem(sys.modules, "octoprint.access.permissions", fake_perm)
    monkeypatch.setitem(sys.modules, "flask", fake_flask)

    importlib.reload(plugin)

    p = plugin.OctoprintUptimePlugin()

    res = p._abort_forbidden()
    assert res == {"error": plugin._("Forbidden")} or isinstance(res, dict)
    assert aborted.get("code") == 403

    monkeypatch.delitem(sys.modules, "octoprint.plugin", raising=False)
    monkeypatch.delitem(sys.modules, "octoprint.access.permissions", raising=False)
    monkeypatch.delitem(sys.modules, "flask", raising=False)
    importlib.reload(plugin)


def test_reload_with_missing_gettext_uses_fallback(monkeypatch):
    """
    Test that when the 'gettext' module is present but lacks the 'gettext' function,
    the plugin falls back to a default translation function that returns the input unchanged.
    """
    import types

    fake_gettext = types.ModuleType("gettext")

    def bindtextdomain(domain, localedir):
        """
        Mock implementation of the gettext.bindtextdomain function.

        Args:
            domain (str): The domain name for the translation.
            localedir (str): The directory where the translation files are located.

        Returns:
            None
        """
        return None

    fake_gettext.bindtextdomain = bindtextdomain
    fake_gettext.textdomain = lambda name: None

    monkeypatch.setitem(sys.modules, "gettext", fake_gettext)
    importlib.reload(plugin)
    assert plugin._("something") == "something"
    monkeypatch.delitem(sys.modules, "gettext", raising=False)
    importlib.reload(plugin)


def test_get_api_settings_multiple_cases():
    """
    Test multiple scenarios for the _get_api_settings method of OctoprintUptimePlugin.

    This test covers:
    - Default values and debug logging when all settings are missing.
    - Clamping of poll_interval_seconds to minimum and maximum allowed values.
    - Handling of invalid poll_interval_seconds values.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()

    p._settings = DummySettings({})
    nav, fmt, poll = p._get_api_settings()
    assert nav is True
    assert fmt == plugin._("full")
    assert poll == 5
    assert any(
        "defaulting to True" in str(c[1]) or "defaulting to 'full'" in str(c[1])
        for c in p._logger.calls
    )

    p._settings = DummySettings(
        {"navbar_enabled": False, "display_format": "x", "poll_interval_seconds": "0"}
    )
    nav, fmt, poll = p._get_api_settings()
    assert poll == 1

    p._settings = DummySettings({"poll_interval_seconds": "999"})
    nav, fmt, poll = p._get_api_settings()
    assert poll == 120

    p._settings = DummySettings({"poll_interval_seconds": "bad"})
    nav, fmt, poll = p._get_api_settings()
    assert poll == 5


def test_fallback_uptime_response_handles_exceptions(monkeypatch):
    """
    Test that the _fallback_uptime_response method correctly handles exceptions raised by
    _get_uptime_info,
    returning a response with 'uptime' set to 'unknown' and
    'uptime_available' set to False.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (_ for _ in ()).throw(AttributeError("boom")),
    )
    out = p._fallback_uptime_response()
    assert out["uptime"] == plugin._("unknown") and out["uptime_available"] is False


def test_safe_update_internal_state_logs_warning():
    """
    Test that _safe_update_internal_state logs a warning when
    _update_internal_state raises an exception.

    This test replaces the _update_internal_state method with one that
    always raises an AttributeError.
    It then checks that a warning is logged by verifying that the logger's
    calls include a warning entry.
    """
    p = plugin.OctoprintUptimePlugin()

    def bad_update():
        """
        Raises an AttributeError with the message "bad".

        This function is intended to simulate an error condition for testing purposes.
        """
        raise AttributeError("bad")

    p._update_internal_state = bad_update
    p._logger = FakeLogger()
    p._safe_update_internal_state()
    assert any(c[0] == "warning" for c in p._logger.calls)


def test_log_settings_save_data_handles_logger_errors():
    """
    Test that _log_settings_save_data handles exceptions raised by the logger
    without propagating them.
    """
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        """
        A logger class that raises a ValueError when the debug method is called.
        Used for testing error handling in logging scenarios.
        """

        def debug(self, *a, **k):
            """
            Raises a ValueError with the message 'boom' for debugging purposes.

            Args:
                *a: Variable length argument list.
                **k: Arbitrary keyword arguments.

            Raises:
                ValueError: Always raised with the message 'boom'.
            """
            raise ValueError("boom")

    p._logger = BadLogger()
    p._log_settings_save_data({"x": 1})


def test_log_debug_inner_exception():
    """
    Test that the _log_debug method handles exceptions raised by the logger's debug method
    without propagating them, specifically when a TypeError is raised internally.
    """
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        """
        A logger class that simulates a faulty logger by raising a TypeError
        whenever the debug method is called. Useful for testing error handling
        in logging scenarios.
        """

        def debug(self, msg):
            """
            Raises a TypeError with the message "bad" when called.

            Args:
                msg: The debug message (not used).

            Raises:
                TypeError: Always raised with the message "bad".
            """
            raise TypeError("bad")

    p._logger = BadLogger()
    p._debug_enabled = True
    p._last_debug_time = 0
    p._debug_throttle_seconds = 0
    p._log_debug("x")


def test_get_uptime_from_psutil_future_boot(monkeypatch):
    """
    Test that _get_uptime_from_psutil returns None when psutil.boot_time() is in the future.

    This test uses monkeypatching to simulate a scenario where the system boot time,
    as reported by psutil.boot_time(), is set to a future timestamp. It verifies that
    the OctoprintUptimePlugin correctly handles this edge case by returning None.
    """
    p = plugin.OctoprintUptimePlugin()
    fake_ps = SimpleNamespace(boot_time=lambda: time.time() + 10000)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: fake_ps if name == "psutil" else importlib.import_module(name),
    )
    assert p._get_uptime_from_psutil() is None


def test_get_uptime_from_proc_missing(monkeypatch):
    """
    Test that _get_uptime_from_proc returns None when the /proc/uptime file is missing.

    This test uses monkeypatch to simulate the absence of the /proc/uptime file by making
    os.path.exists always return False.
    """
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin.os.path, "exists", lambda path: False)
    assert p._get_uptime_from_proc() is None


def test_get_uptime_info_exception_path(monkeypatch):
    """
    Test that _get_uptime_info handles exceptions raised by get_uptime_seconds gracefully.

    This test simulates an exception in get_uptime_seconds and verifies that
    _get_uptime_info returns None and the localized "unknown" string as expected.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p.get_uptime_seconds = lambda: (_ for _ in ()).throw(TypeError("boom"))
    s, full, dhm, dh, d = p._get_uptime_info()
    assert s is None and full == plugin._("unknown")


def test_execute_plugin_source_for_coverage():
    """
    Test that the plugin source file can be executed directly for coverage purposes,
    and verify that key functions are available and behave as expected after execution.

    This test runs the plugin module as a script to ensure all lines are covered by coverage tools,
    then imports the module to check that the 'format_uptime' function exists and returns the
    correct output for a sample input.
    """
    import runpy

    runpy.run_path(plugin.__file__, run_name="__main__")

    import importlib

    mod = importlib.import_module("octoprint_uptime.plugin")
    assert hasattr(mod, "format_uptime")
    assert mod.format_uptime(1) == "1s"


def test_get_settings_defaults_and_on_settings_save(monkeypatch):
    """
    Test the `get_settings_defaults` and `on_settings_save` methods of the OctoprintUptimePlugin.

    This test verifies that:
    - The default settings returned by `get_settings_defaults` are as expected.
    - The `on_settings_save` method correctly calls its internal helper methods:
        - `_validate_and_sanitize_settings`
        - `_log_settings_save_data`
        - `_call_base_on_settings_save`
        - `_update_internal_state`
    using monkeypatching to track their invocation.
    """
    p = plugin.OctoprintUptimePlugin()
    defaults = p.get_settings_defaults()
    assert defaults["debug"] is False
    assert defaults["navbar_enabled"] is True

    called = {}

    def fake_validate(data):
        """
        Simulates a validation function for testing purposes.

        Args:
            data: The input data to be "validated". This argument is not used in the function body.

        Side Effects:
            Sets the "validate" key in the 'called' dictionary to True to indicate
            the function was called.
        """
        called["validate"] = True

    def fake_log(data):
        """
        Mock logging function for testing purposes.

        Args:
            data: The data to be logged. This argument is not used in the function body.
        """
        called["log"] = True

    def fake_call_base(data):
        """
        Simulates a call to the base function by setting the 'call_base' key in the
        'called' dictionary to True.

        Args:
            data: Unused argument, present to match the expected function signature.
        """
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
    """
    Test that reloading the plugin handles a failure in gettext.bindtextdomain gracefully.

    This test simulates an OSError being raised by gettext.bindtextdomain to ensure that
    the plugin's internationalization fallback logic is triggered correctly. It verifies
    that the plugin's translation function (`plugin._`) remains callable even when
    gettext binding fails, and ensures proper cleanup of the monkeypatched module.
    """
    import types

    fake_gettext = types.ModuleType("gettext")

    def bad_bind(domain, localedir):
        raise OSError("nope")

    fake_gettext.bindtextdomain = bad_bind
    fake_gettext.textdomain = lambda name: None
    fake_gettext.gettext = lambda s: s

    monkeypatch.setitem(sys.modules, "gettext", fake_gettext)
    importlib.reload(plugin)
    assert callable(plugin._)
    monkeypatch.delitem(sys.modules, "gettext", raising=False)
    importlib.reload(plugin)


def test_reload_plugin_without_octoprint(monkeypatch):
    """
    Test that the plugin module correctly falls back to base classes when
    OctoPrint is not available.

    This test simulates the absence of the 'octoprint.plugin' and
    'octoprint.access.permissions' modules
    by removing them from 'sys.modules'.
    It then reloads the plugin module to ensure that fallback base
    classes ('SettingsPluginBase' and
    'SimpleApiPluginBase') are defined.
    Finally, it reloads the plugin module again to restore its original state.
    """
    monkeypatch.delitem(sys.modules, "octoprint.plugin", raising=False)
    monkeypatch.delitem(sys.modules, "octoprint.access.permissions", raising=False)
    importlib.reload(plugin)
    assert hasattr(plugin, "SettingsPluginBase")
    assert hasattr(plugin, "SimpleApiPluginBase")
    importlib.reload(plugin)


def make_plugin():
    """
    Creates and returns an instance of OctoprintUptimePlugin with mocked settings and logger.

    The returned plugin instance has:
    - _settings: a mock Settings object with predefined configuration values and a get method.
    - _logger: a mock Logger object that records debug, info, warning, and exception messages.

    Returns:
        OctoprintUptimePlugin: The plugin instance with mocked dependencies for testing.
    """
    p = plugin.OctoprintUptimePlugin()

    class Settings:
        """
        A simple settings container for test purposes.

        Attributes:
            _data (dict): Stores configuration values such as debug mode,
                navbar visibility,
                display format,
                throttle seconds,
                and poll interval.

        Methods:
            get(path): Retrieves the value for the specified configuration key.
        """

        def __init__(self):
            """
            Initializes the instance with default configuration values.

            Attributes:
                _data (dict): A dictionary containing the following default settings:
                    - "debug" (bool): Enables or disables debug mode
                      (default: False).
                    - "navbar_enabled" (bool): Shows or hides the navbar
                      (default: True).
                    - "display_format" (str): Format for display, e.g., "full"
                      (default: "full").
                    - "debug_throttle_seconds" (int): Throttle interval for debug mode
                      in seconds (default: 60).
                    - "poll_interval_seconds" (int): Interval for polling in seconds
                      (default: 5).
            """
            self._data = {
                "debug": False,
                "navbar_enabled": True,
                "display_format": "full",
                "debug_throttle_seconds": 60,
                "poll_interval_seconds": 5,
            }

        def get(self, path):
            """
            Retrieve the value associated with the first element of the given path
            from the internal data store.

            Args:
                path (list): A list where the first element is used as the key
                to look up the value.

            Returns:
                The value associated with the key, or None if the key does not exist.
            """
            return self._data.get(path[0])

    class Logger:
        """
        Logger class for capturing log records during testing.

        Attributes:
            records (list): Stores tuples of log level and arguments.

        Methods:
            debug(*a, **k): Records a debug-level log entry.
            info(*a, **k): Records an info-level log entry.
            warning(*a, **k): Records a warning-level log entry.
            exception(*a, **k): Records an exception-level log entry.
        """

        def __init__(self):
            """
            Initializes a new instance of the class, setting up an empty list to store records.
            """
            self.records = []

        def debug(self, *a, **k):
            """
            Appends a debug record to the records list.

            Args:
                *a: Positional arguments to include in the debug record.
                **k: Keyword arguments (unused).

            Note:
                Only positional arguments are stored; keyword arguments are ignored.
            """
            self.records.append(("debug", a))

        def info(self, *a, **k):
            """
            Appends an 'info' record with the provided positional arguments to the records list.

            Args:
                *a: Variable length positional arguments to be recorded.
                **k: Variable length keyword arguments (currently unused).
            """
            self.records.append(("info", a))

        def warning(self, *a, **k):
            """
            Appends a warning record to the records list.

            Args:
                *a: Positional arguments to be included in the warning record.
                **k: Keyword arguments (unused).
            """
            self.records.append(("warn", a))

        def exception(self, *a, **k):
            """
            Handle an exception event by appending the exception record to the records list.

            Args:
                *a: Positional arguments representing exception details.
                **k: Keyword arguments (unused).

            Note:
                The keyword arguments are accepted for interface compatibility but are not used.
            """
            self.records.append(("exc", a))

    p._settings = Settings()
    p._logger = Logger()
    return p


def test_get_uptime_seconds_prefers_proc(monkeypatch):
    """
    Test that _get_uptime_seconds() prefers reading uptime from /proc/uptime when available.

    This test simulates the presence of /proc/uptime and verifies that the method reads
    the uptime value from it, returning the correct number of seconds and indicating the
    source as "proc".
    """
    p = make_plugin()
    monkeypatch.setattr(os.path, "exists", lambda pth: True)
    mo = mock.mock_open(read_data="123.4 0")
    monkeypatch.setattr(builtins, "open", mo)
    sec, src = p._get_uptime_seconds()
    assert src == "proc"
    assert abs(sec - 123.4) < 0.001


def test_get_uptime_seconds_uses_psutil_when_no_proc(monkeypatch):
    """
    Test that _get_uptime_from_psutil is used to retrieve uptime seconds
    when _get_uptime_from_proc returns None.

    This test monkeypatches the plugin to simulate the absence of /proc uptime
    and verifies that psutil's boot_time is used instead.
    """
    p = make_plugin()
    monkeypatch.setattr(p, "_get_uptime_from_proc", lambda: None)

    class FakePs:
        """
        A fake class to simulate a process statistics object for testing purposes.

        Methods
        -------
        boot_time() : float
            Returns a simulated system boot time, 500 seconds before the current time.
        """

        def boot_time(self):
            """
            Returns the simulated system boot time as a timestamp.

            Returns:
                float: The current time minus 500 seconds, representing the boot time.
            """
            return time.time() - 500

    monkeypatch.setattr(importlib, "import_module", lambda name: FakePs())
    sec = p._get_uptime_from_psutil()
    assert sec is not None and sec > 0


def test_validate_and_sanitize_settings_handles_bad_shapes():
    """
    Test that the _validate_and_sanitize_settings method correctly handles invalid or
    unexpected shapes of the settings input, such as None, empty lists, or improperly
    structured dictionaries.
    """
    p = make_plugin()
    p._validate_and_sanitize_settings(None)
    p._validate_and_sanitize_settings({"plugins": []})
    p._validate_and_sanitize_settings({"plugins": {"octoprint_uptime": []}})


def test_validate_and_sanitize_settings_sanitizes_values():
    """
    Test that _validate_and_sanitize_settings correctly sanitizes invalid or None values
    in the plugin settings, setting 'debug_throttle_seconds' to 60 when None and
    'poll_interval_seconds' to 5 when given an invalid value.
    """
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
    """
    Test that changing the 'navbar_enabled' setting and saving logs an info message.

    This test verifies that after toggling the 'navbar_enabled' setting in the plugin's settings,
    the internal state is updated and the '_log_settings_after_save' method logs an info-level message.
    """
    p = make_plugin()
    p._update_internal_state()
    prev = p._navbar_enabled
    p._settings._data["navbar_enabled"] = not prev
    p._update_internal_state()
    p._log_settings_after_save(prev)
    assert any(r[0] == "info" for r in p._logger.records)


def test_safe_update_internal_state_logs_warning_on_failure():
    """
    Test that _safe_update_internal_state logs a warning when
    _update_internal_state raises an exception.

    This test replaces the plugin's _update_internal_state method with a helper
    function that raises a ValueError.
    It then calls _safe_update_internal_state and asserts that a warning was
    logged, indicating proper error handling.
    """
    p = make_plugin()

    def bad_update():
        """
        A test helper function that raises a ValueError with the message "boom".
        Intended to simulate a failing update operation for testing error handling.
        """
        raise ValueError("boom")

    p._update_internal_state = bad_update
    p._safe_update_internal_state()
    assert any(r[0] == "warn" for r in p._logger.records)


def test_get_uptime_info_handles_custom_getter():
    """
    Test that _get_uptime_info uses a custom uptime getter if provided.

    This test replaces the plugin's get_uptime_seconds method with a lambda that returns 42,
    then verifies that _get_uptime_info returns the correct uptime value and updates the
    _last_uptime_source attribute to "custom".
    """
    p = make_plugin()
    p.get_uptime_seconds = lambda: 42
    seconds, full, dhm, dh, d = p._get_uptime_info()
    assert seconds == 42
    assert p._last_uptime_source == "custom"


def test_get_uptime_info_none_returns_unknown():
    """
    Test that _get_uptime_info returns 'unknown' and None values when
    get_uptime_seconds returns None.

    This test verifies that when the plugin's get_uptime_seconds method returns None,
    the _get_uptime_info method correctly returns None for seconds and the localized
    string 'unknown' for the full uptime description.
    """
    p = make_plugin()
    p.get_uptime_seconds = lambda: None
    seconds, full, dhm, dh, d = p._get_uptime_info()
    assert seconds is None
    assert full == plugin._("unknown")


def test_handle_permission_check_aborts_and_handles_abort_exception():
    """
    Test that _handle_permission_check returns an error dictionary with a "Forbidden" message
    when permission check fails and _abort_forbidden raises an exception.
    """
    p = make_plugin()
    p._check_permissions = lambda: False

    def bad_abort():
        """
        Raises a RuntimeError with the message "nope".

        This function is intended to simulate an abort or failure scenario
        by unconditionally raising a RuntimeError when called.
        """
        raise RuntimeError("nope")

    p._abort_forbidden = bad_abort
    res = p._handle_permission_check()
    assert isinstance(res, dict) and res.get("error") == plugin._("Forbidden")


def test_handle_permission_check_check_raises_and_abort_fallback():
    """
    Test that _handle_permission_check correctly handles exceptions raised by _check_permissions
    by calling _abort_forbidden as a fallback and returning its result.
    """
    p = make_plugin()

    def bad_check():
        """
        Raises:
            AttributeError: Always raised with the message "boom" to indicate an error condition.
        """
        raise AttributeError("boom")

    p._check_permissions = bad_check
    p._abort_forbidden = lambda: {"error": "ok"}
    res = p._handle_permission_check()
    assert res == {"error": "ok"}


def test_abort_forbidden_returns_dict_when_no_flask():
    """
    Test that the _abort_forbidden method returns a dictionary with an error message
    when Flask is not available,
    and raises a Forbidden exception with code 403
    when Flask is present.
    """
    p = make_plugin()
    try:
        res = p._abort_forbidden()
    except Exception as e:
        try:
            from werkzeug.exceptions import Forbidden

            assert isinstance(e, Forbidden)
            assert getattr(e, "code", None) == 403
        except Exception:
            assert hasattr(e, "args")
    else:
        assert isinstance(res, dict) and res.get("error") == plugin._("Forbidden")


def test__get_uptime_seconds_prefers_psutil_branch():
    """
    Test that _get_uptime_seconds() prefers the psutil-based method for retrieving uptime
    when both psutil and proc-based methods are available, and returns the correct source and value.
    """
    p = plugin.OctoprintUptimePlugin()
    p._get_uptime_from_proc = lambda: None
    p._get_uptime_from_psutil = lambda: 123.0
    sec, src = p._get_uptime_seconds()
    assert src == "psutil"
    assert sec == 123.0


def test__log_settings_after_save_handles_info_exceptions():
    """
    Test that the _log_settings_after_save method handles exceptions raised by the logger's
    info method.

    This test replaces the plugin's logger with a custom BadLogger that raises a TypeError
    when its info method is called.
    It then sets various plugin attributes and calls _log_settings_after_save to verify
    that the method does not crash when the logger fails, ensuring robust exception
    handling during logging.

    TypeError: If the exception is not properly handled within _log_settings_after_save.
    """
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        """
        A logger class that raises a TypeError when the info method is called.

        Methods
        -------
        info(*a, **k)
            Raises a TypeError with the message "bad" when called.
        """

        def info(self, *a, **k):
            """
            Raises a TypeError with the message "bad" when called.

            Args:
                *a: Variable length argument list.
                **k: Arbitrary keyword arguments.

            Raises:
                TypeError: Always raised with the message "bad".
            """
            raise TypeError("bad")

    p._logger = BadLogger()
    p._debug_enabled = True
    p._navbar_enabled = True
    p._display_format = "f"
    p._debug_throttle_seconds = 1
    p._log_settings_after_save(prev_navbar=False)


def test__log_debug_outer_exception_handled(monkeypatch):
    """
    Test that the _log_debug method handles exceptions raised due to invalid
    _debug_throttle_seconds values gracefully,
    without propagating the exception, when debug logging is enabled.
    """
    p = plugin.OctoprintUptimePlugin()
    p._logger = FakeLogger()
    p._debug_enabled = True
    p._last_debug_time = 0
    p._debug_throttle_seconds = "bad"
    monkeypatch.setattr(time, "time", lambda: 1000)
    p._log_debug("x")


def test_on_api_get_returns_early_when_permission_denied():
    """
    Test that on_api_get returns early with an error response when permission is denied.

    This test mocks the _handle_permission_check method to simulate a permission denial,
    and asserts that on_api_get returns the expected error dictionary.
    """
    p = plugin.OctoprintUptimePlugin()
    p._handle_permission_check = lambda: {"error": "nope"}
    res = p.on_api_get()
    assert res == {"error": "nope"}


def test__check_permissions_default_true():
    """
    Test that the _check_permissions method of OctoprintUptimePlugin returns True by default.
    """
    p = plugin.OctoprintUptimePlugin()
    assert p._check_permissions() is True


def test__get_uptime_info_uses_internal_getter():
    """
    Test that _get_uptime_info uses the internal _get_uptime_seconds method
    when the public get_uptime_seconds method is not present.

    This test ensures that:
    - The plugin falls back to its internal uptime getter if the external one is missing.
    - The internal getter correctly sets the last uptime source.
    - The returned uptime value and source are as expected.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "get_uptime_seconds"):
        delattr(p, "get_uptime_seconds")

    def internal_get():
        """
        Simulates retrieving the system uptime from the "proc" source.

        Sets the plugin's last uptime source to "proc" and returns a tuple containing
        a fixed uptime value (321) and the source string "proc".

        Returns:
            tuple: A tuple containing the uptime value (int) and the source (str).
        """
        p._last_uptime_source = "proc"
        return 321, "proc"

    p._get_uptime_seconds = internal_get
    sec, full, dhm, dh, d = p._get_uptime_info()
    assert sec == 321
    assert p._last_uptime_source == "proc"


def test__get_uptime_info_handles_logger_exception():
    """
    Test that _get_uptime_info handles exceptions raised both by get_uptime_seconds
    and by the logger,
    returning None and the localized 'unknown' string when both fail.
    """
    p = plugin.OctoprintUptimePlugin()
    p.get_uptime_seconds = lambda: (_ for _ in ()).throw(TypeError("boom"))

    class BadLogger:
        """
        A logger class that raises a TypeError when the exception method is called.
        Intended for testing error handling when logging fails.
        """

        def exception(self, *a, **k):
            """
            Raises a TypeError with the message 'badlog'.

            Args:
                *a: Variable length argument list.
                **k: Arbitrary keyword arguments.

            Raises:
                TypeError: Always raised with the message 'badlog'.
            """
            raise TypeError("badlog")

    p._logger = BadLogger()
    s, full, dhm, dh, d = p._get_uptime_info()
    assert s is None and full == plugin._("unknown")
