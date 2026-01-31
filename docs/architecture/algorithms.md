# Algorithms & Formatting

This page documents the small helper algorithms used to format uptime values and convert raw seconds into human-friendly representations. The implementation lives in `octoprint_uptime` and is documented via docstrings (see the Python API reference).

## Formatting modes

- `full`: long human-readable string, e.g. `"1 day 2 hours 3 minutes 4 seconds"`.
- `dhm`: days/hours/minutes, e.g. `"1d 2h 3m"`.
- `dh`: days/hours only, e.g. `"1d 2h"`.
- `d`: days only, e.g. `"3d"`.
- `short`: compact form where appropriate.

## Edge cases

- Negative or zero seconds are normalized to `0` and rendered as `"0s"` or the configured fallback.
- Large uptimes are expressed in days rather than hours to keep the UI compact.

See the Python API reference for the concrete function names and signatures.
