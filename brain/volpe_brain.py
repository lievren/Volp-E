#!/usr/bin/env python3
import base64
import io
import json
import mimetypes
import os
import re
import subprocess
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
FACE_DIR = ROOT / "face"
PERSONALITY_FILE = Path(os.environ.get("VOLPE_PERSONALITY_FILE", ROOT / "config" / "personality.json"))


DEFAULT_PERSONALITY = {
    "name": "Volp-E",
    "pronunciation": "Volpi",
    "profile": "curious_companion",
    "description": "Petit compagnon attentif, curieux et expressif.",
    "tone": {
        "energy_baseline": 0.55,
    },
    "speech": {
        "enabled": True,
        "min_interval_seconds": 4.0,
        "think_cooldown_seconds": 12.0,
        "voice_gain": 0.5,
    },
    "memory": {
        "max_events": 24,
        "recent_seconds": 600,
        "standby_after_seconds": 300,
        "sleepy_after_seconds": 600,
        "close_face_size": 0.70,
        "presence_energy_gain": 0.10,
        "presence_curiosity_gain": 0.12,
        "presence_familiarity_gain": 0.04,
        "presence_lost_curiosity_gain": 0.06,
        "presence_close_energy_gain": 0.06,
        "presence_close_familiarity_gain": 0.03,
        "standby_energy_loss": 0.08,
        "analysis_curiosity_gain": 0.03,
        "face_energy_gain_per_second": 0.055,
        "face_curiosity_gain_per_second": 0.040,
        "face_familiarity_gain_per_second": 0.010,
        "standby_energy_loss_per_second": 0.030,
        "standby_curiosity_loss_per_second": 0.025,
        "searching_energy_gain_per_second": 0.010,
        "searching_curiosity_gain_per_second": 0.012,
        "ambient_energy_loss_per_second": 0.018,
        "ambient_curiosity_loss_per_second": 0.016,
    },
    "attention": {
        "face_close_size": 0.72,
        "face_medium_size": 0.38,
        "position_deadzone": 0.28,
    },
    "expressions": {},
}


def deep_merge(default, override):
    merged = dict(default)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_personality():
    try:
        with PERSONALITY_FILE.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except Exception as exc:
        print(f"[Volp-E personality] using defaults: {exc}", flush=True)
        return DEFAULT_PERSONALITY
    return deep_merge(DEFAULT_PERSONALITY, loaded)


def personality_float(section, key, default):
    try:
        return float(PERSONALITY.get(section, {}).get(key, default))
    except (TypeError, ValueError):
        return float(default)


def personality_int(section, key, default):
    return int(personality_float(section, key, default))


PERSONALITY = load_personality()
STANDBY_AFTER_SECONDS = personality_float("memory", "standby_after_seconds", 300)
SLEEPY_AFTER_SECONDS = personality_float("memory", "sleepy_after_seconds", 600)
EXTERNAL_BRAIN_URL = os.environ.get("VOLPE_EXTERNAL_BRAIN_URL", "").rstrip("/")
EXTERNAL_CHECK_INTERVAL = 10
EXTERNAL_TIMEOUT = 1.5
EXTERNAL_TTS_TIMEOUT = 6.0
THINK_COOLDOWN_SECONDS = personality_float("speech", "think_cooldown_seconds", 12)
SPEECH_MIN_INTERVAL_SECONDS = personality_float("speech", "min_interval_seconds", 4)
VOICE_GAIN = max(0.0, min(1.0, personality_float("speech", "voice_gain", 0.5)))
SPEECH_WAV_PATH = Path("/tmp/volpe-speech.wav")
APLAY_DEVICE = os.environ.get("VOLPE_APLAY_DEVICE", "").strip()
MEMORY_MAX_EVENTS = personality_int("memory", "max_events", 24)
MEMORY_RECENT_SECONDS = personality_float("memory", "recent_seconds", 600)
MEMORY_CLOSE_FACE_SIZE = personality_float("memory", "close_face_size", 0.70)
MEMORY_PRESENCE_ENERGY_GAIN = personality_float("memory", "presence_energy_gain", 0.10)
MEMORY_PRESENCE_CURIOSITY_GAIN = personality_float("memory", "presence_curiosity_gain", 0.12)
MEMORY_PRESENCE_FAMILIARITY_GAIN = personality_float("memory", "presence_familiarity_gain", 0.04)
MEMORY_LOST_CURIOSITY_GAIN = personality_float("memory", "presence_lost_curiosity_gain", 0.06)
MEMORY_CLOSE_ENERGY_GAIN = personality_float("memory", "presence_close_energy_gain", 0.06)
MEMORY_CLOSE_FAMILIARITY_GAIN = personality_float("memory", "presence_close_familiarity_gain", 0.03)
MEMORY_STANDBY_ENERGY_LOSS = personality_float("memory", "standby_energy_loss", 0.08)
MEMORY_ANALYSIS_CURIOSITY_GAIN = personality_float("memory", "analysis_curiosity_gain", 0.03)
MEMORY_FACE_ENERGY_GAIN = personality_float("memory", "face_energy_gain_per_second", 0.055)
MEMORY_FACE_CURIOSITY_GAIN = personality_float("memory", "face_curiosity_gain_per_second", 0.040)
MEMORY_FACE_FAMILIARITY_GAIN = personality_float("memory", "face_familiarity_gain_per_second", 0.010)
MEMORY_STANDBY_ENERGY_LOSS_PER_SECOND = personality_float("memory", "standby_energy_loss_per_second", 0.030)
MEMORY_STANDBY_CURIOSITY_LOSS_PER_SECOND = personality_float("memory", "standby_curiosity_loss_per_second", 0.025)
MEMORY_SEARCHING_ENERGY_GAIN = personality_float("memory", "searching_energy_gain_per_second", 0.010)
MEMORY_SEARCHING_CURIOSITY_GAIN = personality_float("memory", "searching_curiosity_gain_per_second", 0.012)
MEMORY_AMBIENT_ENERGY_LOSS = personality_float("memory", "ambient_energy_loss_per_second", 0.018)
MEMORY_AMBIENT_CURIOSITY_LOSS = personality_float("memory", "ambient_curiosity_loss_per_second", 0.016)
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
    "sleepy_after": SLEEPY_AFTER_SECONDS,
    "no_presence_since": STARTED_AT,
    "personality": {
        "name": PERSONALITY.get("name", "Volp-E"),
        "pronunciation": PERSONALITY.get("pronunciation", "Volpi"),
        "profile": PERSONALITY.get("profile", "curious_companion"),
        "description": PERSONALITY.get("description", ""),
        "config_path": str(PERSONALITY_FILE),
        "tone": PERSONALITY.get("tone", {}),
        "speech": PERSONALITY.get("speech", {}),
        "expressions": PERSONALITY.get("expressions", {}),
    },
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
    "voice": {
        "enabled": os.environ.get("VOLPE_VOICE_ENABLED", "1") != "0" and bool(PERSONALITY.get("speech", {}).get("enabled", True)),
        "status": "idle",
        "last_at": 0.0,
        "last_text": "",
        "last_engine": "",
        "last_desktop_engine": "",
        "last_audio_path": "",
        "last_audio_bytes": 0,
        "volume_gain": VOICE_GAIN,
        "last_command": "",
        "last_result": "",
        "last_error": "",
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

        if parsed.path == "/api/personality":
            self.send_json({"ok": True, "personality": PERSONALITY})
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

        if parsed.path == "/api/say":
            query = parse_qs(parsed.query)
            text = query.get("text", [""])[0]
            if not text:
                self.send_json({"ok": False, "error": "missing text"}, 400)
                return
            force = query.get("force", ["0"])[0] == "1"
            sync = query.get("sync", ["0"])[0] == "1"
            if sync:
                spoken_text = self.prepare_speech_text(text)
                if not spoken_text:
                    self.send_json({"ok": False, "error": "empty prepared text"}, 400)
                    return
                STATE["voice"]["last_at"] = time.time()
                STATE["voice"]["last_text"] = spoken_text
                self.speak_text(spoken_text)
            else:
                self.maybe_speak(text, force=force)
            self.send_json({"ok": True, "voice": STATE["voice"]})
            return

        if parsed.path == "/api/voice/test":
            text = parse_qs(parsed.query).get("text", ["Test vocal Volp-E"])[0]
            spoken_text = self.prepare_speech_text(text)
            STATE["voice"]["last_at"] = time.time()
            STATE["voice"]["last_text"] = spoken_text
            self.speak_text(spoken_text)
            self.send_json({"ok": STATE["voice"].get("status") != "error", "voice": STATE["voice"]})
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
            if face:
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
            memory["energy"] = cls.clamp01(float(memory.get("energy") or 0.0) + MEMORY_PRESENCE_ENERGY_GAIN)
            memory["curiosity"] = cls.clamp01(float(memory.get("curiosity") or 0.0) + MEMORY_PRESENCE_CURIOSITY_GAIN)
            memory["familiarity"] = cls.clamp01(float(memory.get("familiarity") or 0.0) + MEMORY_PRESENCE_FAMILIARITY_GAIN)
        elif kind == "presence_lost":
            memory["last_presence_lost_at"] = now
            memory["curiosity"] = cls.clamp01(float(memory.get("curiosity") or 0.0) + MEMORY_LOST_CURIOSITY_GAIN)
        elif kind == "presence_close":
            memory["last_close_presence_at"] = now
            memory["energy"] = cls.clamp01(float(memory.get("energy") or 0.0) + MEMORY_CLOSE_ENERGY_GAIN)
            memory["familiarity"] = cls.clamp01(float(memory.get("familiarity") or 0.0) + MEMORY_CLOSE_FAMILIARITY_GAIN)
        elif kind == "standby_entered":
            memory["last_standby_at"] = now
            memory["energy"] = cls.clamp01(float(memory.get("energy") or 0.0) - MEMORY_STANDBY_ENERGY_LOSS)
        elif kind == "analysis_received":
            memory["curiosity"] = cls.clamp01(float(memory.get("curiosity") or 0.0) + MEMORY_ANALYSIS_CURIOSITY_GAIN)

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
            energy += MEMORY_FACE_ENERGY_GAIN * dt
            curiosity += (MEMORY_FACE_CURIOSITY_GAIN + size * 0.025) * dt
            familiarity += MEMORY_FACE_FAMILIARITY_GAIN * dt
            attention = "person_close" if size >= MEMORY_CLOSE_FACE_SIZE else "person"
        elif STATE["mode"] == "standby" or idle_for >= STANDBY_AFTER_SECONDS:
            energy -= MEMORY_STANDBY_ENERGY_LOSS_PER_SECOND * dt
            curiosity -= MEMORY_STANDBY_CURIOSITY_LOSS_PER_SECOND * dt
            attention = "dream"
        elif STATE["mode"] == "sleepy" or idle_for >= SLEEPY_AFTER_SECONDS:
            energy -= MEMORY_AMBIENT_ENERGY_LOSS * dt * 0.55
            curiosity -= MEMORY_AMBIENT_CURIOSITY_LOSS * dt * 0.55
            attention = "resting"
        elif last_lost and now - last_lost < 45:
            energy += MEMORY_SEARCHING_ENERGY_GAIN * dt
            curiosity += MEMORY_SEARCHING_CURIOSITY_GAIN * dt
            attention = "searching"
        else:
            energy -= MEMORY_AMBIENT_ENERGY_LOSS * dt
            curiosity -= MEMORY_AMBIENT_CURIOSITY_LOSS * dt
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
        elif STATE["mode"] == "sleepy" or idle_for >= SLEEPY_AFTER_SECONDS:
            mood = "sleepy"
            summary = "Je suis endormi, mais je reste doucement a l'ecoute."
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

    @staticmethod
    def external_speak_url():
        if not EXTERNAL_BRAIN_URL:
            return ""
        return f"{EXTERNAL_BRAIN_URL}/speak"

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
            "personality": dict(STATE["personality"]),
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
        VolpeHandler.maybe_speak(thought["speech"] or thought["description"])

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

    @classmethod
    def maybe_speak(cls, text, force=False):
        voice = STATE["voice"]
        if not voice.get("enabled"):
            return
        spoken_text = cls.prepare_speech_text(text)
        if not spoken_text:
            return
        now = time.time()
        if not force and spoken_text == voice.get("last_text") and now - float(voice.get("last_at") or 0.0) < 30:
            return
        if not force and now - float(voice.get("last_at") or 0.0) < SPEECH_MIN_INTERVAL_SECONDS:
            return
        voice["last_at"] = now
        voice["last_text"] = spoken_text
        voice["status"] = "queued"
        try:
            threading.Thread(target=cls.speak_text, args=(spoken_text,), daemon=True).start()
        except Exception as exc:
            voice["status"] = "error"
            voice["last_error"] = str(exc)

    @staticmethod
    def prepare_speech_text(text):
        text = " ".join(str(text or "").split())
        if not text:
            return ""
        # Pronunciation only: keep displayed text as Volp-E, but say "Volpi".
        pronunciation = str(PERSONALITY.get("pronunciation") or "Volpi").strip() or "Volpi"
        text = re.sub(r"\bvolp\s*[- ]?\s*e\b", pronunciation, text, flags=re.IGNORECASE)
        return text

    @classmethod
    def speak_text(cls, text):
        voice = STATE["voice"]
        voice["status"] = "speaking"
        voice["last_error"] = ""
        voice["last_result"] = ""
        print(f"[Volp-E voice] speaking request: {text}", flush=True)
        if EXTERNAL_BRAIN_URL:
            try:
                print(f"[Volp-E voice] requesting desktop voice: {cls.external_speak_url()}", flush=True)
                audio, desktop_engine = cls.request_external_speech(text)
                if audio:
                    audio = cls.apply_wav_gain(audio, VOICE_GAIN)
                    SPEECH_WAV_PATH.write_bytes(audio)
                    print(f"[Volp-E voice] desktop audio received: engine={desktop_engine}, bytes={len(audio)}, file={SPEECH_WAV_PATH}", flush=True)
                    cls.play_wav(SPEECH_WAV_PATH)
                    voice["last_engine"] = "desktop"
                    voice["last_desktop_engine"] = desktop_engine
                    voice["last_audio_path"] = str(SPEECH_WAV_PATH)
                    voice["last_audio_bytes"] = len(audio)
                    voice["status"] = "idle"
                    return
            except Exception as exc:
                voice["last_error"] = f"desktop voice failed: {exc}"
                print(f"[Volp-E voice] {voice['last_error']}", flush=True)
        try:
            print("[Volp-E voice] falling back to espeak-ng", flush=True)
            cls.speak_espeak(text)
            voice["last_engine"] = "espeak-ng"
            voice["last_desktop_engine"] = ""
            voice["last_audio_path"] = ""
            voice["last_audio_bytes"] = 0
            voice["status"] = "idle"
        except Exception as exc:
            voice["status"] = "error"
            voice["last_error"] = str(exc)

    @classmethod
    def request_external_speech(cls, text):
        payload = {"text": text, "voice": "fr"}
        request = Request(
            cls.external_speak_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=EXTERNAL_TTS_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "external speech returned ok=false"))
        audio_b64 = result.get("audio_b64", "")
        if not audio_b64:
            raise RuntimeError("external speech returned no audio")
        engine = str(result.get("engine", "desktop"))
        return base64.b64decode(audio_b64, validate=True), engine

    @staticmethod
    def play_wav(path):
        command = ["aplay"]
        if APLAY_DEVICE:
            command.extend(["-D", APLAY_DEVICE])
        command.append(str(path))
        STATE["voice"]["last_command"] = " ".join(command)
        print(f"[Volp-E voice] playing wav: {STATE['voice']['last_command']}", flush=True)
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "aplay failed").strip()
            raise RuntimeError(f"{' '.join(command)} failed: {detail}")
        STATE["voice"]["last_result"] = (result.stderr or result.stdout or "aplay ok").strip()
        if result.stderr.strip():
            print(f"[Volp-E voice] {' '.join(command)}: {result.stderr.strip()}", flush=True)
        else:
            print(f"[Volp-E voice] {' '.join(command)}: ok", flush=True)

    @staticmethod
    def speak_espeak(text):
        amplitude = max(1, min(200, int(round(100 * VOICE_GAIN))))
        command = ["espeak-ng", "-v", "fr", "-a", str(amplitude), text]
        STATE["voice"]["last_command"] = " ".join(command)
        result = subprocess.run(command, capture_output=True, text=True, timeout=12)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "espeak-ng failed").strip()
            raise RuntimeError(f"espeak-ng failed: {detail}")
        STATE["voice"]["last_result"] = (result.stderr or result.stdout or "espeak-ng ok").strip()

    @staticmethod
    def apply_wav_gain(audio, gain):
        """Reduce PCM WAV amplitude without changing the system mixer volume."""
        if gain >= 0.999:
            return audio
        try:
            source = wave.open(io.BytesIO(audio), "rb")
            try:
                params = source.getparams()
                raw = bytearray(source.readframes(source.getnframes()))
            finally:
                source.close()

            if params.comptype != "NONE" or params.sampwidth not in (1, 2, 3, 4):
                return audio

            width = params.sampwidth
            for offset in range(0, len(raw) - width + 1, width):
                chunk = raw[offset:offset + width]
                if width == 1:
                    sample = chunk[0] - 128
                    scaled = int(round(sample * gain)) + 128
                    raw[offset] = max(0, min(255, scaled))
                else:
                    sample = int.from_bytes(chunk, "little", signed=True)
                    scaled = int(round(sample * gain))
                    limits = 8 * width - 1
                    scaled = max(-(1 << limits), min((1 << limits) - 1, scaled))
                    raw[offset:offset + width] = scaled.to_bytes(width, "little", signed=True)

            output = io.BytesIO()
            destination = wave.open(output, "wb")
            try:
                destination.setparams(params)
                destination.writeframes(raw)
            finally:
                destination.close()
            return output.getvalue()
        except Exception as exc:
            print(f"[Volp-E voice] could not apply gain: {exc}", flush=True)
            return audio

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
        if idle_for >= STANDBY_AFTER_SECONDS:
            if STATE["mode"] != "standby":
                VolpeHandler.remember("standby_entered", "Je passe en veille apres une longue periode calme.")
            STATE["mode"] = "standby"
        elif idle_for >= SLEEPY_AFTER_SECONDS:
            STATE["mode"] = "sleepy"
        elif STATE["mode"] in {"sleepy", "standby"}:
            STATE["mode"] = "normal"

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
