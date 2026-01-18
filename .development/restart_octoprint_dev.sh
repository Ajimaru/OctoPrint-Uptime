#!/usr/bin/env bash
set -euo pipefail

# Restart OctoPrint safely (tries to avoid Safe Mode) and optionally clear caches.
#
# This script intentionally avoids hardcoded machine-specific paths so it can be committed.
# It will resolve the `octoprint` executable in this order:
#   1) OCTOPRINT_CMD (explicit path to the octoprint executable)
#   2) OCTOPRINT_VENV (uses $OCTOPRINT_VENV/bin/octoprint)
#   3) common repo-relative locations (e.g. ./venv/bin/octoprint)
#   4) `octoprint` on PATH
#
# Configure via environment variables:
#   OCTOPRINT_CMD=/path/to/octoprint
#   OCTOPRINT_VENV=/path/to/venv
#   OCTOPRINT_PORT=5000
#   OCTOPRINT_ARGS="serve --debug"    # appended after the octoprint executable
#   OCTOPRINT_BASEDIR=$HOME/.octoprint

OCTOPRINT_PORT_DEFAULT="5000"
OCTOPRINT_ARGS_DEFAULT="serve --debug"

OCTOPRINT_PORT="${OCTOPRINT_PORT:-$OCTOPRINT_PORT_DEFAULT}"
OCTOPRINT_ARGS="${OCTOPRINT_ARGS:-$OCTOPRINT_ARGS_DEFAULT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT_DEFAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$WORKSPACE_ROOT_DEFAULT}"

OCTOPRINT_CMD="${OCTOPRINT_CMD:-}"  # if set, must be an executable
OCTOPRINT_VENV="${OCTOPRINT_VENV:-}"  # if set, uses $OCTOPRINT_VENV/bin/octoprint

resolve_octoprint_bin() {
  if [[ -n "$OCTOPRINT_CMD" ]]; then
    echo "$OCTOPRINT_CMD"
    return 0
  fi

  if [[ -n "$OCTOPRINT_VENV" ]]; then
    echo "$OCTOPRINT_VENV/bin/octoprint"
    return 0
  fi

  # Try common relative locations (repo-local, no system-specific absolute paths)
  local candidate
  for candidate in \
    "$WORKSPACE_ROOT/venv/bin/octoprint" \
    "$WORKSPACE_ROOT/.venv/bin/octoprint" \
    "$WORKSPACE_ROOT/../OctoPrint/.venv/bin/octoprint" \
    "$WORKSPACE_ROOT/../OctoPrint/venv/bin/octoprint"; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done

  # Fall back to PATH
  command -v octoprint 2>/dev/null || true
}

OCTOPRINT_BIN="$(resolve_octoprint_bin)"
NOHUP_OUT="${NOHUP_OUT:-/tmp/octoprint.nohup}"
OCTOPRINT_BASEDIR="${OCTOPRINT_BASEDIR:-$HOME/.octoprint}"
OCTOPRINT_LOG="${OCTOPRINT_LOG:-$OCTOPRINT_BASEDIR/logs/octoprint.log}"
SAFE_MARKER="$OCTOPRINT_BASEDIR/data/last_safe_mode"
WEBASSETS_DIR="$OCTOPRINT_BASEDIR/generated/webassets"

# Line number in the OctoPrint log at the moment we (re)start.
# Used to scope verification to new log output only.
LOG_LINE_START=0

usage() {
  cat <<EOF
Usage: $0 [--force-kill] [--clear-cache] [--stop-all | --restart-all] [--stop-only]

Options:
  -h, --help     Show this help and exit.
  --force-kill   If SIGTERM doesn't stop OctoPrint within the timeout, send SIGKILL.
                WARNING: forced kills can trigger OctoPrint Safe Mode on next start.
  --clear-cache  Remove OctoPrint generated webassets cache before starting.
                Useful when changing plugin frontend assets (JS/CSS/templates) and you
                suspect stale bundles. Not required for pure Python changes.
  --stop-all     Stop all detected OctoPrint instances for the current user and exit.
                Uses process matching (best-effort), no sudo required.
  --restart-all  Stop all detected OctoPrint instances for the current user, then restart.
                Uses process matching (best-effort), no sudo required.
  --stop-only    Alias for --stop-all.

Environment overrides:
  OCTOPRINT_CMD, OCTOPRINT_VENV, OCTOPRINT_PORT, OCTOPRINT_ARGS,
  OCTOPRINT_BASEDIR, OCTOPRINT_LOG, NOHUP_OUT
EOF
}

FORCE_KILL=0
CLEAR_CACHE=0
STOP_ALL=0
RESTART_AFTER_STOP_ALL=0
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || "${1:-}" == "help" ]]; then
  usage
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|help)
      usage
      exit 0
      ;;
    --force-kill)
      FORCE_KILL=1
      shift
      ;;
    --clear-cache)
      CLEAR_CACHE=1
      shift
      ;;
    --stop-all)
      STOP_ALL=1
      RESTART_AFTER_STOP_ALL=0
      shift
      ;;
    --restart-all)
      STOP_ALL=1
      RESTART_AFTER_STOP_ALL=1
      shift
      ;;
    --stop-only)
      STOP_ALL=1
      RESTART_AFTER_STOP_ALL=0
      shift
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$OCTOPRINT_BIN" || ! -x "$OCTOPRINT_BIN" ]]; then
  echo "ERROR: octoprint executable not found/executable: $OCTOPRINT_BIN" >&2
  echo "Set OCTOPRINT_CMD to your octoprint binary, or set OCTOPRINT_VENV, or put 'octoprint' on PATH." >&2
  exit 2
fi

find_listener_pid() {
  ss -ltnp 2>/dev/null | awk -v port=":$OCTOPRINT_PORT" '$0 ~ port { if (match($0,/pid=([0-9]+)/,m)) { print m[1]; exit } }'
}

list_octoprint_pids() {
  # Best-effort detection of OctoPrint server processes for the current user.
  # We intentionally avoid sudo/system-wide process inspection.
  local uid
  uid="$(id -u)"

  if command -v pgrep >/dev/null 2>&1; then
    {
      pgrep -u "$uid" -f "octoprint.*serve" 2>/dev/null || true
      pgrep -u "$uid" -f "python(3)? .* -m octoprint.*serve" 2>/dev/null || true
    } | awk '!seen[$0]++'
    return 0
  fi

  ps -u "$uid" -o pid= -o args= 2>/dev/null | awk '
    /octoprint/ && /serve/ { print $1 }
    /python/ && / -m octoprint/ && /serve/ { print $1 }
  ' | awk '!seen[$0]++'
}

wait_pids_exit() {
  local timeout_s="$1"; shift
  local interval_s="0.5"
  local tries
  tries=$(awk -v t="$timeout_s" -v i="$interval_s" 'BEGIN { if (i <= 0) i=0.5; printf "%d", int((t / i) + 0.999) }')

  local n=0
  while (( n < tries )); do
    local any_alive=0
    local pid
    for pid in "$@"; do
      if kill -0 "$pid" 2>/dev/null; then
        any_alive=1
        break
      fi
    done

    if (( ! any_alive )); then
      return 0
    fi

    sleep "$interval_s"
    n=$((n + 1))
  done
  return 1
}

stop_all_octoprint() {
  local pids
  pids="$(list_octoprint_pids || true)"
  if [[ -z "$pids" ]]; then
    echo "No OctoPrint instances detected for current user; nothing to stop."
    return 0
  fi

  echo "Stopping all detected OctoPrint instances (SIGTERM): $(echo "$pids" | tr '\n' ' ')"
  local pid
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    kill -TERM "$pid" 2>/dev/null || true
  done <<<"$pids"

  if wait_pids_exit 30 $(echo "$pids" | tr '\n' ' '); then
    echo "All detected OctoPrint instances stopped."
    return 0
  fi

  echo "Timeout waiting for all OctoPrint instances to stop." >&2
  if (( FORCE_KILL )); then
    echo "Forcing kill (SIGKILL) for remaining processes." >&2
    while read -r pid; do
      [[ -z "$pid" ]] && continue
      if kill -0 "$pid" 2>/dev/null; then
        kill -KILL "$pid" 2>/dev/null || true
      fi
    done <<<"$pids"

    if wait_pids_exit 10 $(echo "$pids" | tr '\n' ' '); then
      echo "All detected OctoPrint instances stopped after SIGKILL." >&2
      return 0
    fi
  fi

  echo "ERROR: One or more OctoPrint instances still appear to be running. Aborting." >&2
  exit 3
}

wait_port_free() {
  local tries=0
  while ss -ltn 2>/dev/null | grep -qE ":${OCTOPRINT_PORT}\\b"; do
    tries=$((tries+1))
    if (( tries > 120 )); then
      return 1
    fi
    sleep 0.5
  done
  return 0
}

stop_octoprint() {
  local pid
  pid="$(find_listener_pid || true)"
  if [[ -z "$pid" ]]; then
    echo "No listener on port $OCTOPRINT_PORT; nothing to stop."
    return 0
  fi

  echo "Stopping OctoPrint pid=$pid (SIGTERM)";
  kill -TERM "$pid" 2>/dev/null || true

  if wait_port_free; then
    echo "Port $OCTOPRINT_PORT is free."
    return 0
  fi

  echo "Timeout waiting for port $OCTOPRINT_PORT to free." >&2
  if (( FORCE_KILL )); then
    echo "Forcing kill (SIGKILL) pid=$pid" >&2
    kill -KILL "$pid" 2>/dev/null || true
    if wait_port_free; then
      echo "Port $OCTOPRINT_PORT is free after SIGKILL." >&2
      return 0
    fi
  fi

  echo "ERROR: OctoPrint still appears to be running. Aborting." >&2
  exit 3
}

clear_octoprint_cache() {
  if (( ! CLEAR_CACHE )); then
    return 0
  fi
  echo "Clearing OctoPrint generated cache (best-effort): $WEBASSETS_DIR"
  rm -rf "$WEBASSETS_DIR" || true
}

clear_octoprint_log() {
  # Start every restart from a clean log to make troubleshooting unambiguous.
  echo "Clearing OctoPrint log (best-effort): $OCTOPRINT_LOG"
  mkdir -p "$(dirname "$OCTOPRINT_LOG")" || true
  rm -f "$OCTOPRINT_LOG" || true
  : > "$OCTOPRINT_LOG" || true
}

tail_log_grep() {
  local pattern="$1"
  local lines="${2:-20000}"
  if [[ ! -f "$OCTOPRINT_LOG" ]]; then
    return 1
  fi
  tail -n "$lines" "$OCTOPRINT_LOG" | grep -E "$pattern" >/dev/null 2>&1
}

log_since_start() {
  if [[ ! -f "$OCTOPRINT_LOG" ]]; then
    return 1
  fi
  tail -n +"$((LOG_LINE_START + 1))" "$OCTOPRINT_LOG" 2>/dev/null
}

log_since_start_grep() {
  local pattern="$1"
  log_since_start | grep -E "$pattern" >/dev/null 2>&1
}

wait_for_log() {
  local pattern="$1"
  local timeout_s="${2:-20}"
  local interval_s="${3:-0.5}"
  local tries
  tries=$(awk -v t="$timeout_s" -v i="$interval_s" 'BEGIN { if (i <= 0) i=0.5; printf "%d", int((t / i) + 0.999) }')

  local n=0
  while (( n < tries )); do
    if log_since_start_grep "$pattern"; then
      return 0
    fi
    sleep "$interval_s"
    n=$((n + 1))
  done
  return 1
}

start_octoprint() {
  # Ensure we start from a clean log for this restart.
  clear_octoprint_log
  LOG_LINE_START=0

  echo "Clearing safe-mode marker (if present): $SAFE_MARKER"
  rm -f "$SAFE_MARKER" || true

  clear_octoprint_cache

  : > "$NOHUP_OUT"

  echo "Starting OctoPrint: $OCTOPRINT_BIN $OCTOPRINT_ARGS"
  # shellcheck disable=SC2086
  nohup "$OCTOPRINT_BIN" $OCTOPRINT_ARGS >"$NOHUP_OUT" 2>&1 &

  local new_pid=$!
  echo "Started pid=$new_pid; waiting for listen on port $OCTOPRINT_PORT"

  local tries=0
  while ! ss -ltn 2>/dev/null | grep -qE ":${OCTOPRINT_PORT}\\b"; do
    tries=$((tries+1))
    if (( tries > 80 )); then
      echo "ERROR: OctoPrint did not start listening in time." >&2
      echo "--- tail $NOHUP_OUT ---" >&2
      tail -n 200 "$NOHUP_OUT" >&2 || true
      exit 4
    fi
    sleep 0.5
  done

  echo "OctoPrint is listening on port $OCTOPRINT_PORT."
}

check_safe_mode() {
  if [[ -f "$SAFE_MARKER" ]]; then
    echo "WARNING: Safe mode marker exists again: $SAFE_MARKER" >&2
    echo "marker_content=$(cat "$SAFE_MARKER" 2>/dev/null || true)" >&2
  fi

  if [[ -f "$OCTOPRINT_LOG" ]]; then
    echo "--- recent safe mode lines (log tail) ---"
    tail -n 8000 "$OCTOPRINT_LOG" | grep -n -i "Starting in SAFE MODE\|Reason for safe mode" | tail -n 30 || echo "(no safe mode lines found)"
  else
    echo "NOTE: OctoPrint log not found: $OCTOPRINT_LOG" >&2
  fi

  echo "--- listener ---"
  ss -ltnp | grep -E ":${OCTOPRINT_PORT}\\b" || true
}

verify_plugin_loaded() {
  if [[ ! -f "$OCTOPRINT_LOG" ]]; then
    echo "NOTE: Cannot verify plugin load; log not found: $OCTOPRINT_LOG" >&2
    return 0
  fi

  echo "--- uptime plugin verification (log tail) ---"

  # Give OctoPrint a moment to finish startup and flush logs.
  # (Especially right after port becomes available.)
  sleep 1

  # Ensure the log is actually being written before we verify plugin markers.
  wait_for_log "octoprint\.startup - INFO - Starting OctoPrint" 20 0.5 || true
  wait_for_log "octoprint\.plugin\.core - INFO - Loading plugins from" 20 0.5 || true

  # If the plugin isn't installed/enabled, it may not show up at all.
  # In that case we should not warn; the user explicitly might have it uninstalled.
  # Also check for already loaded plugins (no "Enabled" message on restart)
  if ! wait_for_log "Enabled plugin uptime|octoprint_uptime/__init__|octoprint\.plugins\.uptime|Loaded plugin octoprint_uptime" 15 0.5; then
    echo "uptime: not detected in startup log (likely not installed); skipping verification"
    return 0
  fi

  # 1) Look for any plugin-specific log activity (optional)
  # Note: Our plugin only logs on API calls, not on startup, so this may not find anything
  if wait_for_log "octoprint\.plugins\.uptime" 5 0.5; then
    echo "uptime: log activity detected"
  else
    echo "NOTE: No uptime log lines observed (since restart)."
  fi

  # 2) Show the actual metadata path OctoPrint used for octoprint_uptime (scoped to log lines since restart).
  # OctoPrint log lines may wrap, splitting the path across multiple lines.
  # We therefore scan for the most recent occurrence across up to 3 concatenated lines.
  local meta_path
  meta_path="$(log_since_start | awk '
    { a[++n] = $0 }
    END {
      for (i = n; i >= 1; i--) {
        combo = a[i]
        if (i + 1 <= n) combo = combo a[i + 1]
        if (i + 2 <= n) combo = combo a[i + 1] a[i + 2]
        if (index(combo, "Parsing plugin metadata from AST of") > 0 && index(combo, "octoprint_uptime/__init__") > 0) {
          if (match(combo, /Parsing plugin metadata from AST of ([^\r\n]*octoprint_uptime\/__init__\.py)/, m)) {
            print m[1]
            exit 0
          }
        }
      }
      exit 1
    }
  ' 2>/dev/null || true)"

  if [[ -n "$meta_path" ]]; then
    echo "uptime: metadata path: $meta_path"
  else
    echo "WARNING: Could not find a fresh 'Parsing plugin metadata...' line for uptime (since restart)." >&2
  fi

  # 3) Confirm OctoPrint enabled the plugin (i.e., not in safe mode)
  # Check for both fresh enable messages and already loaded plugins
  if wait_for_log "Enabled plugin uptime|Loaded plugin octoprint_uptime" 10 0.5; then
    echo "uptime: enabled/loaded OK"
  else
    echo "WARNING: Did not find 'Enabled plugin uptime' or 'Loaded plugin octoprint_uptime' in log (since restart)." >&2
  fi
}

if (( STOP_ALL )); then
  stop_all_octoprint
fi

if (( STOP_ALL )) && (( ! RESTART_AFTER_STOP_ALL )); then
  echo "Stop-all requested; not starting OctoPrint."
  exit 0
fi

stop_octoprint
start_octoprint
check_safe_mode
verify_plugin_loaded

echo "Done."
