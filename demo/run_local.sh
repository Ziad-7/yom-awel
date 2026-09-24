#!/usr/bin/env bash
# One-command local demo: the API (APP_ENV=local, SQLite and local files) and the web app.
# Needs no secrets. If a git-ignored .env exists at the repository root, only the feedback
# variables below are read from it, so a GEMINI_API_KEY there turns on Gemini feedback.
#
# Usage: demo/run_local.sh        (Ctrl+C stops both processes)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
ENV_FILE="$ROOT/.env"
FEEDBACK_VARIABLES=(GEMINI_API_KEY GEMINI_MODEL FEEDBACK_MODE)

log() { printf '[run_local] %s\n' "$*"; }

# Reads KEY=VALUE lines for the allowed keys only; the file is never executed and no value
# is printed.
load_feedback_env() {
  [[ -f "$ENV_FILE" ]] || { log "no .env found: deterministic feedback"; return 0; }
  local line key value allowed
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Z_][A-Z0-9_]*)=(.*)$ ]] || continue
    key="${BASH_REMATCH[2]}"
    value="${BASH_REMATCH[3]}"
    value="${value%\"}"; value="${value#\"}"; value="${value%\'}"; value="${value#\'}"
    for allowed in "${FEEDBACK_VARIABLES[@]}"; do
      if [[ "$key" == "$allowed" && -n "$value" ]]; then
        export "$key=$value"
        log "loaded $key from .env"
      fi
    done
  done < "$ENV_FILE"
}

wait_for() {
  local name="$1" url="$2" deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  until curl -fs -o /dev/null "$url"; do
    if ((SECONDS >= deadline)); then
      log "$name did not become healthy at $url within ${HEALTH_TIMEOUT_SECONDS}s"
      return 1
    fi
    sleep 1
  done
  log "$name healthy: $url"
}

PIDS=()
stop_all() {
  local pid
  for pid in "${PIDS[@]}"; do
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  done
}
trap stop_all EXIT
trap 'exit 130' INT TERM

command -v uv >/dev/null || { log "uv is required: https://docs.astral.sh/uv/"; exit 1; }
command -v npm >/dev/null || { log "npm (Node.js) is required"; exit 1; }

load_feedback_env
mkdir -p "$ROOT/.local"
export APP_ENV=local
export LOCAL_DATABASE_PATH="$ROOT/.local/learning.sqlite3"
export LOCAL_SECRET_PATH="$ROOT/.local/session.key"
export CORS_ORIGINS="http://127.0.0.1:$WEB_PORT"
export API_ORIGIN="http://127.0.0.1:$API_PORT"

if [[ ! -d "$ROOT/apps/web/node_modules" ]]; then
  log "installing web dependencies (npm ci)"
  (cd "$ROOT/apps/web" && npm ci --no-audit --no-fund)
fi

log "starting API on $API_ORIGIN"
set -m
(cd "$ROOT/services/api" && exec uv run uvicorn api.index:app --host 127.0.0.1 --port "$API_PORT") &
PIDS+=("$!")
log "starting web app on http://127.0.0.1:$WEB_PORT"
(cd "$ROOT/apps/web" && exec npm run dev -- --port "$WEB_PORT") &
PIDS+=("$!")
set +m

wait_for "API" "$API_ORIGIN/api/v1/health"
wait_for "web app" "http://127.0.0.1:$WEB_PORT/"
wait_for "web proxy to API" "http://127.0.0.1:$WEB_PORT/api/v1/health"

log "demo ready: open http://127.0.0.1:$WEB_PORT"
log "presenter files: $ROOT/demo/files (see demo/README.md)"
wait -n
