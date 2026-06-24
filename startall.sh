#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/.local/startall-logs"
PID_DIR="$ROOT_DIR/.local/startall-pids"
ROOT_VENV_PY="$ROOT_DIR/.venv/bin/python"
COMFYUI_VENV_PY="$ROOT_DIR/modals/ComfyUI/venv/bin/python"
COMFYUI_ARGS_DEFAULT="--listen 0.0.0.0 --port 8188 --cpu"

mkdir -p "$LOG_DIR" "$PID_DIR"

start_bg() {
  local name="$1"
  shift
  local log_file="$LOG_DIR/${name}.log"
  local pid_file="$PID_DIR/${name}.pid"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      # Ensure it's our process (or matches expected patterns like python/node/redis/minio) and not a recycled PID
      local cmdline=""
      if [[ -f "/proc/$pid/cmdline" ]]; then
        cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || echo "")
      fi
      if [[ -n "$cmdline" ]]; then
        if [[ "$cmdline" == *"$name"* ]] || [[ "$cmdline" == *"python"* ]] || [[ "$cmdline" == *"node"* ]] || [[ "$cmdline" == *"uvicorn"* ]] || [[ "$cmdline" == *"minio"* ]] || [[ "$cmdline" == *"redis"* ]] || [[ "$cmdline" == *"ollama"* ]]; then
          echo "$name already running (pid $pid)"
          return 0
        fi
      fi
    fi
  fi

  echo "starting $name"
  "$@" >"$log_file" 2>&1 &
  echo $! >"$pid_file"
}

start_redis() {
  if command -v redis-server >/dev/null 2>&1; then
    start_bg redis redis-server --save "" --appendonly no
  elif command -v docker >/dev/null 2>&1; then
    echo "Starting redis via docker..."
    docker start redis || docker run -d -p 6379:6379 --name redis redis:alpine
  else
    echo "redis-server and docker not found; skipping redis"
  fi
}

start_backend() {
  start_bg backend bash -c "cd '$ROOT_DIR/backend' && source '$ROOT_DIR/.venv/bin/activate' && exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
}

start_frontend() {
  start_bg frontend bash -c "export NVM_DIR=\"\$HOME/.nvm\"; [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"; cd '$ROOT_DIR/frontend' && exec npm run dev"
}

start_worker() {
  if [[ -f "$ROOT_DIR/backend/start_worker.sh" ]]; then
    start_bg worker bash -c "cd '$ROOT_DIR/backend' && ./start_worker.sh"
  elif [[ -x "$ROOT_VENV_PY" ]]; then
    start_bg worker bash -c "export NVM_DIR=\"\$HOME/.nvm\"; [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"; cd '$ROOT_DIR/backend' && source '$ROOT_DIR/.venv/bin/activate' && exec rq worker ad_jobs --with-scheduler"
  else
    start_bg worker bash -c "export NVM_DIR=\"\$HOME/.nvm\"; [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"; cd '$ROOT_DIR/backend' && exec rq worker ad_jobs --with-scheduler"
  fi
}

start_ollama() {
  if command -v ollama >/dev/null 2>&1; then
    start_bg ollama ollama serve
  fi
}


start_comfyui() {
  local comfyui_dir="$ROOT_DIR/modals/ComfyUI"
  local comfyui_args="${COMFYUI_ARGS:-$COMFYUI_ARGS_DEFAULT}"
  if [[ -f "$comfyui_dir/main.py" ]]; then
    if [[ -x "$COMFYUI_VENV_PY" ]]; then
      start_bg comfyui bash -c "cd '$comfyui_dir' && exec '$COMFYUI_VENV_PY' main.py $comfyui_args"
    elif [[ -x "$ROOT_VENV_PY" ]]; then
      start_bg comfyui bash -c "cd '$comfyui_dir' && exec '$ROOT_VENV_PY' main.py $comfyui_args"
    else
      echo "no python venv found for comfyui; skipping comfyui"
    fi
  fi
}


start_postgres() {
  if command -v postgres >/dev/null 2>&1 || command -v psql >/dev/null 2>&1; then
    if command -v postgresqlctl >/dev/null 2>&1; then
      start_bg postgres postgresqlctl -D /var/lib/postgresql/data start
    elif command -v pg_ctl >/dev/null 2>&1; then
      start_bg postgres pg_ctl -D /var/lib/postgresql/data start
    else
      echo "postgres not found; skipping postgres"
    fi
  else
    echo "postgres-server not found; skipping postgres (using SQLite by default)"
  fi
}

start_minio() {
  if command -v minio >/dev/null 2>&1; then
    mkdir -p "$ROOT_DIR/.local/minio-data"
    MINIO_ROOT_USER=creoad MINIO_ROOT_PASSWORD=creoad123 \
      start_bg minio minio server "$ROOT_DIR/.local/minio-data" --address :9000 --console-address :9001
  else
    echo "minio not found; skipping minio"
  fi
}

echo "CreoAd local startall"
start_redis
start_postgres
start_ollama
start_comfyui
start_minio
start_backend
start_worker
start_frontend

echo
echo "Waiting for services to become healthy (this may take up to 60 seconds)..."
MAX_WAIT=60
wait_count=0
while [ $wait_count -lt $MAX_WAIT ]; do
  if curl -s http://localhost:8000/health > /dev/null; then
    if curl -s http://localhost:8000/health | grep -q '"comfyui":"online"'; then
      break
    fi
  fi
  sleep 2
  wait_count=$((wait_count + 2))
done

if [ $wait_count -ge $MAX_WAIT ]; then
  echo "Warning: Some services (like ComfyUI) may still be starting up. Check logs in $LOG_DIR"
else
  echo "All critical services are online and ready!"
fi

echo
echo "Services started or already running. Logs are in $LOG_DIR"
echo "Backend:   http://localhost:8000"
echo "Worker:    rq worker ad_jobs"
echo "Frontend:  http://localhost:3000"
echo "Ollama:    http://localhost:11434"
echo "ComfyUI:   http://localhost:8188"
echo "Redis:     localhost:6379"
echo "Postgres:  localhost:5432 (optional)"
echo "MinIO:     http://localhost:9000 (API) | http://localhost:9001 (Console)"
