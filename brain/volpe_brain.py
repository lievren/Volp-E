#!/usr/bin/env python3
import base64
import json
import mimetypes
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
FACE_DIR = ROOT / "face"
STANDBY_AFTER_SECONDS = 300
EXTERNAL_BRAIN_URL = os.environ.get("VOLPE_EXTERNAL_BRAIN_URL", "").rstrip("/")
EXTERNAL_CHECK_INTERVAL = 10
EXTERNAL_TIMEOUT = 1.5
THINK_COOLDOWN_SECONDS = 12
MEMORY_MAX_EVENTS = 24
MEMORY_RECENT_SECONDS = 600
MEMORY_CLOSE_FACE_SIZE = 0.70
PERSONALITY_TICK_MIN_SECONDS = 0.25
FRAME_SIZE = (320, 240)
ROTATE_180 = True
LATEST_FRAME = Path("/tmp/volpe-latest-frame.jpg")
LATEST_FRAME_MAX_AGE_SECONDS = 8
FACE_RECENT_SECONDS = 2.5
STARTED_AT = time.time()
STATE = {
    "mode": "normal",
    "camera": "idle",
    "arduino": "not_configured",
    "vision": {
        "face": False,
        "x": 0.0,
        "y": 0.0,
        "size": 0.0,
        "last_seen": 0.0,
    },
    "standby_after": STANDBY_AFTER_SECONDS,
    "no_presence_since": STARTED_AT,
    "external_brain": {
        "configured": bool(EXTERNAL_BRAIN_URL),
        "url": EXTERNAL_BRAIN_URL,
        "status": "unknown" if EXTERNAL_BRAIN_URL else "not_configured",
        "last_check": 0.0,
        "last_ok": 0.0,
        "last_error": "",
        "last_analysis": None,
    },
    "thought": {
        "last_at": 0.0,
        "last_request": 0.0,
        "description": "",
        "mood": "neutral",
        "speech": "",
        "attention": None,
        "actions": [],
    },
    "memory": {
        "mood": "waking",
        "active_mood": "waking",
        "energy": 0.55,
        "curiosity": 0.45,
        "familiarity": 0.0,
        "attention": "boot",
        "last_tick": STARTED_AT,
        "events": [],
        "presence_count": 0,
        "last_presence_at": 0.0,
        "last_presence_lost_at": 0.0,
        "last_close_presence_at": 0.0,
        "last_standby_at": 0.0,
        "last_event": None,
        "summary": "Je viens de demarrer.",
    },
}


class VolpeHandler(BaseHTTPRequestHandler):
    server_version = "VolpEBrain/0.1"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, max-age=0")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self.update_standby()
            self.update_external_brain_status()
            self.update_memory_mood()
            self.send_json(STATE)
            return

        if parsed.path == "/api/external/check":
            self.update_external_brain_status(force=True)
            self.send_json({"ok": True, "external_brain": STATE["external_brain"]})
            return

        if parsed.path in {"/api/analyze_scene", "/api/think"}:
            self.update_external_brain_status(force=True)
            result = self.analyze_scene()
            self.send_json(result, 200 if result.get("ok") else 503)
            return

        if parsed.path == "/api/mode":
            mode = parse_qs(parsed.query).get("mode", [""])[0]
            if mode not in {"normal", "sleepy", "alert", "standby"}:
                self.send_json({"ok": False, "error": "mode must be normal, sleepy, alert, or standby"}, 400)
                return
            STATE["mode"] = mode
            if mode != "standby":
                STATE["no_presence_since"] = time.time()
            self.remember("mode_changed", f"Mode visage change vers {mode}.", mode=mode)
            self.send_json({"ok": True, "mode": mode})
            return

        if parsed.path == "/api/vision":
            query = parse_qs(parsed.query)
            face = query.get("face", ["0"])[0] == "1"
            STATE["camera"] = "tracking" if face else "searching"
            STATE["vision"]["face"] = face
            STATE["vision"]["x"] = self.parse_float(query.get("x", ["0"])[0], 0.0)
            STATE["vision"]["y"] = self.parse_float(query.get("y", ["0"])[0], 0.0)
            STATE["vision"]["size"] = self.parse_float(query.get("size", ["0"])[0], 0.0)
            now = time.time()
            was_face = bool(STATE["vision"].get("last_seen")) and now - float(STATE["vision"].get("last_seen") or 0.0) <= FACE_RECENT_SECONDS
            if face:
                STATE["vision"]["last_seen"] = now
                STATE["no_presence_since"] = now
                if not was_face:
                    self.remember("presence_arrived", "Une presence vient d'apparaitre.", x=STATE["vision"]["x"], y=STATE["vision"]["y"], size=STATE["vision"]["size"])
                if STATE["vision"]["size"] >= MEMORY_CLOSE_FACE_SIZE:
                    last_close = float(STATE["memory"].get("last_close_presence_at") or 0.0)
                    if now - last_close > 8:
                        self.remember("presence_close", "Une presence est proche de moi.", x=STATE["vision"]["x"], y=STATE["vision"]["y"], size=STATE["vision"]["size"])
            elif was_face and now - float(STATE["memory"].get("last_presence_lost_at") or 0.0) > 5:
                self.remember("presence_lost", "La presence vient de disparaitre du champ.")
            if face and STATE["mode"] != "sleepy":
                STATE["mode"] = "alert"
            elif not face and STATE["mode"] == "alert":
                STATE["mode"] = "normal"
            self.update_standby(now)
            self.update_memory_mood(now)
            if face:
                self.maybe_think_async(now)
            self.send_json({"ok": True, "vision": STATE["vision"]})
            return

        self.serve_static(parsed.path)

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            return
        self.serve_static(parsed.path, head_only=True)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    @classmethod
    def remember(cls, kind, description, **details):
        now = time.time()
        memory = STATE["memory"]
        event = {
            "at": now,
            "kind": kind,
            "description": description,
            "details": details,
        }
        memory["events"].append(event)
        memory["events"] = [
            item for item in memory["events"]
            if now - float(item.get("at") or 0.0) <= MEMORY_RECENT_SECONDS
        ][-MEMORY_MAX_EVENTS:]
        memory["last_event"] = event

        if kind == "presence_arrived":
            memory["presence_count"] += 1
            memory["last_presence_at"] = now
            memory["energy"] = cls.clamp01(float(memory.get("energy") or 0.0) + 0.10)
            memory["curiosity"] = cls.clamp01(float(memory.get("curiosity") or 0.0) + 0.12)
            memory["familiarity"] = cls.clamp01(float(memory.get("familiarity") or 0.0) + 0.04)
        elif kind == "presence_lost":
            memory["last_presence_lost_at"] = now
            memory["curiosity"] = cls.clamp01(float(memory.get("curiosity") or 0.0) + 0.06)
        elif kind == "presence_close":
            memory["last_close_presence_at"] = now
            memory["energy"] = cls.clamp01(float(memory.get("energy") or 0.0) + 0.06)
            memory["familiarity"] = cls.clamp01(float(memory.get("familiarity") or 0.0) + 0.03)
        elif kind == "standby_entered":
            memory["last_standby_at"] = now
            memory["energy"] = cls.clamp01(float(memory.get("energy") or 0.0) - 0.08)
        elif kind == "analysis_received":
            memory["curiosity"] = cls.clamp01(float(memory.get("curiosity") or 0.0) + 0.03)

        cls.update_memory_mood(now)

    @classmethod
    def update_memory_mood(cls, now=None):
        now = now or time.time()
        memory = STATE["memory"]
        face = bool(STATE["vision"]["face"])
        last_presence = float(memory.get("last_presence_at") or 0.0)
        last_close = float(memory.get("last_close_presence_at") or 0.0)
        last_lost = float(memory.get("last_presence_lost_at") or 0.0)
        idle_for = now - STATE["no_presence_since"]
        last_tick = float(memory.get("last_tick") or now)
        dt = max(PERSONALITY_TICK_MIN_SECONDS, min(8.0, now - last_tick))
        memory["last_tick"] = now

        energy = float(memory.get("energy") or 0.0)
        curiosity = float(memory.get("curiosity") or 0.0)
        familiarity = float(memory.get("familiarity") or 0.0)
        size = float(STATE["vision"].get("size") or 0.0)

        if face:
            energy += 0.055 * dt
            curiosity += (0.040 + size * 0.025) * dt
            familiarity += 0.010 * dt
            attention = "person_close" if size >= MEMORY_CLOSE_FACE_SIZE else "person"
        elif STATE["mode"] == "standby" or idle_for >= STANDBY_AFTER_SECONDS:
            energy -= 0.030 * dt
            curiosity -= 0.025 * dt
            attention = "dream"
        elif last_lost and now - last_lost < 45:
            energy += 0.010 * dt
            curiosity += 0.012 * dt
            attention = "searching"
        else:
            energy -= 0.018 * dt
            curiosity -= 0.016 * dt
            attention = "ambient"

        energy = cls.clamp01(energy)
        curiosity = cls.clamp01(curiosity)
        familiarity = cls.clamp01(familiarity)
        memory["energy"] = round(energy, 3)
        memory["curiosity"] = round(curiosity, 3)
        memory["familiarity"] = round(familiarity, 3)
        memory["attention"] = attention

        if STATE["mode"] == "standby" or idle_for >= STANDBY_AFTER_SECONDS:
            mood = "dreaming" if energy < 0.45 else "calm"
            summary = "Je suis en veille et je garde une trace calme de ce qui m'entoure."
        elif face and now - last_close < 20:
            mood = "happy" if familiarity >= 0.35 and curiosity >= 0.60 else "attentive"
            summary = "Une presence proche retient mon attention."
        elif face or now - last_presence < 20:
            mood = "happy" if familiarity >= 0.45 else "curious"
            summary = "Je suis attentif a une presence recente."
        elif last_lost and now - last_lost < 45:
            mood = "searching"
            summary = "Je viens de perdre une presence et je surveille encore."
        elif energy < 0.22:
            mood = "sleepy"
            summary = "Je suis calme et mon energie baisse doucement."
        else:
            mood = "calm"
            summary = "La scene est calme, je reste disponible."

        memory["mood"] = mood
        memory["active_mood"] = mood
        memory["summary"] = summary

    @staticmethod
    def clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def external_health_url():
        if not EXTERNAL_BRAIN_URL:
            return ""
        return f"{EXTERNAL_BRAIN_URL}/health"

    @staticmethod
    def external_analyze_url():
        if not EXTERNAL_BRAIN_URL:
            return ""
        return f"{EXTERNAL_BRAIN_URL}/analyze"

    @classmethod
    def update_external_brain_status(cls, force=False):
        external = STATE["external_brain"]
        if not EXTERNAL_BRAIN_URL:
            external["status"] = "not_configured"
            return
        now = time.time()
        if not force and now - external["last_check"] < EXTERNAL_CHECK_INTERVAL:
            return
        external["last_check"] = now
        try:
            with urlopen(cls.external_health_url(), timeout=EXTERNAL_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            external["status"] = "online" if payload.get("ok") else "error"
            external["last_ok"] = now if payload.get("ok") else external["last_ok"]
            external["last_error"] = "" if payload.get("ok") else "health returned ok=false"
        except Exception as exc:
            external["status"] = "offline"
            external["last_error"] = str(exc)

    @classmethod
    def analyze_scene(cls):
        external = STATE["external_brain"]
        if not EXTERNAL_BRAIN_URL:
            return {"ok": False, "error": "external brain is not configured"}
        STATE["thought"]["last_request"] = time.time()
        image = cls.capture_frame()
        if image is None:
            return {"ok": False, "error": "cannot capture camera frame"}
        state_snapshot = cls.build_state_snapshot()
        payload = {
            "source": "volp-e",
            "timestamp": time.time(),
            "state": state_snapshot,
            "image_format": "jpg",
            "image_b64": base64.b64encode(image).decode("ascii"),
        }
        request = Request(
            cls.external_analyze_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=4.0) as response:
                result = json.loads(response.read().decode("utf-8"))
            external["status"] = "online"
            external["last_ok"] = time.time()
            external["last_error"] = ""
            external["last_analysis"] = result
            cls.apply_analysis(result, state_snapshot)
            return {"ok": True, "external_brain": external, "analysis": result}
        except Exception as exc:
            external["status"] = "offline"
            external["last_error"] = str(exc)
            return {"ok": False, "error": str(exc), "external_brain": external}

    @staticmethod
    def build_state_snapshot():
        now = time.time()
        vision = dict(STATE["vision"])
        last_seen = float(vision.get("last_seen") or 0.0)
        vision_age = None if last_seen <= 0 else now - last_seen
        face_recent = bool(vision.get("face")) or (vision_age is not None and vision_age <= FACE_RECENT_SECONDS)
        return {
            "mode": STATE["mode"],
            "camera": STATE["camera"],
            "vision": vision,
            "vision_age": vision_age,
            "face_recent": face_recent,
            "memory": dict(STATE["memory"]),
            "snapshot_at": now,
        }

    @staticmethod
    def apply_analysis(result, state_snapshot=None):
        thought = STATE["thought"]
        thought["last_at"] = time.time()
        thought["description"] = str(result.get("description", ""))
        thought["mood"] = str(result.get("mood", "neutral"))
        thought["speech"] = str(result.get("speech", ""))
        thought["attention"] = result.get("attention")
        thought["actions"] = result.get("actions", [])
        VolpeHandler.remember(
            "analysis_received",
            thought["speech"] or thought["description"] or "Analyse recue du cerveau externe.",
            mood=thought["mood"],
            suggested_mode=result.get("suggested_mode", ""),
        )

        suggested_mode = result.get("suggested_mode")
        if suggested_mode in {"normal", "sleepy", "alert", "standby"}:
            current_face = bool(STATE["vision"]["face"])
            snapshot_face = bool((state_snapshot or {}).get("face_recent"))
            attention = result.get("attention") or {}
            priority = attention.get("priority") if isinstance(attention, dict) else None
            stale_no_presence = suggested_mode == "normal" and priority == "none" and (current_face or snapshot_face)
            if stale_no_presence:
                STATE["mode"] = "alert"
                thought["actions"] = thought["actions"] + [{"type": "face_mode", "mode": "alert", "reason": "active_presence_override"}]
                return
            if suggested_mode != "standby":
                STATE["no_presence_since"] = time.time()
            STATE["mode"] = suggested_mode

    @staticmethod
    def capture_frame():
        try:
            if LATEST_FRAME.exists() and time.time() - LATEST_FRAME.stat().st_mtime <= LATEST_FRAME_MAX_AGE_SECONDS:
                return LATEST_FRAME.read_bytes()
        except Exception:
            pass

        try:
            import cv2
        except Exception as exc:
            print(f"[Volp-E brain] OpenCV unavailable: {exc}", flush=True)
            return None

        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        cap.release()
        if not ok:
            return None
        frame = cv2.resize(frame, FRAME_SIZE, interpolation=cv2.INTER_AREA)
        if ROTATE_180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        if not ok:
            return None
        return encoded.tobytes()

    @classmethod
    def maybe_think_async(cls, now):
        if not EXTERNAL_BRAIN_URL:
            return
        if now - STATE["thought"]["last_request"] < THINK_COOLDOWN_SECONDS:
            return
        STATE["thought"]["last_request"] = now
        try:
            import threading

            thread = threading.Thread(target=cls.analyze_scene, daemon=True)
            thread.start()
        except Exception as exc:
            STATE["external_brain"]["last_error"] = str(exc)

    @staticmethod
    def parse_float(raw, default):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def update_standby(now=None):
        now = now or time.time()
        if STATE["vision"]["face"]:
            return
        idle_for = now - STATE["no_presence_since"]
        if idle_for >= STANDBY_AFTER_SECONDS and STATE["mode"] not in {"sleepy", "standby"}:
            STATE["mode"] = "standby"

    def serve_static(self, request_path, head_only=False):
        relative = request_path.lstrip("/") or "index.html"
        target = (FACE_DIR / relative).resolve()
        if not str(target).startswith(str(FACE_DIR.resolve())) or not target.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)


def main():
    address = ("127.0.0.1", 8765)
    print(f"Volp-E brain listening on http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, VolpeHandler).serve_forever()


if __name__ == "__main__":
    main()
