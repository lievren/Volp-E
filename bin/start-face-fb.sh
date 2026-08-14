#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${VOLPE_FB_FACE_LOG:-/tmp/volpe-fb-face.log}"
: > "$LOG_FILE"
echo "[Volp-E face] $(date -Is) starting framebuffer face" >> "$LOG_FILE"

if [ -w /dev/tty1 ]; then
  printf '\033[?25l\033[2J\033[H' > /dev/tty1 || true
  setterm -cursor off -blank 0 -powerdown 0 -clear all > /dev/tty1 2>/dev/null || true
fi

exec /usr/bin/python3 /opt/volp-e/face/fb_face.py >> "$LOG_FILE" 2>&1
