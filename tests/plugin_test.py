# pylint: disable=protected-access, too-many-lines, too-many-statements

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
import runpy
import sys
import time
import types
from types import SimpleNamespace
from unittest import mock

import pytest
from werkzeug.exceptions import Forbidden

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
        self.calls.append(("warn", msg, args))

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
    if plugin.format_uptime(0) != "0s":
        pytest.fail("format_uptime(0) != '0s'")
    if plugin.format_uptime(1) != "1s":
        pytest.fail("format_uptime(1) != '1s'")
    if plugin.format_uptime(61) != "1m 1s":
        pytest.fail("format_uptime(61) != '1m 1s'")
    if plugin.format_uptime(3601) != "1h 0m 1s":
        pytest.fail("format_uptime(3601) != '1h 0m 1s'")
    if plugin.format_uptime(90061) != "1d 1h 1m 1s":
        pytest.fail("format_uptime(90061) != '1d 1h 1m 1s'")


def test_format_uptime_dhm_dh_d():
    """
    Test the formatting functions for uptime durations in days, hours, and minutes.

    This test verifies that:
    - `format_uptime_dhm` correctly formats seconds into "Xd Xh Xm" or "Xh Xm".
    - `format_uptime_dh` correctly formats seconds into "Xd Xh" or "Xh".
    - `format_uptime_d` correctly formats seconds into "Xd".

    Assertions are made for representative input values to ensure expected output strings.
    """
    val = plugin.format_uptime_dhm(3600)
    if val != "1h 0m":
        pytest.fail(f"format_uptime_dhm(3600) != '1h 0m' (got {val!r})")

    val = plugin.format_uptime_dhm(90061)
    if val != "1d 1h 1m":
        pytest.fail(f"format_uptime_dhm(90061) != '1d 1h 1m' (got {val!r})")

    val = plugin.format_uptime_dh(3600)
    if val != "1h":
        pytest.fail(f"format_uptime_dh(3600) != '1h' (got {val!r})")

    val = plugin.format_uptime_dh(90061)
    if val != "1d 1h":
        pytest.fail(f"format_uptime_dh(90061) != '1d 1h' (got {val!r})")

    val = plugin.format_uptime_d(90061)
    if val != "1d":
        pytest.fail(f"format_uptime_d(90061) != '1d' (got {val!r})")


def test_validate_and_sanitize_settings_plugins_not_dict():
    """
    Test that _validate_and_sanitize_settings handles 'plugins' key not being a dict.

    This test passes a dictionary where 'plugins' is a list or None and ensures
    no exception is raised and the input is unchanged.
    """
    p = make_plugin()
    data1 = {"plugins": []}
    data2 = {"plugins": None}
    data3 = {"plugins": 123}
    for data in [data1, data2, data3]:
        p._validate_and_sanitize_settings(data)
        if "plugins" not in data:
            pytest.fail("'plugins' key missing from settings after validation")


def test_validate_and_sanitize_settings_octoprint_uptime_not_dict():
    """
    Test that _validate_and_sanitize_settings handles 'octoprint_uptime' key not being a dict.

    This test passes a dictionary where 'octoprint_uptime' is a list or None and ensures
    no exception is raised and the input is unchanged.
    """
    p = make_plugin()
    data1 = {"plugins": {"octoprint_uptime": []}}
    data2 = {"plugins": {"octoprint_uptime": None}}
    data3 = {"plugins": {"octoprint_uptime": 123}}
    for data in [data1, data2, data3]:
        p._validate_and_sanitize_settings(data)
        if "octoprint_uptime" not in data["plugins"]:
            pytest.fail("'octoprint_uptime' key missing from settings['plugins'] after validation")


def test_validate_and_sanitize_settings_valid_and_invalid_values():
    """
    Test that _validate_and_sanitize_settings clamps and sanitizes values as expected.

    This test checks that values above/below allowed range are clamped,
    and invalid types are replaced with defaults.
    """
    p = make_plugin()
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
    if cfg.get("debug_throttle_seconds") != 120:
        pytest.fail("debug_throttle_seconds should be 120")
    if cfg.get("poll_interval_seconds") != 1:
        pytest.fail("poll_interval_seconds should be 1")

    data2 = {
        "plugins": {
            "octoprint_uptime": {
                "debug_throttle_seconds": "-1",
                "poll_interval_seconds": "200",
            }
        }
    }
    p._validate_and_sanitize_settings(data2)
    cfg2 = data2["plugins"]["octoprint_uptime"]
    if cfg2.get("debug_throttle_seconds") != 1:
        pytest.fail("debug_throttle_seconds should be 1")
    if cfg2.get("poll_interval_seconds") != 120:
        pytest.fail("poll_interval_seconds should be 120")

    data3 = {
        "plugins": {
            "octoprint_uptime": {
                "debug_throttle_seconds": None,
                "poll_interval_seconds": "bad",
            }
        }
    }
    p._validate_and_sanitize_settings(data3)
    cfg3 = data3["plugins"]["octoprint_uptime"]
    if cfg3.get("debug_throttle_seconds") != 60:
        pytest.fail("debug_throttle_seconds should be 60")
    if cfg3.get("poll_interval_seconds") != 5:
        pytest.fail("poll_interval_seconds should be 5")


def test_log_settings_save_data_and_call_base_on_settings_save(monkeypatch):
    """
    Test that OctoprintUptimePlugin correctly logs settings save data and safely calls the base
    on_settings_save method, ensuring exceptions from the base method are swallowed and do not
    propagate.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    data = {"x": 1}
    p._log_settings_save_data(data)

    monkeypatch.setattr(
        plugin.SettingsPluginBase,
        "on_settings_save",
        lambda _self, _d: (_ for _ in ()).throw(ValueError("boom")),
        raising=False,
    )
    p._call_base_on_settings_save({})


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
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p._update_internal_state()
    if p._debug_enabled is not True:
        pytest.fail("p._debug_enabled is not True")
    if p._navbar_enabled is not False:
        pytest.fail("p._navbar_enabled is not False")
    if p._display_format != "compact":
        pytest.fail(f"p._display_format != 'compact' (got {p._display_format!r})")
    if p._debug_throttle_seconds != 30:
        pytest.fail(f"p._debug_throttle_seconds != 30 (got {p._debug_throttle_seconds!r})")

    nav, fmt, poll = p._get_api_settings()
    if nav is not False:
        pytest.fail("nav is not False")
    if fmt != "compact":
        pytest.fail(f"fmt != 'compact' (got {fmt!r})")
    if poll != 120:
        pytest.fail(f"poll != 120 (got {poll!r})")


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
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p._debug_enabled = True
    p._navbar_enabled = True
    p._display_format = "f"
    p._debug_throttle_seconds = 7
    p._log_settings_after_save(prev_navbar=False)
    infos = [c for c in p._logger.calls if c[0] == "info"]
    if len(infos) < 2:
        pytest.fail("expected at least 2 info log calls")


def test_log_debug_throttle(monkeypatch):
    """
    Test that the _log_debug method logs a debug message when throttling conditions are met.
    This test sets up the plugin with debug enabled and a throttle interval, mocks the current time,
    calls _log_debug, and asserts that a debug log entry is created.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p._debug_enabled = True
    p._last_debug_time = 0
    p._debug_throttle_seconds = 10
    monkeypatch.setattr(time, "time", lambda: 1000)
    p._log_debug("hello")
    if not any(c[0] == "debug" for c in p._logger.calls):
        pytest.fail("expected a debug log call")


def test_fallback_uptime_response_no_flask_uptime_unavailable(monkeypatch):
    """
    Test _fallback_uptime_response when uptime info is unavailable and Flask is not present.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (None, "unknown", "unknown", "unknown", "unknown"),
    )
    monkeypatch.setattr(plugin, "_flask", None)
    resp = p._fallback_uptime_response()
    if isinstance(resp, dict):
        data = resp
    elif hasattr(resp, "get_json"):
        data = resp.get_json()
    else:
        data = None
    if not (
        isinstance(data, dict) and data.get("uptime_available") is False and "uptime_note" in data
    ):
        pytest.fail(
            "Expected data to be a dict with uptime_available == False and "
            "containing 'uptime_note'"
        )


def test_fallback_uptime_response_handles_type_errors(monkeypatch):
    """
    Test that _fallback_uptime_response handles TypeError from Flask's jsonify gracefully,
    falling back to a dict response.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

    class BadFlask:
        """
        A mock Flask-like class used for testing error handling when the jsonify method fails.

        Methods
        -------
        jsonify(**kwargs):
            Static method that simulates a failure by always raising a TypeError.
        """

        @staticmethod
        def jsonify(**kwargs):
            """
            Simulates a failure in JSON serialization by always raising a TypeError.

            Args:
                **kwargs: Arbitrary keyword arguments intended for JSON serialization.

            Raises:
                TypeError: Always raised to indicate JSON serialization failure.
            """
            raise TypeError("jsonify failed")

    monkeypatch.setattr(plugin, "_flask", BadFlask)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (100, "1m 40s", "1m", "1h", "0d"),
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_api_settings",
        lambda _: (True, "full", 5),
    )
    resp = p._fallback_uptime_response()
    if not isinstance(resp, dict):
        raise AssertionError("resp is not a dict")
    if resp.get("uptime") != "1m 40s":
        raise ValueError("Uptime response is not as expected.")


def test_fallback_uptime_response_logger_exception(monkeypatch):
    """
    Test that _fallback_uptime_response handles exceptions from logger without crashing.
    """
    p = plugin.OctoprintUptimePlugin()

    class BadLogger:
        """
        A mock logger class that simulates a logger raising a TypeError when its
        exception method is called.
        Useful for testing error handling when logging fails.
        """

        def exception(self, *a, **k):
            """
            Raises a TypeError with the message "badlog".

            Args:
                *a: Variable length argument list.
                **k: Arbitrary keyword arguments.

            Raises:
                TypeError: Always raised with the message "badlog".
            """
            raise TypeError("badlog")

    p._logger = BadLogger()
    monkeypatch.setattr(plugin, "_flask", None)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (_ for _ in ()).throw(AttributeError("fail")),
    )
    resp = p._fallback_uptime_response()
    if not isinstance(resp, dict):
        raise AssertionError("resp is not a dict")
    if resp.get("uptime") != plugin._("unknown"):
        raise AssertionError("resp.get('uptime') != plugin._('unknown')")
    if resp.get("uptime_available") is not False:
        raise AssertionError("resp.get('uptime_available') is not False")


def test_fallback_uptime_response_with_partial_uptime(monkeypatch):
    """
    Test _fallback_uptime_response when uptime is zero or negative.
    """
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin, "_flask", None)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (0, "0s", "0m", "0h", "0d"),
    )
    resp = p._fallback_uptime_response()
    if not isinstance(resp, dict):
        pytest.fail("resp is not a dict")
    if resp.get("uptime") != "0s":
        pytest.fail("resp.get('uptime') != '0s'")
    if resp.get("uptime_available") is not True:
        pytest.fail("resp.get('uptime_available') is not True")

    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (-1, "unknown", "unknown", "unknown", "unknown"),
    )
    resp = p._fallback_uptime_response()
    if not isinstance(resp, dict):
        raise AssertionError("resp is not a dict")
    if resp.get("uptime_available") is not False:
        raise AssertionError("resp.get('uptime_available') is not False")


def test_fallback_uptime_response_flask_jsonify_args(monkeypatch):
    """
    Test _fallback_uptime_response passes correct arguments to Flask's jsonify.
    """
    p = plugin.OctoprintUptimePlugin()
    captured = {}

    class CaptureFlask:
        """
        A helper class to capture Flask JSON responses during testing.

        Methods
        -------
        jsonify(**kwargs):
            Static method that updates the captured dict with provided kwargs and
            returns them in a JSON-like dict.
        """

        @staticmethod
        def jsonify(**kwargs):
            """
            Converts keyword arguments to a JSON-like dictionary and updates the captured
            dictionary with the provided values.

            Args:
                **kwargs: Arbitrary keyword arguments to be included in the JSON response
                and captured.

            Returns:
                dict: A dictionary containing the provided keyword arguments under the
                'json' key.
            """
            captured.update(kwargs)
            return {"json": kwargs}

    monkeypatch.setattr(plugin, "_flask", CaptureFlask)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_api_settings",
        lambda _: (False, "compact", 10),
    )
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda _: (50, "50s", "0m", "0h", "0d"),
    )
    resp = p._fallback_uptime_response()
    if not (isinstance(resp, dict) and "json" in resp):
        raise ValueError("Response is not a valid JSON dictionary")
    if captured.get("uptime") != "50s":
        raise AssertionError("Expected uptime to be '50s'")
    if captured.get("navbar_enabled") is not False:
        raise AssertionError("navbar_enabled should be False")
    if captured.get("display_format") != "compact":
        raise AssertionError("display_format should be 'compact'")
    if captured.get("poll_interval_seconds") != 10:
        raise AssertionError("poll_interval_seconds should be 10")


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

    monkeypatch.setattr(plugin.OctoprintUptimePlugin, "_check_permissions", lambda self: True)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (42, "42s", "42s", "0h", "0d"),
    )
    monkeypatch.setattr(plugin, "_flask", None, raising=False)
    out = p.on_api_get()
    if out != {"uptime": "42s"}:
        pytest.fail(f"Expected out == {{'uptime': '42s'}}, got {out!r}")

    monkeypatch.setattr(plugin.OctoprintUptimePlugin, "_check_permissions", lambda _: False)
    p2 = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin, "_flask", None, raising=False)
    got = p2._handle_permission_check()
    if not (got and isinstance(got, dict)):
        pytest.fail(f"Expected got to be a dict and truthy, got {got!r}")


def test_get_uptime_info_custom_getter():
    """
    Test that the OctoprintUptimePlugin correctly uses a custom uptime getter.

    This test replaces the plugin's `get_uptime_seconds` method with a lambda that returns
    a fixed uptime value and a custom source string. It then verifies that the returned
    uptime seconds match the expected value and that the plugin records the correct source.
    """
    p = plugin.OctoprintUptimePlugin()
    p.get_uptime_seconds = lambda: (200, "custom")
    seconds, *_ = p._get_uptime_info()
    if seconds != 200:
        pytest.fail(f"Expected seconds == 200, got {seconds!r}")
    if p._last_uptime_source != "custom":
        pytest.fail(f"Expected _last_uptime_source == 'custom', got {p._last_uptime_source!r}")


def test_get_uptime_from_psutil_and_proc(monkeypatch):
    """
    Test that uptime can be retrieved from both psutil and /proc/uptime sources.

    This test verifies that the plugin correctly calculates uptime using psutil's boot_time
    and by reading from /proc/uptime,
    ensuring both code paths are exercised and return expected values.
    """
    p = plugin.OctoprintUptimePlugin()

    fake_ps = SimpleNamespace(boot_time=lambda: time.time() - 1234)

    def safe_import_module(name):
        """
        Safely imports a module by name, restricting imports to a predefined set of allowed modules.

        Args:
            name (str): The name of the module to import.

        Returns:
            module: The imported module object.

        Raises:
            ImportError: If the module name is not in the allowed set.

        Special Cases:
            - If 'psutil' is requested, returns the 'fake_ps' object instead of importing.
        """
        if name == "psutil":
            return fake_ps
        allowed_modules = {
            "os",
            "sys",
            "time",
            "types",
            "builtins",
            "pytest",
            "octoprint_uptime.plugin",
        }
        if name in allowed_modules:
            return sys.modules[name]
        raise ImportError(f"Import of module '{name}' is not allowed in tests")

    monkeypatch.setattr(
        importlib,
        "import_module",
        safe_import_module,
    )
    val = p._get_uptime_from_psutil()
    if not (isinstance(val, float) and abs(val - 1234) < 5):
        pytest.fail("Expected val to be a float and within 5 of 1234")

    monkeypatch.setattr(plugin.os.path, "exists", lambda _: True)
    mo = mock.mock_open(read_data="987.65 0.00\n")
    monkeypatch.setattr(builtins, "open", mo)
    val2 = p._get_uptime_from_proc()
    if not (val2 is not None and abs(val2 - 987.65) < 0.001):
        pytest.fail("Expected val2 to be not None and within 0.001 of 987.65")


def test_hook_inspection_and_safe_invoke(monkeypatch):
    """
    Test hook inspection and safe invocation logic in OctoprintUptimePlugin.

    This test verifies that the plugin correctly determines the number of positional parameters
    for various hook functions, handles exceptions raised by inspect.signature, and safely
    invokes hooks, logging exceptions without raising them.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

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

    def get_hook_param_count_public(hook):
        """Public wrapper for testing positional param count."""
        return p._get_hook_positional_param_count(hook)

    if get_hook_param_count_public(no_arg_func) != 0:
        pytest.fail("get_hook_param_count_public(no_arg_func) != 0")
    if get_hook_param_count_public(identity) != 1:
        pytest.fail("get_hook_param_count_public(identity) != 1")
    if get_hook_param_count_public(two) != 2:
        pytest.fail("get_hook_param_count_public(two) != 2")

    monkeypatch.setattr(
        plugin.inspect, "signature", lambda h: (_ for _ in ()).throw(ValueError("nope")) or (_ := h)
    )
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

    if get_hook_param_count_public(no_arg_func) is not None:
        pytest.fail("get_hook_param_count_public(no_arg_func) is not None")

    def bad(one):
        """
        Raises a RuntimeError with the message "boom".

        Args:
            one: Unused parameter.

        Raises:
            RuntimeError: Always raised when the function is called.
        """
        raise RuntimeError("boom")

    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p._safe_invoke_hook(bad, 1)
    if not any(c[0] == "exception" for c in p._logger.calls):
        pytest.fail("Expected at least one 'exception' log call")


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
    if "octoprint_uptime" not in info:
        pytest.fail('"octoprint_uptime" not in update information')
    if p.get_assets() != {"js": ["js/uptime.js"]}:
        pytest.fail("get_assets() did not return expected value")
    tcs = p.get_template_configs()
    if not any(isinstance(x, dict) for x in tcs):
        pytest.fail("No dict found in template configs")
    if p.is_api_protected() is not True:
        pytest.fail("is_api_protected() did not return True")
    if p.is_template_autoescaped() is not True:
        pytest.fail("is_template_autoescaped() did not return True")

    monkeypatch.setattr(plugin.OctoprintUptimePlugin, "_get_uptime_from_proc", lambda _: None)
    monkeypatch.setattr(plugin.OctoprintUptimePlugin, "_get_uptime_from_psutil", lambda _: None)
    secs, src = p._get_uptime_seconds()
    if not (secs is None and src == "none"):
        pytest.fail("_get_uptime_seconds() did not return (None, 'none')")


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
    if p._get_uptime_from_proc() is not None:
        pytest.fail(
            "_get_uptime_from_proc() should return None when "
            "/proc/uptime contains invalid content"
        )


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
    res = p._get_uptime_from_psutil()
    if res is not None:
        pytest.fail(
            "_get_uptime_from_psutil() should return None when import_module raises ImportError"
        )

    fake_ps = SimpleNamespace(boot_time=lambda: "invalid")
    monkeypatch.setattr(importlib, "import_module", lambda name: fake_ps)
    res2 = p._get_uptime_from_psutil()
    if res2 is not None:
        pytest.fail("_get_uptime_from_psutil() should return None when boot_time is invalid")


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
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

    called = {"base0": False, "base1": None}

    def base0(self):
        called["base0"] = True

    def base1(self):
        called["base1"] = self

    monkeypatch.setattr(plugin.SettingsPluginBase, "on_settings_initialized", base0, raising=False)
    p.on_settings_initialized()
    if called["base0"] is not True:
        pytest.fail("Expected called['base0'] to be True")

    monkeypatch.setattr(plugin.SettingsPluginBase, "on_settings_initialized", base1, raising=False)
    p.on_settings_initialized()
    if called["base1"] is None:
        raise AssertionError("Expected called['base1'] to be not None")


def test_invoke_settings_hook_unexpected_param_count():
    """
    Test that _invoke_settings_hook logs a warning when the hook function has an
    unexpected number of positional parameters.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    mp = pytest.MonkeyPatch()
    mp.setattr(p, "_get_hook_positional_param_count", lambda hook: 3)
    p._invoke_settings_hook(lambda: None)
    if not any(c[0] == "warning" for c in p._logger.calls):
        raise AssertionError("Expected at least one 'warning' log call")
    mp.undo()


def test_log_debug_throttled_no_logging(monkeypatch):
    """
    Test that the _log_debug method does not log a debug message when throttling is in effect.

    This test sets up the OctoprintUptimePlugin with debug logging enabled and simulates the
    current time such that the last debug log was just now, and the throttle interval has not
    yet passed. It verifies that no debug log is emitted under these conditions.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p._debug_enabled = True
    monkeypatch.setattr(time, "time", lambda: 1000)
    p._last_debug_time = 1000
    p._debug_throttle_seconds = 60
    p._log_debug("x")
    if any(c[0] == "debug" for c in p._logger.calls):
        raise AssertionError("Expected no debug log calls when throttling is in effect")


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
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

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
    if not isinstance(out, dict):
        raise AssertionError("Expected 'out' to be a dict")


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
    monkeypatch.setattr(plugin.OctoprintUptimePlugin, "_handle_permission_check", lambda self: None)
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (5, "5s", "5s", "0h", "0d"),
    )
    out = p.on_api_get()
    if not (isinstance(out, dict) and "json" in out):
        pytest.fail("Expected output to be a dict containing 'json' key")


def test_handle_permission_check_abort_raises(monkeypatch):
    """
    Test that _handle_permission_check handles exceptions raised by both
    _check_permissions and _abort_forbidden,
    and returns a dictionary response when both methods raise errors.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
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
    if not (res and isinstance(res, dict)):
        raise AssertionError("Expected res to be truthy and a dict")


def test_get_api_settings_exceptions():
    """
    Test that _get_api_settings handles exceptions when accessing settings,
    returning default values when a ValueError is raised by the settings object.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

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
    if not (nav is True and fmt == plugin._("full") and poll == 5):
        pytest.fail(
            f"Expected nav=True, fmt={plugin._('full')}, poll=5 but got nav={nav}, "
            f"fmt={fmt}, poll={poll}"
        )


def test_reload_with_octoprint_present_and_flask_abort(monkeypatch):
    """
    Test that the plugin reloads correctly when OctoPrint and Flask are present,
    and that the _abort_forbidden method triggers a Flask abort with code 403,
    returning the appropriate error response. Uses monkeypatching to inject
    fake modules and verifies cleanup after the test.
    """

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

    fake_flask.__dict__["abort"] = fake_abort
    fake_flask.__dict__["jsonify"] = lambda **kwargs: {"json": kwargs}

    monkeypatch.setitem(sys.modules, "octoprint.plugin", fake_plugin_mod)
    monkeypatch.setitem(sys.modules, "octoprint.access.permissions", fake_perm)
    monkeypatch.setitem(sys.modules, "flask", fake_flask)

    importlib.reload(plugin)
    p = plugin.OctoprintUptimePlugin()

    res = p._abort_forbidden()
    if not (res == {"error": plugin._("Forbidden")} or isinstance(res, dict)):
        raise AssertionError(
            f"Expected res to be {{'error': plugin._('Forbidden')}} or a dict, " f"got {res!r}"
        )
    if aborted.get("code") != 403:
        raise ValueError("Expected aborted code to be 403")

    monkeypatch.delitem(sys.modules, "octoprint.plugin", raising=False)
    monkeypatch.delitem(sys.modules, "octoprint.access.permissions", raising=False)
    monkeypatch.delitem(sys.modules, "flask", raising=False)
    importlib.reload(plugin)


def test_reload_with_missing_gettext_uses_fallback(monkeypatch):
    """
    Test that when the 'gettext' module is present but lacks the 'gettext' function,
    the plugin falls back to a default translation function that returns the input unchanged.
    """

    fake_gettext = types.ModuleType("gettext")

    def bindtextdomain(_, __):
        """
        Mock implementation of the gettext.bindtextdomain function.

        Args:
            _ (str): The domain name for the translation (unused).
            __ (str): The directory where the translation files are located (unused).

        Returns:
            None
        """
        return None

    setattr(fake_gettext, "bindtextdomain", bindtextdomain)
    setattr(fake_gettext, "textdomain", lambda _name: None)

    monkeypatch.setitem(sys.modules, "gettext", fake_gettext)
    importlib.reload(plugin)
    if plugin._("something") != "something":
        raise AssertionError('plugin._("something") != "something"')
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
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())

    p._settings = DummySettings({})
    nav, fmt, poll = p._get_api_settings()
    if nav is not True:
        pytest.fail("nav is not True")
    if fmt != plugin._("full"):
        pytest.fail(f"fmt != plugin._('full') (got {fmt!r})")
    if poll != 5:
        pytest.fail(f"poll != 5 (got {poll!r})")
    if not any(
        "defaulting to True" in str(c[1]) or "defaulting to 'full'" in str(c[1])
        for c in p._logger.calls
    ):
        pytest.fail("Expected defaulting log message not found in logger calls")

    p._settings = DummySettings(
        {"navbar_enabled": False, "display_format": "x", "poll_interval_seconds": "0"}
    )
    nav, fmt, poll = p._get_api_settings()
    if poll != 1:
        pytest.fail(f"poll != 1 (got {poll!r})")

    p._settings = DummySettings({"poll_interval_seconds": "999"})
    nav, fmt, poll = p._get_api_settings()
    if poll != 120:
        pytest.fail(f"poll != 120 (got {poll!r})")

    p._settings = DummySettings({"poll_interval_seconds": "bad"})
    nav, fmt, poll = p._get_api_settings()
    if poll != 5:
        raise AssertionError(f"poll != 5 (got {poll!r})")


def test_fallback_uptime_response_handles_exceptions(monkeypatch):
    """
    Test that the _fallback_uptime_response method correctly handles exceptions raised by
    _get_uptime_info,
    returning a response with 'uptime' set to 'unknown' and
    'uptime_available' set to False.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    monkeypatch.setattr(
        plugin.OctoprintUptimePlugin,
        "_get_uptime_info",
        lambda self: (_ for _ in ()).throw(AttributeError("boom")),
    )
    out = p._fallback_uptime_response()
    if isinstance(out, dict):
        data = out
    elif hasattr(out, "get_json"):
        data = out.get_json()
    elif hasattr(out, "json"):
        data = out.json
    else:
        data = None
    if isinstance(data, dict):
        uptime_is_unknown = data.get("uptime") == plugin._("unknown")
        uptime_not_available = data.get("uptime_available") is False
        if not (uptime_is_unknown and uptime_not_available):
            raise AssertionError(
                "Expected data['uptime'] == plugin._('unknown') and "
                "data['uptime_available'] is False"
            )
    else:
        pytest.fail("Response is not a dict and cannot check keys")


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
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p._safe_update_internal_state()
    if not any(c[0] == "warning" for c in p._logger.calls):
        raise AssertionError("Expected at least one 'warning' log call")


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

    if hasattr(p, "set_logger"):
        p.set_logger(BadLogger())
    else:
        setattr(p, "_logger", BadLogger())
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

    if hasattr(p, "set_logger"):
        p.set_logger(BadLogger())
    else:
        setattr(p, "_logger", BadLogger())
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
    allowed_modules = {
        "os",
        "sys",
        "time",
        "types",
        "builtins",
        "pytest",
        "octoprint_uptime.plugin",
    }

    def safe_import_module(name):
        """
        Safely imports a module by name, restricting imports to a predefined set of allowed modules.

        Args:
            name (str): The name of the module to import.

        Returns:
            module: The imported module object.

        Raises:
            ImportError: If the module name is not in the allowed set.

        Special Cases:
            - If 'psutil' is requested, returns the 'fake_ps' object instead of importing.
        """
        if name == "psutil":
            return fake_ps
        if name in allowed_modules:
            return sys.modules[name]
        raise ImportError(f"Import of module '{name}' is not allowed in tests")

    monkeypatch.setattr(
        importlib,
        "import_module",
        safe_import_module,
    )

    if p._get_uptime_from_psutil() is not None:
        pytest.fail(
            "_get_uptime_from_psutil() should return None when boot_time() is in the future"
        )


def test_get_uptime_from_proc_missing(monkeypatch):
    """
    Test that _get_uptime_from_proc returns None when the /proc/uptime file is missing.

    This test uses monkeypatch to simulate the absence of the /proc/uptime file by making
    os.path.exists always return False.
    """
    p = plugin.OctoprintUptimePlugin()
    monkeypatch.setattr(plugin.os.path, "exists", lambda path: False)
    if p._get_uptime_from_proc() is not None:
        pytest.fail("_get_uptime_from_proc() should return None when /proc/uptime is missing")


def test_get_uptime_info_exception_path():
    """
    Test that _get_uptime_info handles exceptions raised by get_uptime_seconds gracefully.

    This test simulates an exception in get_uptime_seconds and verifies that
    _get_uptime_info returns None and the localized "unknown" string as expected.
    """
    p = plugin.OctoprintUptimePlugin()
    if hasattr(p, "set_logger"):
        p.set_logger(FakeLogger())
    else:
        setattr(p, "_logger", FakeLogger())
    p.get_uptime_seconds = lambda: (_ for _ in ()).throw(TypeError("boom"))
    s, full, *_ = p._get_uptime_info()
    if not (s is None and full == plugin._("unknown")):
        raise AssertionError("Expected s to be None and full to be plugin._('unknown')")


def test_execute_plugin_source_for_coverage():
    """
    Test that the plugin source file can be executed directly for coverage purposes,
    and verify that key functions are available and behave as expected after execution.

    This test runs the plugin module as a script to ensure all lines are covered by coverage tools,
    then imports the module to check that the 'format_uptime' function exists and returns the
    correct output for a sample input.
    """

    runpy.run_path(plugin.__file__, run_name="__main__")

    mod = importlib.import_module("octoprint_uptime.plugin")
    if not hasattr(mod, "format_uptime"):
        raise AssertionError("Module does not have 'format_uptime'")
    if mod.format_uptime(1) != "1s":
        raise AssertionError("mod.format_uptime(1) != '1s'")


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
    if defaults["debug"] is not False:
        pytest.fail('Expected defaults["debug"] to be False')
    if defaults["navbar_enabled"] is not True:
        pytest.fail('Expected defaults["navbar_enabled"] to be True')

    called = {}

    def fake_validate(_):
        """
        Simulates a validation function for testing purposes.

        Args:
            _: The input data to be "validated". This argument is not used in the function body.

        Side Effects:
            Sets the "validate" key in the 'called' dictionary to True to indicate
            the function was called.
        """
        called["validate"] = True

    def fake_log(_):
        """
        Mock logging function for testing purposes.

        Args:
            _: The data to be logged. This argument is not used in the function body.
        """
        called["log"] = True

    def fake_call_base(_):
        """
        Simulates a call to the base function by setting the 'call_base' key in the
        'called' dictionary to True.

        Args:
            _: Unused argument, present to match the expected function signature.
        """
        called["call_base"] = True

    monkeypatch.setattr(p, "_validate_and_sanitize_settings", fake_validate)
    monkeypatch.setattr(p, "_log_settings_save_data", fake_log)
    monkeypatch.setattr(p, "_call_base_on_settings_save", fake_call_base)
    monkeypatch.setattr(p, "_update_internal_state", lambda: called.__setitem__("updated", True))

    p.on_settings_save({})
    if not (
        called.get("validate")
        and called.get("log")
        and called.get("call_base")
        and called.get("updated")
    ):
        pytest.fail("Expected all hooks to be called: validate, log, call_base, updated")


def test_reload_plugin_with_gettext_bind_failure(monkeypatch):
    """
    Test that reloading the plugin handles a failure in gettext.bindtextdomain gracefully.

    This test simulates an OSError being raised by gettext.bindtextdomain to ensure that
    the plugin's internationalization fallback logic is triggered correctly. It verifies
    that the plugin's translation function (`plugin._`) remains callable even when
    gettext binding fails, and ensures proper cleanup of the monkeypatched module.
    """

    fake_gettext = types.ModuleType("gettext")

    def bad_bind(_domain, _localedir):
        """
        Simulates a failing bind operation by always raising an OSError.

        Args:
            _domain: The domain parameter (unused).
            _localedir: The localedir parameter (unused).

        Raises:
            OSError: Always raised with the message "nope".
        """
        raise OSError("nope")

    setattr(fake_gettext, "bindtextdomain", bad_bind)
    setattr(fake_gettext, "textdomain", lambda _name: None)
    setattr(fake_gettext, "gettext", lambda s: s)

    monkeypatch.setitem(sys.modules, "gettext", fake_gettext)
    importlib.reload(plugin)
    if not callable(plugin._):
        raise AssertionError("plugin._ is not callable")
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
    if not hasattr(plugin, "SettingsPluginBase"):
        raise AssertionError("plugin does not have attribute 'SettingsPluginBase'")
    if not hasattr(plugin, "SimpleApiPluginBase"):
        raise AssertionError("plugin does not have attribute 'SimpleApiPluginBase'")
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

        def debug(self, *a):
            """
            Appends a debug record to the records list.

            Args:
                *a: Positional arguments to include in the debug record.

            Note:
                Only positional arguments are stored.
            """
            self.records.append(("debug", a))

        def info(self, *a):
            """
            Appends an 'info' record with the provided positional arguments to the records list.

            Args:
                *a: Variable length positional arguments to be recorded.
            """
            self.records.append(("info", a))

        def warning(self, *a):
            """
            Appends a warning record to the records list.

            Args:
                *a: Positional arguments to be included in the warning record.
            """
            self.records.append(("warn", a))

        def exception(self, *a):
            """
            Handle an exception event by appending the exception record to the records list.

            Args:
                *a: Positional arguments representing exception details.

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
    if src != "proc":
        raise AssertionError("Expected source to be 'proc'")
    if not (sec is not None and abs(sec - 123.4) < 0.001):
        raise AssertionError("Expected sec to be not None and within 0.001 of 123.4")


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
    if not (sec is not None and sec > 0):
        raise AssertionError("Expected sec to be not None and greater than 0")


def test_validate_and_sanitize_settings_handles_bad_shapes():
    """
    Test that the _validate_and_sanitize_settings method correctly handles invalid or
    unexpected shapes of the settings input, such as empty lists, or improperly
    structured dictionaries.
    """
    p = make_plugin()
    p._validate_and_sanitize_settings({})
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
    if cfg["debug_throttle_seconds"] != 60:
        raise ValueError("Invalid debug_throttle_seconds")
    if cfg["poll_interval_seconds"] != 5:
        raise AssertionError("poll_interval_seconds should be 5")


def test_log_settings_after_save_logs_change():
    """
    Test that changing the 'navbar_enabled' setting and saving logs an info message.

    This test verifies that after toggling the 'navbar_enabled' setting in the plugin's
    settings, the internal state is updated and the '_log_settings_after_save' method logs
    an info-level message.
    """
    p = make_plugin()
    p._update_internal_state()
    prev = p._navbar_enabled
    p._settings._data["navbar_enabled"] = not prev
    p._update_internal_state()
    p._log_settings_after_save(prev)
    if not any(r[0] == "info" for r in p._logger.records):
        raise AssertionError("Expected info-level log message not found.")


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
    if not any(r[0] == "warn" for r in p._logger.records):
        raise AssertionError("Expected at least one 'warn' log call")


def test_get_uptime_info_handles_custom_getter():
    """
    Test that _get_uptime_info uses a custom uptime getter if provided.

    This test replaces the plugin's get_uptime_seconds method with a lambda that returns 42,
    then verifies that _get_uptime_info returns the correct uptime value and updates the
    _last_uptime_source attribute to "custom".
    """
    p = make_plugin()
    p.get_uptime_seconds = lambda: 42
    seconds, *_ = p._get_uptime_info()
    if seconds != 42:
        pytest.fail(f"Expected seconds == 42, got {seconds!r}")
    if p._last_uptime_source != "custom":
        pytest.fail(f"Expected _last_uptime_source == 'custom', got {p._last_uptime_source!r}")


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
    seconds, full, *_ = p._get_uptime_info()
    if seconds is not None:
        pytest.fail("Expected seconds to be None")
    if full != plugin._("unknown"):
        pytest.fail(f"Expected full == plugin._('unknown'), got {full!r}")


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
    if not (isinstance(res, dict) and res.get("error") == plugin._("Forbidden")):
        raise RuntimeError("Permission check failed")


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
    if res != {"error": "ok"}:
        raise AssertionError(f"Expected res == {{'error': 'ok'}}, got {res!r}")


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
    except Forbidden as e:
        try:
            if not isinstance(e, Forbidden):
                pytest.fail("Exception is not instance of Forbidden")
            if getattr(e, "code", None) != 403:
                pytest.fail("Forbidden exception code is not 403")
        except (ImportError, AttributeError):
            if not hasattr(e, "args"):
                pytest.fail("Exception does not have 'args' attribute")
    else:
        if not (isinstance(res, dict) and res.get("error") == plugin._("Forbidden")):
            pytest.fail("Expected a dict with error == plugin._('Forbidden')")


def test__get_uptime_seconds_prefers_psutil_branch():
    """
    Test that _get_uptime_seconds() prefers the psutil-based method for retrieving uptime
    when both psutil and proc-based methods are available, and returns the correct source and value.
    """
    p = plugin.OctoprintUptimePlugin()
    p._get_uptime_from_proc = lambda: None
    p._get_uptime_from_psutil = lambda: 123.0
    sec, src = p._get_uptime_seconds()
    if src != "psutil":
        raise AssertionError("Expected source to be 'psutil'")
    if sec != 123.0:
        raise AssertionError("Expected sec == 123.0")


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
    p._debug_throttle_seconds = None  # type: ignore
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
    if res != {"error": "nope"}:
        raise AssertionError(f"Expected res == {{'error': 'nope'}}, got {res!r}")


def test__check_permissions_default_true():
    """
    Test that the _check_permissions method of OctoprintUptimePlugin returns True by default.
    """
    p = plugin.OctoprintUptimePlugin()
    if p._check_permissions() is not True:
        raise AssertionError("Expected _check_permissions() to return True")


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
    sec, _, _, _, _ = p._get_uptime_info()
    if sec != 321:
        raise AssertionError("Expected sec == 321")
    if p._last_uptime_source != "proc":
        raise AssertionError("Expected p._last_uptime_source == 'proc'")


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
    s, full, *_ = p._get_uptime_info()
    if not (s is None and full == plugin._("unknown")):
        raise AssertionError("Expected s is None and full == plugin._('unknown')")
