#!/usr/bin/env python3
import base64
import json
import os
import random
import re
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "0.0.0.0"
PORT = 8787
ROOT = Path(__file__).resolve().parent
LATEST_IMAGE = ROOT / "latest_scene.jpg"
LATEST_JSON = ROOT / "latest_scene.json"
PHRASES_JSON = ROOT / "phrases.json"
LATEST_SPEECH = ROOT / "latest_speech.wav"
PERSONALITY_FILE = Path(os.environ.get("VOLPE_PERSONALITY_FILE", ROOT.parent / "config" / "personality.json"))
PIPER_EXE = Path(os.environ.get("VOLPE_PIPER_EXE", ROOT / "piper" / "piper.exe"))
PIPER_MODEL = Path(os.environ.get("VOLPE_PIPER_MODEL", ROOT / "voices" / "fr_FR-siwis-medium.onnx"))
DEFAULT_PERSONALITY = {
    "name": "Volp-E",
    "pronunciation": "Volpi",
    "profile": "curious_companion",
    "description": "Petit compagnon attentif, curieux et expressif.",
    "tone": {
        "warmth": 0.78,
        "curiosity": 0.72,
        "playfulness": 0.35,
        "caution": 0.42,
        "talkativeness": 0.55,
    },
    "speech": {
        "prefix_chance": 0.18,
        "prefixes": {
            "happy": ["Ah.", "Tiens."],
            "curious": ["Hm.", "Interessant."],
            "sleepy": ["Doucement.", "Tout bas."],
            "searching": ["Attends.", "Je regarde."],
            "attentive": ["Ok.", "Je te suis."],
        },
    },
    "attention": {
        "face_close_size": 0.72,
        "face_medium_size": 0.38,
        "position_deadzone": 0.28,
    },
}
DEFAULT_PHRASES = {
    "face_close": [
        "Je te vois tout pres de moi.",
        "Tu es vraiment proche.",
        "Presence proche. Je reste attentif.",
        "Salut toi. Tu es dans ma zone proche.",
    ],
    "face_medium": [
        "Je te vois devant moi.",
        "Je t'ai repere.",
        "Quelqu'un est face a moi.",
        "Presence detectee. Je regarde dans ta direction.",
    ],
    "face_far": [
        "Je crois voir quelqu'un au loin.",
        "Je distingue une presence plus loin.",
        "Mouvement lointain detecte.",
        "Je garde un oeil sur cette presence.",
    ],
    "no_presence": [
        "Aucune presence detectee dans la derniere image exploitable.",
        "Scene calme. Je surveille doucement.",
        "Pas de visage confirme pour l'instant.",
        "Je reste en observation.",
    ],
    "presence_returned": [
        "Ah, te revoila.",
        "Je te retrouve dans mon champ de vision.",
        "Presence revenue. Je reprends le suivi.",
    ],
    "presence_continues": [
        "Je garde le contact visuel.",
        "Je continue de te suivre.",
        "Presence stable. Mon attention reste active.",
    ],
    "presence_lost": [
        "Je t'ai perdu de vue.",
        "Presence sortie du champ. Je reste attentif.",
        "Je ne te vois plus, mais je surveille.",
    ],
    "mood_happy": [
        "Content de te revoir.",
        "Je reconnais ce rythme. Tu reviens souvent.",
        "Presence familiere. Mon attention se stabilise.",
    ],
    "mood_sleepy": [
        "Je baisse un peu mon attention.",
        "Mode calme. Je reste en veille legere.",
        "Je ralentis doucement, mais je reste la.",
    ],
    "mood_curious": [
        "Quelque chose attire mon attention.",
        "Je suis curieux de ce qui se passe devant moi.",
        "J'observe. Il y a quelque chose d'interessant ici.",
    ],
    "description_face": [
        "Presence detectee {distance_text}. Position: {horizontal}/{vertical}.",
        "Analyse scene: personne {distance_text}, zone {horizontal}/{vertical}.",
        "Attention dirigee vers une presence {distance_text}, secteur {horizontal}/{vertical}.",
        "Suivi visuel actif: cible {distance_text}, position {horizontal}/{vertical}.",
    ],
}
STATE = {
    "started_at": time.time(),
    "last_analysis_at": 0.0,
    "last_image": "",
    "last_error": "",
    "last_intention": None,
    "personality": {},
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
        print(f"[Volp-E desktop brain] using default personality: {exc}", flush=True)
        return DEFAULT_PERSONALITY
    return deep_merge(DEFAULT_PERSONALITY, loaded)


PERSONALITY = load_personality()
STATE["personality"] = {
    "name": PERSONALITY.get("name", "Volp-E"),
    "pronunciation": PERSONALITY.get("pronunciation", "Volpi"),
    "profile": PERSONALITY.get("profile", "curious_companion"),
    "description": PERSONALITY.get("description", ""),
    "config_path": str(PERSONALITY_FILE),
    "tone": PERSONALITY.get("tone", {}),
    "speech": PERSONALITY.get("speech", {}),
}


def personality_float(section, key, default):
    try:
        return float(PERSONALITY.get(section, {}).get(key, default))
    except (TypeError, ValueError):
        return float(default)


def load_phrases():
    try:
        with PHRASES_JSON.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except Exception:
        return DEFAULT_PHRASES

    phrases = dict(DEFAULT_PHRASES)
    for key, fallback in DEFAULT_PHRASES.items():
        values = loaded.get(key, fallback)
        if isinstance(values, list):
            cleaned = [str(value).strip() for value in values if str(value).strip()]
            if cleaned:
                phrases[key] = cleaned
    return phrases


def say(category):
    return random.choice(load_phrases().get(category, DEFAULT_PHRASES[category]))


def chance(base_probability):
    talkativeness = personality_float("tone", "talkativeness", 0.55)
    return random.random() < max(0.0, min(1.0, base_probability * (0.55 + talkativeness)))


def style_speech(text, mood):
    text = str(text or "").strip()
    if not text:
        return ""
    speech = PERSONALITY.get("speech", {})
    prefixes = speech.get("prefixes", {}) if isinstance(speech, dict) else {}
    mood_prefixes = prefixes.get(mood, []) if isinstance(prefixes, dict) else []
    prefix_chance = personality_float("speech", "prefix_chance", 0.18)
    if mood_prefixes and random.random() < prefix_chance:
        return f"{random.choice(mood_prefixes)} {text}"
    return text


def describe_face(distance_text, horizontal, vertical):
    template = say("description_face")
    return template.format(
        distance_text=distance_text,
        horizontal=horizontal,
        vertical=vertical,
    )


class DesktopBrainHandler(BaseHTTPRequestHandler):
    server_version = "VolpEDesktopBrain/0.1"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json({
                "ok": True,
                "service": "volpe-desktop-brain",
                "uptime": time.time() - STATE["started_at"],
                "last_analysis_at": STATE["last_analysis_at"],
            })
            return
        if self.path == "/state":
            self.send_json({"ok": True, "state": STATE})
            return
        if self.path == "/personality":
            self.send_json({"ok": True, "personality": PERSONALITY})
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/analyze":
            if self.path == "/speak":
                self.handle_speak()
                return
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            image = base64.b64decode(payload.get("image_b64", ""), validate=True)
            if not image:
                raise ValueError("missing image_b64")

            LATEST_IMAGE.write_bytes(image)
            metadata = {
                "received_at": time.time(),
                "source": payload.get("source", "unknown"),
                "image_format": payload.get("image_format", "jpg"),
                "state": payload.get("state", {}),
                "image_bytes": len(image),
            }
            intention = build_intention(metadata["state"])
            metadata["intention"] = intention
            LATEST_JSON.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            STATE["last_analysis_at"] = metadata["received_at"]
            STATE["last_image"] = str(LATEST_IMAGE)
            STATE["last_error"] = ""
            STATE["last_intention"] = intention

            self.send_json({
                "ok": True,
                "kind": "scene_intention",
                "description": intention["description"],
                "mood": intention["mood"],
                "suggested_mode": intention["suggested_mode"],
                "speech": intention["speech"],
                "attention": intention["attention"],
                "actions": intention["actions"],
                "image_bytes": len(image),
                "saved_to": str(LATEST_IMAGE),
                "next_step": "connect a vision-language model or API to replace this rule-based interpretation",
            })
        except Exception as exc:
            STATE["last_error"] = str(exc)
            self.send_json({"ok": False, "error": str(exc)}, 400)

    def handle_speak(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = prepare_speech_text(payload.get("text", ""))
            if not text:
                raise ValueError("missing text")
            audio, engine = synthesize_speech_wav(text)
            LATEST_SPEECH.write_bytes(audio)
            self.send_json({
                "ok": True,
                "audio_format": "wav",
                "audio_b64": base64.b64encode(audio).decode("ascii"),
                "bytes": len(audio),
                "engine": engine,
            })
        except Exception as exc:
            STATE["last_error"] = str(exc)
            self.send_json({"ok": False, "error": str(exc)}, 400)


def build_intention(state):
    vision = state.get("vision", {}) if isinstance(state, dict) else {}
    memory = state.get("memory", {}) if isinstance(state, dict) else {}
    camera = state.get("camera", "") if isinstance(state, dict) else ""
    face = bool(vision.get("face")) or bool(state.get("face_recent")) or camera == "tracking"
    x = as_float(vision.get("x"), 0.0)
    y = as_float(vision.get("y"), 0.0)
    size = as_float(vision.get("size"), 0.0)
    memory_mood = str(memory.get("mood") or "")
    active_mood = str(memory.get("active_mood") or memory_mood)
    energy = as_float(memory.get("energy"), 0.5)
    curiosity = as_float(memory.get("curiosity"), 0.5)
    familiarity = as_float(memory.get("familiarity"), 0.0)
    last_event = memory.get("last_event") if isinstance(memory.get("last_event"), dict) else {}
    last_kind = str(last_event.get("kind") or "")
    face_close_size = personality_float("attention", "face_close_size", 0.72)
    face_medium_size = personality_float("attention", "face_medium_size", 0.38)
    deadzone = personality_float("attention", "position_deadzone", 0.28)

    if face:
        if size >= face_close_size:
            distance = "close"
            distance_text = "proche"
            speech = say("face_close")
        elif size >= face_medium_size:
            distance = "medium"
            distance_text = "a distance moyenne"
            speech = say("face_medium")
        else:
            distance = "far"
            distance_text = "loin"
            speech = say("face_far")

        if last_kind == "presence_arrived" and as_float(last_event.get("at"), 0.0) > time.time() - 12:
            speech = say("presence_returned")
        elif active_mood == "happy" or familiarity >= 0.50:
            speech = say("mood_happy")
        elif active_mood == "attentive" and size >= face_close_size and chance(0.45):
            speech = say("face_close")
        elif memory_mood == "curious" and chance(0.35):
            speech = say("presence_continues")
        elif curiosity >= 0.72 and chance(0.35):
            speech = say("mood_curious")

        horizontal = "center"
        if x < -deadzone:
            horizontal = "left"
        elif x > deadzone:
            horizontal = "right"

        vertical = "center"
        if y < -deadzone:
            vertical = "up"
        elif y > deadzone:
            vertical = "down"
        mood = active_mood if active_mood in {"curious", "attentive", "searching", "happy"} else ("curious" if distance != "close" else "attentive")

        return {
            "description": describe_face(distance_text, horizontal, vertical),
            "mood": mood,
            "suggested_mode": "alert",
            "speech": style_speech(speech, mood),
            "attention": {
                "priority": "person",
                "confidence": 0.75,
                "x": x,
                "y": y,
                "size": size,
                "distance": distance,
                "horizontal": horizontal,
                "vertical": vertical,
            },
            "actions": [
                {"type": "face_mode", "mode": "alert"},
                {"type": "look_at", "x": x, "y": y},
            ],
        }

    speech = ""
    if memory_mood == "searching" or last_kind == "presence_lost":
        speech = say("presence_lost") if chance(0.85) else ""
    elif active_mood == "sleepy" or energy <= 0.24:
        speech = say("mood_sleepy") if chance(0.45) else ""
    elif active_mood == "curious" and curiosity >= 0.65 and chance(0.55):
        speech = say("mood_curious")
    mood = active_mood if active_mood in {"sleepy", "curious", "searching", "dreaming"} else "calm"

    return {
        "description": say("no_presence"),
        "mood": mood,
        "suggested_mode": "normal",
        "speech": style_speech(speech, mood),
        "attention": {
            "priority": "none",
            "confidence": 0.0,
            "x": 0.0,
            "y": 0.0,
            "size": 0.0,
            "distance": "unknown",
            "horizontal": "center",
            "vertical": "center",
        },
        "actions": [
            {"type": "face_mode", "mode": "normal"},
        ],
    }


def as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def prepare_speech_text(text):
    text = " ".join(str(text or "").split())
    pronunciation = str(PERSONALITY.get("pronunciation") or "Volpi").strip() or "Volpi"
    return re.sub(r"\bvolp\s*[- ]?\s*e\b", pronunciation, text, flags=re.IGNORECASE)


def synthesize_speech_wav(text):
    try:
        return synthesize_with_piper(text), "piper"
    except Exception:
        return synthesize_with_windows_tts(text), "windows-tts"


def synthesize_with_piper(text):
    if not PIPER_EXE.exists():
        raise FileNotFoundError(f"Piper executable not found: {PIPER_EXE}")
    if not PIPER_MODEL.exists():
        raise FileNotFoundError(f"Piper model not found: {PIPER_MODEL}")
    config_path = Path(str(PIPER_MODEL) + ".json")
    if not config_path.exists():
        raise FileNotFoundError(f"Piper model config not found: {config_path}")

    with tempfile.TemporaryDirectory(prefix="volpe-piper-") as tmp:
        wav_path = Path(tmp) / "speech.wav"
        completed = subprocess.run(
            [str(PIPER_EXE), "--model", str(PIPER_MODEL), "--output_file", str(wav_path)],
            input=text,
            timeout=20,
            text=True,
            capture_output=True,
            cwd=str(PIPER_EXE.parent),
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or "Piper failed")
        if not wav_path.exists() or wav_path.stat().st_size <= 1024:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or "Piper created no usable audio")
        return wav_path.read_bytes()


def synthesize_with_windows_tts(text):
    with tempfile.TemporaryDirectory(prefix="volpe-tts-") as tmp:
        tmp_path = Path(tmp)
        text_path = tmp_path / "speech.txt"
        wav_path = tmp_path / "speech.wav"
        script_path = tmp_path / "speak.ps1"
        text_path.write_text(text, encoding="utf-8")
        script_path.write_text(
            """
$textPath = $args[0]
$wavPath = $args[1]
$text = Get-Content -Raw -Encoding UTF8 $textPath

function Test-UsableWav($path) {
  return ((Test-Path $path) -and ((Get-Item $path).Length -gt 1024))
}

$ok = $false

try {
  Add-Type -AssemblyName System.Speech
  $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
  try {
    try {
      $speaker.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet, [System.Speech.Synthesis.VoiceAge]::NotSet, 0, [System.Globalization.CultureInfo]'fr-FR')
    } catch {}
    $speaker.Rate = 0
    $speaker.Volume = 100
    $speaker.SetOutputToWaveFile($wavPath)
    $speaker.Speak($text)
    $speaker.SetOutputToNull()
    $ok = Test-UsableWav $wavPath
  } finally {
    if ($speaker) { $speaker.Dispose() }
  }
} catch {}

if (-not $ok) {
  try {
    if (Test-Path $wavPath) { Remove-Item -Force $wavPath }
    $voice = New-Object -ComObject SAPI.SpVoice
    $stream = New-Object -ComObject SAPI.SpFileStream
    $format = New-Object -ComObject SAPI.SpAudioFormat
    $format.Type = 22
    $stream.Format = $format
    $stream.Open($wavPath, 3, $false)
    try {
      $voice.Rate = 0
      $voice.Volume = 100
      $voice.AudioOutputStream = $stream
      [void]$voice.Speak($text, 0)
    } finally {
      $stream.Close()
    }
    $ok = Test-UsableWav $wavPath
  } catch {}
}

if (-not $ok) {
  throw "Windows TTS did not create a usable WAV file."
}
""".strip(),
            encoding="utf-8",
        )
        powershell = "powershell.exe"
        completed = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path), str(text_path), str(wav_path)],
            timeout=12,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or "Windows TTS failed")
        if not wav_path.exists() or wav_path.stat().st_size <= 1024:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or "Windows TTS created no usable audio")
        return wav_path.read_bytes()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    address = (HOST, PORT)
    print(f"Volp-E desktop brain listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer(address, DesktopBrainHandler).serve_forever()


if __name__ == "__main__":
    main()
