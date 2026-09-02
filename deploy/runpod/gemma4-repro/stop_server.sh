#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"
pid_path="$RUNS_DIR/${PROFILE_SLUG}_vllm_server.pid"
[[ -f "$pid_path" ]] || { echo "No recorded server PID"; exit 0; }
pid="$(<"$pid_path")"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
fi
rm -f "$pid_path"
echo "OK: server stopped"
