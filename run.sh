#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$APP_DIR/.venv/bin/python"
APP_CLI="$APP_DIR/.venv/bin/network-diagnostics-report-tool"
LOG_DIR="$HOME/.local/state/network-diagnostics-report-tool"
LOG_FILE="$LOG_DIR/launcher.log"
mkdir -p "$LOG_DIR"

{
  echo "[$(date --iso-8601=seconds)] Launch requested"
  echo "App dir: $APP_DIR"
} >> "$LOG_FILE"

# Offline-safe launcher: do NOT run pip install here. The network diagnostics
# tool must be able to open while DNS/internet is broken so it can diagnose it.
if [ ! -x "$VENV_PYTHON" ]; then
  notify-send --app-name='Network Diagnostics Report Tool' --icon=network-error \
    'Network Diagnostics setup missing' \
    'The local Python environment is missing. Ask Hermes to repair the Network Diagnostics app setup.' 2>/dev/null || true
  echo "Missing venv python: $VENV_PYTHON" >> "$LOG_FILE"
  exit 1
fi

if [ -x "$APP_CLI" ]; then
  exec "$APP_CLI"
fi

# Fallback if the entry-point wrapper is missing but the package source is present.
export PYTHONPATH="$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV_PYTHON" -m net_troubleshooter
