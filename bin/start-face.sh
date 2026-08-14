#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:0}"
URL="${VOLPE_FACE_URL:-file:///opt/volp-e/face/index.html}"
BRAIN_URL="${VOLPE_BRAIN_URL:-http://127.0.0.1:8765/api/state}"
PROFILE_DIR="${VOLPE_CHROME_PROFILE:-/tmp/volpe-chromium-profile}"
LOG_FILE="${VOLPE_CHROME_LOG:-/tmp/volpe-chromium.log}"

rm -rf "$PROFILE_DIR"
mkdir -p "$PROFILE_DIR"
: > "$LOG_FILE"
echo "[Volp-E face] $(date -Is) starting Chromium kiosk" >> "$LOG_FILE"
echo "[Volp-E face] URL=$URL" >> "$LOG_FILE"
echo "[Volp-E face] BRAIN_URL=$BRAIN_URL" >> "$LOG_FILE"

xset s off || true
xset -dpms || true
xset s noblank || true

if command -v unclutter >/dev/null 2>&1; then
  unclutter -idle 0.1 -root >/dev/null 2>&1 &
fi

CHROMIUM=""
for candidate in /usr/lib/chromium/chromium /usr/lib/chromium-browser/chromium-browser chromium-browser chromium; do
  if [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; then
    CHROMIUM="$candidate"
    break
  fi
done

if [ -z "$CHROMIUM" ]; then
  echo "Chromium is not installed. Run install.sh first." >&2
  exit 1
fi

for _ in $(seq 1 120); do
  if curl -fsS "$BRAIN_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

exec "$CHROMIUM" \
  --kiosk "$URL" \
  --user-data-dir="$PROFILE_DIR" \
  --window-size=800,480 \
  --start-fullscreen \
  --lang=fr-FR \
  --no-first-run \
  --no-default-browser-check \
  --enable-logging=stderr \
  --v=0 \
  --noerrdialogs \
  --test-type \
  --no-sandbox \
  --disable-application-cache \
  --disable-translate \
  --disable-infobars \
  --disable-gpu \
  --disable-extensions \
  --disable-sync \
  --disable-background-networking \
  --disable-session-crashed-bubble \
  --disable-component-update \
  --disable-dev-shm-usage \
  --renderer-process-limit=1 \
  --enable-low-end-device-mode \
  --disable-features=Translate,TranslateUI,MediaRouter,OptimizationHints \
  --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 \
  >> "$LOG_FILE" 2>&1
