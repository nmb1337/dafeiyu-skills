#!/usr/bin/env bash
# Restart a QQ/OneBot bridge WITHOUT losing the reply of the turn in flight.
# The bridge blocks on the agent's answer while the agent works, so run this detached:
# it sleeps past the expected turn length, then kills the listening pid and execs the bridge.
#
# Adjust PY / BRIDGE / WORKDIR for the install (resolve the venv via references/runtime-layout.md).
set -u
SLEEP_S="${1:-150}"
PY="$HERMES_HOME/installs/<install-id>/environments/<env-hash>/venv/Scripts/python.exe"
BRIDGE="scripts/qq-bridge.py"
WORKDIR="$HERMES_HOME"
LOG="$HERMES_HOME/logs/qq-bridge.log"
PORT=8790

sleep "$SLEEP_S"
PID=$(netstat -ano | grep "127.0.0.1:$PORT" | grep LISTENING | awk '{print $5}' | head -1)
echo "[restart] old pid=$PID $(date)" >> "$LOG"
if [ -n "${PID:-}" ]; then taskkill //F //PID "$PID" >/dev/null 2>&1; sleep 2; fi
cd "$WORKDIR" || exit 1
export API_SERVER_KEY="$(grep -m1 '^API_SERVER_KEY=' .env | cut -d= -f2-)"
export PYTHONIOENCODING=utf-8
echo "[restart] starting new bridge $(date)" >> "$LOG"
exec "$PY" -u "$BRIDGE" >> "$LOG" 2>&1
