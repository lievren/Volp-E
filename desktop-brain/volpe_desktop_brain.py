#!/usr/bin/env python3
import base64
import json
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "0.0.0.0"
PORT = 8787
ROOT = Path(__file__).resolve().parent
LATEST_IMAGE = ROOT / "latest_scene.jpg"
LATEST_JSON = ROOT / "latest_scene.json"
PHRASES_JSON = ROOT / "phrases.json"
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
}


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
        self.send_error(404)

    def do_POST(self):
        if self.path != "/analyze":
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

    if face:
        if size >= 0.72:
            distance = "close"
            distance_text = "proche"
            speech = say("face_close")
        elif size >= 0.38:
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
        elif active_mood == "attentive" and size >= 0.72 and random.random() < 0.45:
            speech = say("face_close")
        elif memory_mood == "curious" and random.random() < 0.35:
            speech = say("presence_continues")
        elif curiosity >= 0.72 and random.random() < 0.35:
            speech = say("mood_curious")

        horizontal = "center"
        if x < -0.28:
            horizontal = "left"
        elif x > 0.28:
            horizontal = "right"

        vertical = "center"
        if y < -0.28:
            vertical = "up"
        elif y > 0.28:
            vertical = "down"

        return {
            "description": describe_face(distance_text, horizontal, vertical),
            "mood": active_mood if active_mood in {"curious", "attentive", "searching", "happy"} else ("curious" if distance != "close" else "attentive"),
            "suggested_mode": "alert",
            "speech": speech,
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
        speech = say("presence_lost")
    elif active_mood == "sleepy" or energy <= 0.24:
        speech = say("mood_sleepy")
    elif active_mood == "curious" and curiosity >= 0.65:
        speech = say("mood_curious")

    return {
        "description": say("no_presence"),
        "mood": active_mood if active_mood in {"sleepy", "curious", "searching", "dreaming"} else "calm",
        "suggested_mode": "normal",
        "speech": speech,
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


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    address = (HOST, PORT)
    print(f"Volp-E desktop brain listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer(address, DesktopBrainHandler).serve_forever()


if __name__ == "__main__":
    main()
