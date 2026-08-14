#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo ./update.sh" >&2
  exit 1
fi

APP_USER="${SUDO_USER:-pi}"
APP_DIR="/opt/volp-e"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[Volp-E] Updating app files without apt..."
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude 'models/*.tflite' \
  "$SOURCE_DIR/" "$APP_DIR/"

chmod +x "$APP_DIR/bin/start-face.sh"
chmod +x "$APP_DIR/bin/start-face-fb.sh"
chmod +x "$APP_DIR/bin/start-vision.sh"
chmod +x "$APP_DIR/update.sh"
chmod +x "$APP_DIR/brain/volpe_brain.py"
chmod +x "$APP_DIR/face/fb_face.py"
chmod +x "$APP_DIR/vision/face_tracker.py"
chmod +x "$APP_DIR/vision/debug_snapshot.py"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "[Volp-E] Refreshing systemd units..."
cp "$APP_DIR/systemd/volpe-brain.service" /etc/systemd/system/volpe-brain.service
cp "$APP_DIR/systemd/volpe-vision.service" /etc/systemd/system/volpe-vision.service
cp "$APP_DIR/systemd/volpe-face-fb.service" /etc/systemd/system/volpe-face-fb.service
cp "$APP_DIR/systemd/volpe-face.service" "/etc/systemd/system/volpe-face@.service"
sed -i "s/^User=.*/User=${APP_USER}/" /etc/systemd/system/volpe-vision.service

if [ ! -f /etc/default/volp-e ]; then
  cat > /etc/default/volp-e <<'DEFAULTS'
# Optional desktop brain URL, for example:
# VOLPE_EXTERNAL_BRAIN_URL=http://YOUR_PC_IP:8787
VOLPE_EXTERNAL_BRAIN_URL=
DEFAULTS
fi

systemctl daemon-reload
systemctl enable volpe-brain.service
systemctl enable volpe-vision.service
systemctl enable volpe-face-fb.service
systemctl disable "volpe-face@${APP_USER}.service" >/dev/null 2>&1 || true
systemctl disable getty@tty1.service >/dev/null 2>&1 || true

mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/volpe-autologin.conf <<GETTY
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${APP_USER} --noclear %I \$TERM
GETTY
systemctl daemon-reload

USER_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"
if [ -n "$USER_HOME" ] && [ -d "$USER_HOME" ]; then
  cat > "$USER_HOME/.bash_profile" <<'PROFILE'
# Volp-E face is now rendered by volpe-face-fb.service directly on /dev/fb0.
PROFILE
  chown "$APP_USER:$APP_USER" "$USER_HOME/.bash_profile"
fi

systemctl stop "volpe-face@${APP_USER}.service" >/dev/null 2>&1 || true
systemctl stop getty@tty1.service >/dev/null 2>&1 || true
pkill -f chromium-browser >/dev/null 2>&1 || true
pkill -f "/usr/lib/chromium" >/dev/null 2>&1 || true
systemctl restart volpe-brain.service
systemctl restart volpe-vision.service
systemctl restart volpe-face-fb.service

echo "[Volp-E] Update done."
echo "Check with:"
echo "  curl 'http://127.0.0.1:8765/api/state'"
