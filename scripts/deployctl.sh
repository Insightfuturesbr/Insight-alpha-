#!/usr/bin/env bash
set -euo pipefail

# Simulate a Docker deploy locally using /bin/bash
# - Caches each run under .deploy_cache/<RUN_ID>
# - Starts Gunicorn via bash, logs to cache, writes PID
# - Health-checks /health and supports kill+restart cycle

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CACHE_DIR="$ROOT_DIR/.deploy_cache"
APP_MODULE="wsgi:app"

# Defaults (can be overridden by env or .env)
: "${PORT:=8080}"
: "${WORKERS:=2}"
: "${THREADS:=2}"
: "${ENV:=production}"
: "${FLASK_ENV:=production}"

ensure_cache() { mkdir -p "$CACHE_DIR"; }

gen_run_id() {
  date +"%Y%m%d-%H%M%S" | awk '{printf "%s-%06d\n", $0, srand()%1000000}'
}

log() { echo "[$(date +"%H:%M:%S")] $*"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

pick_gunicorn() {
  if [ -x "$ROOT_DIR/venv/bin/gunicorn" ]; then
    echo "$ROOT_DIR/venv/bin/gunicorn"
  elif has_cmd gunicorn; then
    echo "gunicorn"
  else
    if python3 - >/dev/null 2>&1 <<'PY'
import importlib
import sys
sys.exit(0 if importlib.util.find_spec('gunicorn') else 1)
PY
    then
      echo "python3 -m gunicorn"
    else
      echo ""  # not available
    fi
  fi
}

health_check() {
  local port="$1"
  if [ "${NO_BIND:-}" = "1" ]; then
    # In no-bind mode, treat as healthy after test_client check
    return 0
  fi
  if has_cmd curl; then
    curl -fsS "http://127.0.0.1:${port}/health" || return 1
  else
    python3 - "$port" <<'PY'
import json, sys, urllib.request
port = int(sys.argv[1])
with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
    print(r.read().decode())
PY
  fi
}

start() {
  ensure_cache
  local run_id="${RUN_ID:-$(gen_run_id)}"
  local run_dir="$CACHE_DIR/$run_id"
  mkdir -p "$run_dir"

  # Merge env: .env (if present) + current shell
  if [ -f "$ROOT_DIR/.env" ]; then
    # shellcheck disable=SC1090
    source "$ROOT_DIR/.env"
  fi

  local log_path="$run_dir/app.log"
  local pid_path="$run_dir/pid"
  local env_dump="$run_dir/env"
  env | sort > "$env_dump"

  local gunicorn
  gunicorn="$(pick_gunicorn)"

  local cmd
  if [ "${NO_BIND:-}" = "1" ]; then
    log "NO_BIND=1: running test_client health check via /bin/bash"
    cmd="ENV=${ENV} FLASK_ENV=${FLASK_ENV} \
      python3 - <<'PY'
from app.webserver import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/health')
    print(r.status_code, r.get_json())
PY"
  elif [ -n "$gunicorn" ]; then
    cmd="ENV=${ENV} FLASK_ENV=${FLASK_ENV} PORT=${PORT} WORKERS=${WORKERS} THREADS=${THREADS} \
      MPLBACKEND=Agg MPLCONFIGDIR=$ROOT_DIR/.cache/mpl \
      exec ${gunicorn} -b 0.0.0.0:${PORT} -w ${WORKERS} -k gthread --threads ${THREADS} \
      --timeout 120 --access-logfile - --error-logfile - ${APP_MODULE}"
  else
    log "Gunicorn not available; falling back to Flask dev server"
    cmd="ENV=${ENV} FLASK_ENV=${FLASK_ENV} PORT=${PORT} \
      MPLBACKEND=Agg MPLCONFIGDIR=$ROOT_DIR/.cache/mpl \
      python3 - <<'PY'
from wsgi import app
app.run(host='0.0.0.0', port=int(${PORT}), debug=False)
PY"
  fi

  mkdir -p "$ROOT_DIR/.cache/mpl"
  mkdir -p "$ROOT_DIR/uploads" "$ROOT_DIR/outputs"

  log "RUN_ID=$run_id"
  log "Starting via /bin/bash ..."
  nohup bash -lc "$cmd" > "$log_path" 2>&1 & echo $! > "$pid_path"
  sleep 1

  # Wait for health
  local deadline=$((SECONDS+30))
  while (( SECONDS < deadline )); do
    if health_check "$PORT" >/dev/null 2>&1; then
      log "Healthy at http://127.0.0.1:${PORT}/health"
      echo "$run_id"
      return 0
    fi
    sleep 1
  done

  log "Health check failed. See $log_path"
  echo "$run_id"
  return 2
}

status() {
  local run_id="$1"
  local pid_path="$CACHE_DIR/$run_id/pid"
  [ -f "$pid_path" ] || { echo "no such RUN_ID $run_id"; return 1; }
  local pid; pid="$(cat "$pid_path")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "$run_id running (pid=$pid)"
  else
    echo "$run_id not running"
    return 1
  fi
}

stop() {
  local run_id="$1"
  local pid_path="$CACHE_DIR/$run_id/pid"
  [ -f "$pid_path" ] || { echo "no such RUN_ID $run_id"; return 0; }
  local pid; pid="$(cat "$pid_path")"
  log "Stopping RUN_ID=$run_id pid=$pid"
  kill "$pid" 2>/dev/null || true
  for _ in {1..10}; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1
  done
  log "Force killing pid=$pid"
  kill -9 "$pid" 2>/dev/null || true
}

tail_logs() {
  local run_id="$1"
  tail -n 200 -f "$CACHE_DIR/$run_id/app.log"
}

restart_until_healthy() {
  local attempts="${1:-3}"
  local last_id=""
  for i in $(seq 1 "$attempts"); do
    log "Attempt $i/$attempts"
    last_id="$(RUN_ID="" start)" || true
    if health_check "$PORT" >/dev/null 2>&1; then
      log "Healthy after attempt $i. RUN_ID=$last_id"
      echo "$last_id"
      return 0
    fi
    log "Unhealthy. Stopping RUN_ID=$last_id"
    stop "$last_id" || true
    sleep 1
  done
  log "Failed after $attempts attempts. Last RUN_ID=$last_id"
  echo "$last_id"
  return 2
}

usage() {
  cat <<USAGE
Usage: $0 <command> [args]
Commands:
  start                 Start a new run; print RUN_ID
  stop <RUN_ID>         Stop a run by id
  status <RUN_ID>       Show status of a run
  tail <RUN_ID>         Tail logs of a run
  restart               Killbug cycle: retry start until healthy (3 attempts)
USAGE
}

main() {
  local cmd="${1:-}"; shift || true
  case "$cmd" in
    start) start ;;
    stop) stop "${1:-}" ;;
    status) status "${1:-}" ;;
    tail) tail_logs "${1:-}" ;;
    restart) restart_until_healthy "${1:-3}" ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
