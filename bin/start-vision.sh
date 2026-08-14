#!/usr/bin/env bash
set -euo pipefail

APP_USER="${VOLPE_USER:-pi}"
VENV_PYTHON="/home/${APP_USER}/volpe-ai/bin/python"

export PYTHONPATH="/usr/lib/python3/dist-packages:${PYTHONPATH:-}"

if [ "${VOLPE_USE_VENV:-0}" = "1" ] && [ -x "$VENV_PYTHON" ]; then
  exec "$VENV_PYTHON" /opt/volp-e/vision/face_tracker.py
fi

exec /usr/bin/python3 /opt/volp-e/vision/face_tracker.py
