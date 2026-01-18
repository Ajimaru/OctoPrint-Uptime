import io
import os
import sys
import time
import types


def _prepare_dummy_env():
    # Provide minimal dummy modules for octoprint_uptime import in tests
    if "octoprint" not in sys.modules:
        sys.modules["octoprint"] = types.ModuleType("octoprint")
    if "octoprint.plugin" not in sys.modules:
        mod = types.ModuleType("octoprint.plugin")

        class SimpleApiPlugin:
            """Stub for octoprint.plugin.SimpleApiPlugin"""

            pass

        class AssetPlugin:
            """Stub for octoprint.plugin.AssetPlugin"""

            pass

        mod.SimpleApiPlugin = SimpleApiPlugin  # type: ignore
        mod.AssetPlugin = AssetPlugin  # type: ignore
        sys.modules["octoprint.plugin"] = mod
        # expose on top-level octoprint module
        if "octoprint" in sys.modules:
            setattr(sys.modules["octoprint"], "plugin", mod)
    if "octoprint.access.permissions" not in sys.modules:
        mod = types.ModuleType("octoprint.access.permissions")

        class Permissions:
            """Stub for octoprint.access.permissions.Permissions"""

            class SYSTEM:
                @staticmethod
                def can():
                    return True

        mod.Permissions = Permissions  # type: ignore
        sys.modules["octoprint.access.permissions"] = mod
        # ensure octoprint.access points to a module with permissions
        if "octoprint" in sys.modules:
            access_mod = types.ModuleType("octoprint.access")
            access_mod.permissions = mod.Permissions  # type: ignore
            sys.modules["octoprint.access"] = access_mod
            setattr(sys.modules["octoprint"], "access", access_mod)
    # Minimal flask stub
    if "flask" not in sys.modules:
        f = types.ModuleType("flask")

        def _jsonify(**kwargs):
            return kwargs

        f.jsonify = _jsonify  # type: ignore
        sys.modules["flask"] = f


def _ensure_repo_on_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _load_octoprint_uptime():
    import importlib.util

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    init_path = os.path.join(repo_root, "octoprint_uptime", "__init__.py")
    spec = importlib.util.spec_from_file_location(
        "octoprint_uptime",
        init_path,
    )
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["octoprint_uptime"] = module
    loader.exec_module(module)
    return module


def test_format_uptime():
    _prepare_dummy_env()
    # load package from repository path to avoid import issues
    octoprint_uptime = _load_octoprint_uptime()

    assert octoprint_uptime._format_uptime(1) == "1s"
    assert octoprint_uptime._format_uptime(65) == "1m 5s"
    assert octoprint_uptime._format_uptime(3600 + 65) == "1h 1m 5s"
    assert octoprint_uptime._format_uptime(86400 + 3600 + 65) == "1d 1h 1m 5s"


def test_get_uptime_from_proc(monkeypatch):
    _prepare_dummy_env()
    # Simulate /proc/uptime
    monkeypatch.setattr("os.path.exists", lambda p: True)

    def _dummy_open(p, mode="r"):
        return io.StringIO("12345.67 0.00")

    monkeypatch.setattr("builtins.open", _dummy_open)
    octoprint_uptime = _load_octoprint_uptime()
    plugin = octoprint_uptime.UptimePlugin()
    secs = plugin._get_uptime_seconds()
    assert abs(secs - 12345.67) < 1e-6


def test_get_uptime_from_psutil(monkeypatch):
    _prepare_dummy_env()
    # /proc missing
    monkeypatch.setattr("os.path.exists", lambda p: False)

    ps = types.ModuleType("psutil")

    def _boot_time():
        return time.time() - 500

    setattr(ps, "boot_time", _boot_time)
    sys.modules["psutil"] = ps
    octoprint_uptime = _load_octoprint_uptime()
    plugin = octoprint_uptime.UptimePlugin()
    secs = plugin._get_uptime_seconds()
    assert 490 < secs < 510
