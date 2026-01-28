#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
_SCRIPT_DIR_HINT="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd || dirname "$0")"
REPO_ROOT="$(cd "$_SCRIPT_DIR_HINT/.." >/dev/null 2>&1 && pwd || echo "$_SCRIPT_DIR_HINT")"
WRAPPER="$REPO_ROOT/.development/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
  if [ -x "$WRAPPER" ]; then
    exec "$WRAPPER" "$0" "$@"
  elif command -v bash >/dev/null 2>&1; then
    exec bash "$0" "$@"
  fi
fi

# Description: Safely stop and restart local OctoPrint instances for development.
# Behavior:
#  - Resolves the `octoprint` executable from `OCTOPRINT_CMD`, `OCTOPRINT_VENV`, common
#    repo-relative locations, or the PATH.
#  - Can stop/restart a single instance (by listening port) or stop/restart all instances
#    for the current user. Provides options to force-kill and to clear generated webassets.
#  - Waits for ports to free and attempts graceful shutdown before SIGKILL (when allowed).
#  - Verifies plugin startup by observing log entries and can clear safe-mode markers.
# Environment variables:
#  - OCTOPRINT_CMD, OCTOPRINT_VENV, OCTOPRINT_PORT, OCTOPRINT_ARGS, OCTOPRINT_BASEDIR
# Usage examples:
#  - Stop and restart: ./.development/restart_octoprint_dev.sh
#  - Stop all instances: ./.development/restart_octoprint_dev.sh --stop-all
#  - Restart with cache clear: ./.development/restart_octoprint_dev.sh --clear-cache

set -euo pipefail

OCTOPRINT_PORT_DEFAULT="5000"
OCTOPRINT_ARGS_DEFAULT="serve --debug"

OCTOPRINT_PORT="${OCTOPRINT_PORT:-$OCTOPRINT_PORT_DEFAULT}"
OCTOPRINT_ARGS="${OCTOPRINT_ARGS:-$OCTOPRINT_ARGS_DEFAULT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT_DEFAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$WORKSPACE_ROOT_DEFAULT}"

OCTOPRINT_CMD="${OCTOPRINT_CMD:-}"
OCTOPRINT_VENV="${OCTOPRINT_VENV:-}"

resolve_octoprint_bin() {
  if [[ -n "$OCTOPRINT_CMD" ]]; then
    echo "$OCTOPRINT_CMD"
    return 0
  fi

  if [[ -n "$OCTOPRINT_VENV" ]]; then
    echo "$OCTOPRINT_VENV/bin/octoprint"
    return 0
  fi

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

  command -v octoprint 2>/dev/null || true
}

OCTOPRINT_BIN="$(resolve_octoprint_bin)"
NOHUP_OUT="${NOHUP_OUT:-/tmp/octoprint.nohup}"
OCTOPRINT_BASEDIR="${OCTOPRINT_BASEDIR:-$HOME/.octoprint}"
OCTOPRINT_LOG="${OCTOPRINT_LOG:-$OCTOPRINT_BASEDIR/logs/octoprint.log}"
SAFE_MARKER="$OCTOPRINT_BASEDIR/data/last_safe_mode"
WEBASSETS_DIR="$OCTOPRINT_BASEDIR/generated/webassets"
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

  readarray -t _pids <<<"$pids"
  if wait_pids_exit 30 "${_pids[@]}"; then
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

    if wait_pids_exit 10 "${_pids[@]}"; then
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
  clear_octoprint_log
  LOG_LINE_START=0

  echo "Clearing safe-mode marker (if present): $SAFE_MARKER"
  rm -f "$SAFE_MARKER" || true

  clear_octoprint_cache

  : > "$NOHUP_OUT"

  echo "Starting OctoPrint: $OCTOPRINT_BIN $OCTOPRINT_ARGS"
  read -r -a _octo_args <<< "$OCTOPRINT_ARGS"
  nohup "$OCTOPRINT_BIN" "${_octo_args[@]}" >"$NOHUP_OUT" 2>&1 &

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
  sleep 1
  if wait_for_log "tornado\.access - INFO - 200 GET \/api\/plugin\/octoprint_uptime" 120 1; then
    echo "uptime: detected API access (tornado.access GET /api/plugin/octoprint_uptime)"
  else
    echo "WARNING: No API GET for /api/plugin/octoprint_uptime observed within 120s; plugin may be disabled or navbar not enabled." >&2
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

