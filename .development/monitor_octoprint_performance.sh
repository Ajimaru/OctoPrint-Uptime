#!/usr/bin/env bash
set -euo pipefail

# Lightweight OctoPrint performance monitor for long-running plugin tests.
# Writes logs to the repo-local .logs/ folder (gitignored).
# Intended for development use only.

usage() {
  cat <<'EOF'
Usage: .development/monitor_octoprint_performance.sh [options]

Options:
  --interval SECONDS     Sampling interval (default: 10)
  --duration SECONDS     Stop after this many seconds (default: 0 = run until Ctrl+C)
  --pid PID              Monitor this OctoPrint PID (auto-detect if omitted)
  --port PORT            Port to resolve PID from (via ss), default: OCTOPRINT_PORT or 5000
  --basedir PATH          OctoPrint basedir (default: $OCTOPRINT_BASEDIR or ~/.octoprint)
  --octoprint-log PATH   Path to octoprint.log (default: basedir/logs/octoprint.log)
  --data-dir PATH        Plugin data dir to monitor (default: basedir/data/octoprint_uptime)
  --out-prefix NAME      Output file prefix (default: octoprint_perf)
  --once                 Take one sample and exit
  -h, --help             Show this help

Environment:
  OCTOPRINT_BASEDIR, OCTOPRINT_LOG, OCTOPRINT_PORT

Outputs (created under .logs/):
  - <prefix>_<timestamp>.csv  (metrics)
  - <prefix>_<timestamp>.log  (human-readable)

Notes:
  - For meaningful performance numbers, disable verbose debug logging after verifying behavior.
  - PID auto-detection is best-effort and prefers a process listening on the chosen port.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
REPO_ROOT=""
if command -v git >/dev/null 2>&1; then
  REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

INTERVAL_S=10
DURATION_S=0
ONCE=0
PID=""
OUT_PREFIX="octoprint_perf"

OCTOPRINT_PORT_DEFAULT="${OCTOPRINT_PORT:-5000}"
OCTOPRINT_PORT="$OCTOPRINT_PORT_DEFAULT"

OCTOPRINT_BASEDIR_DEFAULT="${OCTOPRINT_BASEDIR:-$HOME/.octoprint}"
OCTOPRINT_BASEDIR="$OCTOPRINT_BASEDIR_DEFAULT"

OCTOPRINT_LOG_DEFAULT="${OCTOPRINT_LOG:-$OCTOPRINT_BASEDIR/logs/octoprint.log}"
OCTOPRINT_LOG_PATH="$OCTOPRINT_LOG_DEFAULT"

PLUGIN_DATA_DIR_DEFAULT="$OCTOPRINT_BASEDIR/data/octoprint_uptime"
PLUGIN_DATA_DIR="$PLUGIN_DATA_DIR_DEFAULT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval)
      INTERVAL_S="$2"; shift 2 ;;
    --duration)
      DURATION_S="$2"; shift 2 ;;
    --pid)
      PID="$2"; shift 2 ;;
    --port)
      OCTOPRINT_PORT="$2"; shift 2 ;;
    --basedir)
      OCTOPRINT_BASEDIR="$2"; shift 2 ;;
    --octoprint-log)
      OCTOPRINT_LOG_PATH="$2"; shift 2 ;;
    --data-dir)
      PLUGIN_DATA_DIR="$2"; shift 2 ;;
    --out-prefix)
      OUT_PREFIX="$2"; shift 2 ;;
    --once)
      ONCE=1; shift ;;
    -h|--help|help)
      usage; exit 0 ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$INTERVAL_S" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "ERROR: --interval must be a number" >&2
  exit 2
fi
if ! [[ "$DURATION_S" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "ERROR: --duration must be a number" >&2
  exit 2
fi

LOG_DIR="$REPO_ROOT/.logs"
mkdir -p "$LOG_DIR"

START_TS="$(date +%Y%m%d_%H%M%S)"
CSV_PATH="$LOG_DIR/${OUT_PREFIX}_${START_TS}.csv"
LOG_PATH="$LOG_DIR/${OUT_PREFIX}_${START_TS}.log"

log() {
  printf '[monitor] %s\n' "$*" | tee -a "$LOG_PATH" >/dev/null
}

find_pid_by_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | awk -v port=":${port}" '$0 ~ port { if (match($0,/pid=([0-9]+)/,m)) { print m[1]; exit } }'
  fi
}

find_pid_by_pgrep() {
  local uid
  uid="$(id -u)"
  if command -v pgrep >/dev/null 2>&1; then
    {
      pgrep -u "$uid" -f "octoprint.*serve" 2>/dev/null || true
      pgrep -u "$uid" -f "python(3)? .* -m octoprint.*serve" 2>/dev/null || true
    } | awk '!seen[$0]++' | head -n 1
  fi
}

resolve_pid() {
  if [[ -n "$PID" ]]; then
    echo "$PID"
    return 0
  fi

  local by_port
  by_port="$(find_pid_by_port "$OCTOPRINT_PORT" || true)"
  if [[ -n "$by_port" ]]; then
    echo "$by_port"
    return 0
  fi

  local by_pgrep
  by_pgrep="$(find_pid_by_pgrep || true)"
  if [[ -n "$by_pgrep" ]]; then
    echo "$by_pgrep"
    return 0
  fi

  echo ""
}

write_header() {
  echo "timestamp_iso,pid,cpu_percent,mem_percent,rss_kb,vsz_kb,etimes_s,threads,fd_count,octoprint_log_bytes,plugin_log_tail_lines,data_dir_bytes,json_count,json_bytes,tmp_count" >"$CSV_PATH"
}

safe_stat_bytes() {
  local path="$1"
  if [[ -e "$path" ]]; then
    stat -c %s "$path" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

count_fds() {
  local pid="$1"
  if [[ -n "$pid" && -d "/proc/$pid/fd" ]]; then
    find "/proc/$pid/fd" -maxdepth 1 -mindepth 1 -printf '.' 2>/dev/null | wc -c
  else
    echo 0
  fi
}

data_dir_metrics() {
  local dir="$1"
  local data_bytes=0
  local json_count=0
  local json_bytes=0
  local tmp_count=0

  if [[ -d "$dir" ]]; then
    data_bytes=$(du -sb "$dir" 2>/dev/null | awk '{print $1}' || echo 0)

    json_count=$(find "$dir" -maxdepth 1 -type f -name 'history_*.json' -printf '.' 2>/dev/null | wc -c)
    tmp_count=$(find "$dir" -maxdepth 1 -type f -name 'history_*.tmp' -printf '.' 2>/dev/null | wc -c)

    if command -v stat >/dev/null 2>&1; then
      json_bytes=$(find "$dir" -maxdepth 1 -type f -name 'history_*.json' -print0 2>/dev/null | xargs -0 -r stat -c %s | awk '{s+=$1} END{print s+0}')
    fi
  fi

  echo "$data_bytes,$json_count,$json_bytes,$tmp_count"
}

plugin_log_tail_lines() {
  local path="$1"
  if [[ -f "$path" ]]; then
    tail -n 200 "$path" 2>/dev/null | grep -ci 'octoprint_uptime' || echo 0
  else
    echo 0
  fi
}

sample_once() {
  local pid="$1"
  local ts
  ts="$(date -Iseconds)"

  local cpu="" mem="" rss="" vsz="" etimes="" nlwp=""
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    local ps_out
    ps_out="$(ps -p "$pid" -o %cpu=,%mem=,rss=,vsz=,etimes=,nlwp= 2>/dev/null || true)"
    cpu="$(echo "$ps_out" | awk '{print $1}' | tr -d ' ')"
    mem="$(echo "$ps_out" | awk '{print $2}' | tr -d ' ')"
    rss="$(echo "$ps_out" | awk '{print $3}' | tr -d ' ')"
    vsz="$(echo "$ps_out" | awk '{print $4}' | tr -d ' ')"
    etimes="$(echo "$ps_out" | awk '{print $5}' | tr -d ' ')"
    nlwp="$(echo "$ps_out" | awk '{print $6}' | tr -d ' ')"
  else
    pid=""
  fi

  local fd_count
  fd_count="$(count_fds "$pid")"

  local log_bytes
  log_bytes="$(safe_stat_bytes "$OCTOPRINT_LOG_PATH")"

  local tail_lines
  tail_lines="$(plugin_log_tail_lines "$OCTOPRINT_LOG_PATH")"

  local dd
  dd="$(data_dir_metrics "$PLUGIN_DATA_DIR")"
  local data_bytes json_count json_bytes tmp_count
  data_bytes="$(echo "$dd" | awk -F, '{print $1}')"
  json_count="$(echo "$dd" | awk -F, '{print $2}')"
  json_bytes="$(echo "$dd" | awk -F, '{print $3}')"
  tmp_count="$(echo "$dd" | awk -F, '{print $4}')"

  echo "$ts,${pid:-},${cpu:-},${mem:-},${rss:-},${vsz:-},${etimes:-},${nlwp:-},${fd_count:-0},${log_bytes:-0},${tail_lines:-0},${data_bytes:-0},${json_count:-0},${json_bytes:-0},${tmp_count:-0}" >>"$CSV_PATH"

  log "ts=$ts pid=${pid:-n/a} cpu=${cpu:-n/a}% mem=${mem:-n/a}% rss=${rss:-n/a}KB threads=${nlwp:-n/a} fds=${fd_count:-0} log_bytes=${log_bytes:-0} data_bytes=${data_bytes:-0} json_count=${json_count:-0} tmp_count=${tmp_count:-0}"
}

write_header
log "Repo root: $REPO_ROOT"
log "Output CSV: $CSV_PATH"
log "Output LOG: $LOG_PATH"
log "OctoPrint basedir: $OCTOPRINT_BASEDIR"
log "OctoPrint log: $OCTOPRINT_LOG_PATH"
log "Plugin data dir: $PLUGIN_DATA_DIR"
log "Interval: ${INTERVAL_S}s Duration: ${DURATION_S}s Once: ${ONCE}"

START_EPOCH="$(date +%s)"

while true; do
  RESOLVED_PID="$(resolve_pid)"
  if [[ -z "$RESOLVED_PID" ]]; then
    log "WARNING: OctoPrint PID not found (port=$OCTOPRINT_PORT). Retrying..."
  fi

  sample_once "$RESOLVED_PID"

  if (( ONCE == 1 )); then
    break
  fi

  if awk -v d="$DURATION_S" 'BEGIN { exit !(d > 0) }'; then
    NOW_EPOCH="$(date +%s)"
    ELAPSED=$((NOW_EPOCH - START_EPOCH))
    if (( ELAPSED >= ${DURATION_S%.*} )); then
      log "Reached duration (${DURATION_S}s). Exiting."
      break
    fi
  fi

  sleep "$INTERVAL_S"
done

