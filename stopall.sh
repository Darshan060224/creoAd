#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$ROOT_DIR/.local/startall-pids"

if [[ ! -d "$PID_DIR" ]]; then
  echo "No process ID directory found at $PID_DIR. Nothing to stop."
  exit 0
fi

# Find all PID files
shopt -s nullglob
pid_files=("$PID_DIR"/*.pid)

if [[ ${#pid_files[@]} -eq 0 ]]; then
  echo "No running services found (no PID files in $PID_DIR)."
  exit 0
fi

kill_child_processes() {
  local parent_pid=$1
  # Get all child PIDs recursively
  local children
  children=$(pgrep -P "$parent_pid" 2>/dev/null || true)
  for child in $children; do
    kill_child_processes "$child"
  done
  if kill -0 "$parent_pid" 2>/dev/null; then
    kill -15 "$parent_pid" 2>/dev/null || true
  fi
}

for pid_file in "${pid_files[@]}"; do
  name=$(basename "$pid_file" .pid)
  if [[ -f "$pid_file" ]]; then
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping $name (PID: $pid)..."
      
      # Kill children recursively first
      kill_child_processes "$pid"
      
      # Kill the main process
      kill -15 "$pid" 2>/dev/null || true
      
      # Wait up to 5 seconds for it to exit
      for i in {1..5}; do
        if ! kill -0 "$pid" 2>/dev/null; then
          break
        fi
        sleep 1
      done
      
      # Force kill if still running
      if kill -0 "$pid" 2>/dev/null; then
        echo "$name (PID: $pid) did not exit gracefully, force killing..."
        kill -9 "$pid" 2>/dev/null || true
      fi
    else
      echo "$name is not running (stale PID: $pid)."
    fi
    # Remove the PID file
    rm -f "$pid_file"
  fi
done

echo "All services stopped."
