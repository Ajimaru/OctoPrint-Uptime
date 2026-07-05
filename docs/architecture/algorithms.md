# Algorithms & Formatting

This page documents the helper algorithms used to convert raw uptime seconds into human-friendly strings. The implementation lives in `octoprint_uptime/plugin.py` and is documented via docstrings (see the [Python API reference](../api/python.md)).

## Uptime sources

- **System uptime**: read from `/proc/uptime` on Linux; falls back to `psutil.boot_time()` (uptime = now − boot time) when `/proc` is unavailable.
- **OctoPrint process uptime**: computed from `/proc/self/stat` (process start in clock ticks relative to boot, which is robust against wall-clock jumps); falls back to `psutil.Process(...).create_time()`.
- Values outside the sanity range `0 ≤ uptime < ~10 years` are discarded as clock artifacts; when no source yields a valid value, the API reports `uptime_available: false`.

## Formatting modes

All formatters truncate to whole seconds and derive days/hours/minutes/seconds via integer division (`86400` / `3600` / `60`).

| Mode    | Function            | Example (93784 s) | Notes                                                |
| ------- | ------------------- | ----------------- | ---------------------------------------------------- |
| `full`  | `format_uptime`     | `1d 2h 3m 4s`     | Leading zero units are omitted (e.g. `61` → `1m 1s`) |
| `dhm`   | `format_uptime_dhm` | `1d 2h 3m`        | `0` days omitted (e.g. `3600` → `1h 0m`)             |
| `dh`    | `format_uptime_dh`  | `1d 2h`           | `0` days omitted (e.g. `3600` → `1h`)                |
| `d`     | `format_uptime_d`   | `1d`              | Always shows days, even `0d`                         |
| `short` | —                   | `1d 2h`           | Legacy alias; the frontend renders the `dh` variant  |

The API always returns **all** variants; `display_format` only selects which variant the frontend displays.

## Edge cases

- Fractional seconds are truncated (`61.9` → `1m 1s`).
- When no uptime source is available, the formatted strings are the localized string `unknown` and `uptime_available` is `false` in the API response.
- Negative or implausibly large values never reach the formatters: the retrieval layer filters them out beforehand.
