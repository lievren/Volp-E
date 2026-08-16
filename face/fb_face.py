#!/usr/bin/env python3
import json
import math
import os
import random
import struct
import time
from pathlib import Path
from urllib.request import urlopen


API_STATE = "http://127.0.0.1:8765/api/state"
FB_PATH = "/dev/fb0"
SYS_FB = "/sys/class/graphics/fb0"
FPS = 40
ROTATE_180 = True
STATE_POLL_INTERVAL = 0.11
STATE_TIMEOUT = 0.035
THOUGHT_VISIBLE_SECONDS = 45
RAW_EYE_DIRS = {
    16: Path(__file__).resolve().parent / "assets" / "eyes-rgb565",
    24: Path(__file__).resolve().parent / "assets" / "eyes-bgr24",
    32: Path(__file__).resolve().parent / "assets" / "eyes-bgrx32",
}
EYE_FRAME_NAMES = {
    "center": "yeux_BASE.raw",
    "closed": "yeux_FERME.raw",
    "left1": "yeux_GAUCHE1.raw",
    "left2": "yeux_GAUCHE2.raw",
    "right1": "yeux_DROITE1.raw",
    "right2": "yeux_DROITE2.raw",
    "up_left": "regard_haut_gauche.raw",
    "up_right": "regard_haut_droit.raw",
    "down_left": "regard_bas_gauche.raw",
    "down_right": "regard_bas_droite.raw",
}

FONT = {
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    ".": ["0", "0", "0", "0", "0", "0", "1"],
    ",": ["0", "0", "0", "0", "0", "1", "1"],
    ":": ["0", "1", "0", "0", "0", "1", "0"],
    "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "'": ["1", "1", "0", "0", "0", "0", "0"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
}

LETTER_FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["111", "010", "010", "010", "010", "010", "111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}
FONT.update(LETTER_FONT)


def read_text(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return default


def framebuffer_info():
    virtual = read_text(os.path.join(SYS_FB, "virtual_size"), "800,480")
    width, height = [int(part) for part in virtual.split(",", 1)]
    bpp = int(read_text(os.path.join(SYS_FB, "bits_per_pixel"), "16"))
    stride = int(read_text(os.path.join(SYS_FB, "stride"), str(width * max(1, bpp // 8))))
    return width, height, bpp, stride


def rgb565(r, g, b):
    return struct.pack("<H", ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))


def pixel_bytes(color, bpp):
    r, g, b = color
    if bpp == 16:
        return rgb565(r, g, b)
    if bpp == 24:
        return bytes((b, g, r))
    return bytes((b, g, r, 0))


class Canvas:
    def __init__(self, width, height, bpp, stride):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.bytes_per_pixel = max(1, bpp // 8)
        self.stride = stride
        self.buffer = bytearray(stride * height)
        self.black = pixel_bytes((5, 3, 1), bpp)
        self.color_cache = {(5, 3, 1): self.black}

    def clear(self):
        row = self.black * self.width
        if len(row) < self.stride:
            row += self.black[:1] * (self.stride - len(row))
        for y in range(self.height):
            start = y * self.stride
            self.buffer[start:start + self.stride] = row[:self.stride]

    def blit_raw_frame(self, frame):
        expected = self.width * self.height * self.bytes_per_pixel
        if len(frame) != expected:
            return False
        row_bytes = self.width * self.bytes_per_pixel
        if self.stride == row_bytes:
            self.buffer[:expected] = frame
            return True
        for y in range(self.height):
            src = y * row_bytes
            dst = y * self.stride
            self.buffer[dst:dst + row_bytes] = frame[src:src + row_bytes]
        return True

    def put(self, x, y, color):
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        if ROTATE_180:
            x = self.width - 1 - x
            y = self.height - 1 - y
        start = y * self.stride + x * self.bytes_per_pixel
        data = self.color_cache.get(color)
        if data is None:
            data = pixel_bytes(color, self.bpp)
            self.color_cache[color] = data
        self.buffer[start:start + self.bytes_per_pixel] = data

    def put_cached(self, x, y, data):
        if ROTATE_180:
            x = self.width - 1 - x
            y = self.height - 1 - y
        start = y * self.stride + x * self.bytes_per_pixel
        self.buffer[start:start + self.bytes_per_pixel] = data

    def ellipse(self, cx, cy, rx, ry, color, outline=None, outline_width=1):
        x0 = max(0, int(cx - rx - outline_width))
        x1 = min(self.width - 1, int(cx + rx + outline_width))
        y0 = max(0, int(cy - ry - outline_width))
        y1 = min(self.height - 1, int(cy + ry + outline_width))
        fill_data = self.color_cache.get(color)
        if fill_data is None:
            fill_data = pixel_bytes(color, self.bpp)
            self.color_cache[color] = fill_data
        outline_data = None
        if outline:
            outline_data = self.color_cache.get(outline)
            if outline_data is None:
                outline_data = pixel_bytes(outline, self.bpp)
                self.color_cache[outline] = outline_data
        for y in range(y0, y1 + 1):
            dy = (y - cy) / max(1, ry)
            for x in range(x0, x1 + 1):
                dx = (x - cx) / max(1, rx)
                d = dx * dx + dy * dy
                if d <= 1:
                    self.put_cached(x, y, fill_data)
                elif outline and d <= 1 + outline_width / max(2, min(rx, ry)):
                    self.put_cached(x, y, outline_data)

    def line(self, x0, y0, x1, y1, color):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy


def fetch_state(last_state):
    try:
        with urlopen(API_STATE, timeout=STATE_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return last_state


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def normalize_text(text):
    table = str.maketrans({
        "à": "a", "á": "a", "â": "a", "ä": "a", "ã": "a",
        "ç": "c",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "ö": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "œ": "oe",
    })
    return " ".join(str(text or "").translate(table).upper().split())


def text_width(text, scale):
    width = 0
    for char in text:
        glyph = FONT.get(char, FONT[" "])
        width += (max(len(row) for row in glyph) + 1) * scale
    return max(0, width - scale)


def draw_char(canvas, x, y, char, color, scale):
    glyph = FONT.get(char, FONT[" "])
    for row_i, row in enumerate(glyph):
        for col_i, value in enumerate(row):
            if value == "1":
                for yy in range(scale):
                    for xx in range(scale):
                        canvas.put(x + col_i * scale + xx, y + row_i * scale + yy, color)
    return (max(len(row) for row in glyph) + 1) * scale


def draw_text(canvas, text, x, y, color=(214, 244, 255), scale=3):
    cursor = int(x)
    for char in text:
        cursor += draw_char(canvas, cursor, int(y), char, color, scale)


def wrap_text(text, max_width, scale):
    words = normalize_text(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if text_width(candidate, scale) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:2]


def thought_text(state):
    thought = state.get("thought", {}) if isinstance(state, dict) else {}
    seen_at = float(thought.get("last_at") or 0.0)
    if not seen_at or time.time() - seen_at > THOUGHT_VISIBLE_SECONDS:
        return ""
    return thought.get("speech") or thought.get("description") or ""


def draw_eye(canvas, cx, cy, rx, ry, look_x, look_y, big=True, sleepy=False, alert=False):
    if sleepy:
        ry *= 0.22
    if alert:
        rx *= 1.03
        ry *= 1.05

    glow = (18, 104, 190) if alert else (8, 72, 158)
    core = (142, 246, 255)
    rim = (205, 255, 255)
    iris = (220, 151, 28)
    shadow = (2, 9, 16)

    canvas.ellipse(cx, cy, rx * 1.10, ry * 1.07, glow)
    canvas.ellipse(cx, cy, rx, ry, core, rim, 2)

    fx = cx + look_x * rx * 0.66
    fy = cy + look_y * ry * 0.54
    canvas.ellipse(fx, fy, rx * 0.22, ry * 0.18, iris)
    canvas.ellipse(fx, fy, rx * 0.092, ry * 0.078, shadow)
    canvas.ellipse(fx + rx * 0.028, fy - ry * 0.03, rx * 0.024, ry * 0.022, (220, 255, 255))

    if sleepy:
        canvas.line(cx - rx * 0.70, cy, cx + rx * 0.70, cy, (192, 255, 255))


def draw_standby(canvas, now):
    cx = canvas.width * 0.50
    cy = canvas.height * 0.49
    scale = min(canvas.width, canvas.height)

    pulse = 1.0 + math.sin(now * 1.8) * 0.08
    canvas.ellipse(cx, cy, scale * 0.135 * pulse, scale * 0.135 * pulse, (0, 36, 64))
    canvas.ellipse(cx, cy, scale * 0.084 * pulse, scale * 0.084 * pulse, (0, 210, 245))
    canvas.ellipse(cx, cy, scale * 0.034, scale * 0.034, (255, 220, 132))

    for ring, speed, tilt, color in (
        (0.22, 0.65, 0.42, (0, 138, 180)),
        (0.33, -0.42, 0.32, (62, 214, 255)),
        (0.43, 0.25, 0.22, (255, 214, 120)),
    ):
        old_x = None
        old_y = None
        for i in range(56):
            a = i / 55 * math.pi * 2 + now * speed
            wobble = math.sin(a * 3 + now * 0.8) * scale * 0.012
            x = cx + math.cos(a) * (scale * ring + wobble)
            y = cy + math.sin(a) * scale * ring * tilt
            if old_x is not None and i % 2 == 0:
                canvas.line(old_x, old_y, x, y, color)
            old_x, old_y = x, y

    for i in range(90):
        band = i / 90
        angle = band * math.pi * 9 + now * (0.55 + band * 0.35)
        radius = scale * (0.10 + band * 0.43)
        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius * (0.28 + band * 0.16)
        color = (130, 238, 255) if i % 4 else (255, 225, 140)
        size = 1.2 + (i % 3) * 0.35
        canvas.ellipse(x, y, size, size, color)


def draw_thought(canvas, state):
    if state.get("mode") == "standby":
        return
    text = thought_text(state)
    if not text:
        return
    scale = 3 if canvas.width < 900 else 4
    lines = wrap_text(text, int(canvas.width * 0.86), scale)
    if not lines:
        return
    line_h = 9 * scale
    start_y = int(canvas.height - (len(lines) * line_h) - canvas.height * 0.035)
    for i, line in enumerate(lines):
        w = text_width(line, scale)
        x = int((canvas.width - w) / 2)
        y = start_y + i * line_h
        draw_text(canvas, line, x + scale, y + scale, (18, 35, 46), scale)
        draw_text(canvas, line, x, y, (214, 244, 255), scale)


def load_eye_frames(width, height, bpp):
    root = RAW_EYE_DIRS.get(bpp)
    if root is None:
        print(f"[Volp-E fb] PNG eye frames disabled: unsupported {bpp}bpp framebuffer", flush=True)
        return {}
    frame_dir = root / f"{width}x{height}"
    frames = {}
    for key, name in EYE_FRAME_NAMES.items():
        path = frame_dir / name
        try:
            frames[key] = path.read_bytes()
        except OSError:
            pass
    if "center" not in frames or "closed" not in frames:
        print(f"[Volp-E fb] missing PNG eye frames in {frame_dir}", flush=True)
        return {}
    print(f"[Volp-E fb] loaded {len(frames)} PNG eye frames from {frame_dir}", flush=True)
    return frames


def choose_eye_frame(frames, mode, look_x, look_y, blink_closed):
    if not frames:
        return None
    if blink_closed:
        return frames.get("closed")
    if mode == "sleepy":
        return frames.get("closed")
    if look_y < -0.45:
        return frames.get("up_left" if look_x < -0.12 else "up_right")
    if look_y > 0.45:
        return frames.get("down_left" if look_x < -0.12 else "down_right")
    if look_x < -0.58:
        return frames.get("left2")
    if look_x < -0.22:
        return frames.get("left1")
    if look_x > 0.58:
        return frames.get("right2")
    if look_x > 0.22:
        return frames.get("right1")
    return frames.get("center")


def main():
    width, height, bpp, stride = framebuffer_info()
    canvas = Canvas(width, height, bpp, stride)
    eye_frames = load_eye_frames(width, height, bpp)
    last_state = {"mode": "normal", "vision": {"face": False, "x": 0.0, "y": 0.0}}
    target_x = 0.0
    target_y = 0.0
    look_x = 0.0
    look_y = 0.0
    next_random = 0.0
    next_state_poll = 0.0
    next_blink = time.time() + random.uniform(2.8, 6.5)
    blink_until = 0.0
    print(f"[Volp-E fb] framebuffer {width}x{height} {bpp}bpp stride={stride}", flush=True)

    with open(FB_PATH, "r+b", buffering=0) as fb:
        while True:
            now = time.time()
            if now >= next_state_poll:
                last_state = fetch_state(last_state)
                next_state_poll = now + STATE_POLL_INTERVAL
            state = last_state
            mode = state.get("mode", "normal")
            vision = state.get("vision", {})
            face_seen = bool(vision.get("face"))
            if face_seen:
                target_x = clamp(float(vision.get("x", 0.0) or 0.0), -1.0, 1.0)
                target_y = clamp(float(vision.get("y", 0.0) or 0.0), -1.0, 1.0)
            elif now >= next_random:
                spread = 0.78 if mode == "alert" else 0.48
                target_x = random.uniform(-spread, spread)
                target_y = random.uniform(-spread * 0.68, spread * 0.68)
                next_random = now + (0.35 if mode == "alert" else 1.1)

            if face_seen:
                ease = 0.34 if mode == "alert" else 0.28
            else:
                ease = 0.16 if mode == "alert" else 0.085
            look_x += (target_x - look_x) * ease
            look_y += (target_y - look_y) * ease

            if mode != "standby" and now >= next_blink:
                blink_until = now + random.uniform(0.10, 0.16)
                next_blink = now + random.uniform(3.0, 7.5)
            blink_closed = now < blink_until

            canvas.clear()
            if mode == "standby":
                draw_standby(canvas, now)
            else:
                frame = choose_eye_frame(eye_frames, mode, look_x, look_y, blink_closed)
                if not frame or not canvas.blit_raw_frame(frame):
                    wobble_x = math.sin(now * (43 if mode == "alert" else 0.9)) * (3 if mode == "alert" else 0.6)
                    wobble_y = math.cos(now * (39 if mode == "alert" else 0.75)) * (2 if mode == "alert" else 0.4)
                    scale = min(width / 800, height / 480)
                    center_y = height * 0.47 + wobble_y
                    left_cx = width * 0.30 + wobble_x
                    right_cx = width * 0.70 + wobble_x
                    sleepy = mode == "sleepy"
                    alert = mode == "alert"
                    draw_eye(canvas, left_cx, center_y + 2 * scale, 84 * scale, 156 * scale, look_x, look_y, False, sleepy, alert)
                    draw_eye(canvas, right_cx, center_y - 6 * scale, 90 * scale, 164 * scale, look_x, look_y, True, sleepy, alert)
                draw_thought(canvas, state)

            fb.seek(0)
            fb.write(canvas.buffer)
            time.sleep(1 / FPS)


if __name__ == "__main__":
    main()
