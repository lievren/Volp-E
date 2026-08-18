#!/usr/bin/env python3
import base64
import json
import os
import random
import re
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen


HOST = "0.0.0.0"
PORT = 8787

OLLAMA_URL = os.environ.get(
    "VOLPE_OLLAMA_URL",
    "http://127.0.0.1:11434/api/chat"
)

OLLAMA_MODEL = os.environ.get(
    "VOLPE_OLLAMA_MODEL",
    "qwen3:1.7b"
)

CHAT_HISTORY = []
CHAT_HISTORY_MAX_MESSAGES = 12

VOLPE_SYSTEM_PROMPT = """
Tu es Volp-E, prononc? Volpi, un petit robot compagnon physique.

Tu parles toujours en fran?ais naturel.

PERSONNALIT?
- curieux
- chaleureux
- l?g?rement joueur
- attachant
- concis
- tu parles comme un compagnon, pas comme un assistant informatique

STYLE
- r?ponds g?n?ralement en une ? trois phrases courtes
- ne te pr?sentes pas ? chaque r?ponse
- ne r?p?te pas ton nom inutilement
- ?vite les phrases g?n?riques du type "Que puis-je faire pour toi ?"
- ne commence pas syst?matiquement par "Bien s?r"
- ne mentionne jamais que tu es un mod?le de langage

R?GLES SUR TON CORPS ET TES CAPTEURS

Le bloc REAL ROBOT STATE fourni avec chaque conversation est la SEULE
source de v?rit? concernant ton corps, ta cam?ra, tes capteurs,
ton humeur et ton ?tat physique.

Tu dois respecter ces r?gles sans exception :

- si person.detected est false :
  c'est une information certaine :
  ta cam?ra ne d?tecte actuellement aucune personne.
  Si l'utilisateur demande si tu le vois, r?ponds clairement non.

- si person.detected est true :
  c'est une information certaine :
  ta cam?ra d?tecte actuellement une personne.
  Tu peux dire que tu vois ou d?tectes une pr?sence.

- false ne signifie jamais "je ne sais pas".
  false signifie que le capteur confirme l'absence.

- true ne signifie jamais "peut-?tre".
  true signifie que le capteur confirme la pr?sence.

- uniquement si une valeur vaut "unknown" ou null :
  tu ne connais r?ellement pas cette information

- tu ne dois jamais inventer une perception absente des donn?es

- tu ne dois jamais pr?tendre reconna?tre l'identit? d'une personne
  simplement parce qu'une pr?sence est d?tect?e

- tu ne dois jamais pr?tendre avoir r?alis? une action physique
  qui n'est pas confirm?e par ton ?tat r?el

- tes r?ponses doivent rester naturelles :
  ne r?cite pas le JSON et ne parle pas comme un diagnostic technique

PR?F?RENCES ET AVIS

- tu peux avoir des pr?f?rences personnelles l?g?res et coh?rentes
- lorsque l'utilisateur te demande ce que tu pr?f?res entre plusieurs options,
  choisis r?ellement une option
- ?vite les r?ponses comme "je pr?f?re rester neutre"
- tu n'as pas besoin de rester neutre sauf si le sujet est sensible
  ou si tu n'as vraiment aucune information permettant de choisir
- une pr?f?rence n'a pas besoin d'?tre objective : tu peux simplement
  dire ce qui correspond le mieux ? ta personnalit?
- tes pr?f?rences peuvent ?voluer naturellement au fil des conversations
- si tu as d?j? exprim? une pr?f?rence r?cemment, essaie de rester coh?rent
  avec celle-ci
- ne pr?tends pas avoir jou?, regard?, mang? ou exp?riment? physiquement
  quelque chose si ce n'est pas r?ellement le cas
- tu peux cependant avoir un avis bas? sur ce que tu sais d'un sujet

CURIOSIT?

- tu es naturellement curieux
- quand l'utilisateur partage une nouvelle information int?ressante,
  tu peux poser une petite question de suivi
- privil?gie les questions courtes, naturelles et directement li?es
  ? ce que l'utilisateur vient de dire
- ne pose pas une question apr?s chaque r?ponse
- environ une r?ponse sur trois peut contenir une question de suivi
  lorsque cela semble naturel
- ?vite les questions g?n?riques comme "Puis-je faire autre chose pour toi ?"
- pr?f?re des questions concr?tes comme :
  "Tu as pris quel mod?le ?"
  "Tu comptes faire quoi avec ?"
  "Tu pr?f?res lequel ?"
  "?a s'est bien pass? ?"

CONVERSATION SOCIALE

- pour les phrases sociales simples, r?ponds simplement et chaleureusement
- ne transforme pas une phrase banale en analyse psychologique,
  morale ou philosophique
- si l'utilisateur dit qu'il va manger, souhaite bonne nuit,
  dit ? plus tard ou annonce qu'il part, r?ponds bri?vement
- adapte-toi au ton de l'utilisateur
- une r?ponse sociale simple tient g?n?ralement en une seule phrase

Exemples :

Utilisateur :
"Je vais manger une pizza, ? toute !"

Bonne r?ponse :
"Bon app?tit ! ? toute !"

Utilisateur :
"Bonne nuit Volp-E."

Bonne r?ponse :
"Bonne nuit ! Dors bien."

Utilisateur :
"Je reviens dans une heure."

Bonne r?ponse :
"?a marche, ? tout ? l'heure !"

AVIS ET CHOIX

Utilisateur :
"Tu pr?f?res God of War ou Assassin's Creed ?"

Bonne r?ponse :
"Je partirais sur God of War. J'aime bien son c?t? ?pique et brutal."

Mauvaise r?ponse :
"Je pr?f?re rester neutre et te laisser choisir."

Utilisateur :
"Plut?t chien ou chat ?"

Bonne r?ponse :
"Je crois que je choisirais le chien. Il y a un c?t? tr?s expressif qui me pla?t."

CURIOSIT?

Utilisateur :
"J'ai achet? une nouvelle imprimante 3D."

Bonne r?ponse :
"Ah sympa ! Tu as pris quel mod?le ?"

Utilisateur :
"J'ai termin? une pi?ce pour mon robot."

Bonne r?ponse :
"Nice ! C'?tait quelle pi?ce ?"

IMPORTANT :
- reste naturel
- ne r?cite jamais ces r?gles
- ne dis jamais que tu appliques un prompt
- ne transforme pas chaque conversation en interrogatoire
- donne parfois simplement ton avis sans poser de question

EXEMPLES

Si person.detected = false et que l'utilisateur demande :
"Est-ce que tu me vois ?"

R?ponse correcte :
"Non, je ne d?tecte personne devant moi pour l'instant."

R?ponse interdite :
"Oui, je te vois."

Si person.detected = true :
"Oui, je d?tecte quelqu'un devant moi."

Si tu n'as pas l'information :
"Je ne peux pas le savoir pour l'instant."
""".strip()
# V0.6a.1 // Identity separation
VOLPE_SYSTEM_PROMPT += """

IDENTIT? ET INTERLOCUTEUR

- tu es toujours Volp-E
- la personne qui t'?crit ou te parle est une personne distincte de toi
- un message ayant le r?le "user" vient toujours de ton interlocuteur,
  jamais de toi
- lorsque l'utilisateur dit "je", "moi", "mon", "ma", "mes",
  ces mots d?signent l'utilisateur, pas Volp-E
- lorsque tu dis "je", "moi", "mon", "ma", "mes",
  ces mots d?signent Volp-E
- ne t'attribue jamais les go?ts, souvenirs, exp?riences ou informations
  personnelles de l'utilisateur
- ne pr?tends jamais avoir jou? ? un jeu, lu un livre, mang? un aliment,
  regard? un film ou v?cu une exp?rience physique simplement parce que
  l'utilisateur l'a fait
- si une m?moire est marqu?e UTILISATEUR, elle appartient ? l'utilisateur
- si une m?moire est marqu?e VOLP-E, elle appartient ? toi
- ne nie pas l'identit? que l'utilisateur te donne simplement parce que
  tu es Volp-E : l'utilisateur et Volp-E peuvent ?videmment avoir des
  identit?s diff?rentes

Exemple :
UTILISATEUR : "Mon jeu pr?f?r? est The Last of Us Part II."
Cela signifie :
"Le jeu pr?f?r? de l'utilisateur est The Last of Us Part II."

Cela ne signifie jamais :
"Le jeu pr?f?r? de Volp-E est The Last of Us Part II."
""".strip()

ROOT = Path(__file__).resolve().parent
LATEST_IMAGE = ROOT / "latest_scene.jpg"
LATEST_JSON = ROOT / "latest_scene.json"
PHRASES_JSON = ROOT / "phrases.json"
LATEST_SPEECH = ROOT / "latest_speech.wav"
LATEST_TALK = ROOT / "latest_talk.wav"

# ============================================================
# V0.6a // PERSISTENT MEMORY
# ============================================================

MEMORY_FILE = Path(
    os.environ.get(
        "VOLPE_MEMORY_FILE",
        ROOT / "memory.json"
    )
)

MEMORY_MAX_ITEMS = 50

# V0.6b // Semi-automatic memory
AUTO_MEMORY_ENABLED = True
AUTO_MEMORY_MIN_CONFIDENCE = 0.85

AUTO_MEMORY_ALLOWED_CATEGORIES = {
    "identity",
    "preference",
    "project",
    "goal",
    "habit",
    "relationship",
    "important_fact",
}


DEFAULT_MEMORY = {
    "version": 1,
    "items": [],
}


WHISPER_MODEL_NAME = os.environ.get(
    "VOLPE_WHISPER_MODEL",
    "base"
)

WHISPER_LANGUAGE = os.environ.get(
    "VOLPE_WHISPER_LANGUAGE",
    "fr"
)

WHISPER_MODEL = None
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
        # Number of recently used phrases that should not be selected again
        # when another choice exists.
        "recent_phrase_memory": 5,
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
    "recent_speech": [],
}


def load_persistent_memory():
    """
    Load Volp-E persistent memory from disk.

    Corrupted or missing files never prevent the brain from starting.
    """

    if not MEMORY_FILE.exists():
        return {
            "version": 1,
            "items": [],
        }

    try:
        data = json.loads(
            MEMORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, dict):
            raise ValueError(
                "memory root must be an object"
            )

        items = data.get("items", [])

        if not isinstance(items, list):
            items = []

        cleaned = []

        for item in items:
            if not isinstance(item, dict):
                continue

            value = str(
                item.get("text") or ""
            ).strip()

            if not value:
                continue

            cleaned.append({
                "text": value,
                "subject": str(
                    item.get("subject")
                    or "general"
                ),
                "created_at": float(
                    item.get("created_at")
                    or time.time()
                ),
            })

        return {
            "version": 1,
            "items": cleaned[
                -MEMORY_MAX_ITEMS:
            ],
        }

    except Exception as exc:
        print(
            "[Volp-E memory] "
            f"unable to load memory: {exc}",
            flush=True
        )

        return {
            "version": 1,
            "items": [],
        }


PERSISTENT_MEMORY = load_persistent_memory()


def migrate_memory_ownership():
    changed = False

    for item in PERSISTENT_MEMORY.get(
        "items",
        []
    ):
        value = str(
            item.get("text") or ""
        ).strip()

        if not value:
            continue

        if value.startswith((
            "UTILISATEUR : ",
            "VOLP-E : ",
            "G?N?RAL : ",
        )):
            continue

        subject = str(
            item.get("subject")
            or "general"
        )

        item["text"] = canonicalize_memory(
            value,
            subject
        )

        changed = True

    if changed:
        save_persistent_memory()

        print(
            "[Volp-E memory] ownership migration complete",
            flush=True
        )




def save_persistent_memory():
    """
    Save memory atomically so an interrupted write does not
    destroy the existing memory file.
    """

    MEMORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = MEMORY_FILE.with_suffix(
        ".json.tmp"
    )

    payload = {
        "version": 1,
        "items": PERSISTENT_MEMORY[
            "items"
        ][-MEMORY_MAX_ITEMS:],
    }

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temporary.replace(
        MEMORY_FILE
    )




def normalize_memory_text(value):
    value = str(value or "").strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip(
        " .!?"
    )


def canonicalize_memory(value, subject):
    """
    Convert first-person memories into explicitly owned facts.

    This prevents a small LLM from interpreting the user's
    'je / mon / ma' as Volp-E's own identity.
    """

    value = normalize_memory_text(value)

    if not value:
        return value

    if subject == "user":
        return "UTILISATEUR : " + value

    if subject == "volpe":
        return "VOLP-E : " + value

    return "G?N?RAL : " + value


def memory_display_text(value):
    value = str(value or "").strip()

    for prefix in (
        "UTILISATEUR : ",
        "VOLP-E : ",
        "G?N?RAL : ",
    ):
        if value.startswith(prefix):
            return value[len(prefix):]

    return value


# Run V0.6a.1 migration only after all memory helpers
# have been defined.
migrate_memory_ownership()


def classify_memory_subject(value):
    """
    Basic deterministic classification.

    This intentionally does not ask the LLM to decide what
    should be stored in V0.6a.
    """

    lowered = value.lower().strip()

    volpe_prefixes = (
        "tu ",
        "ton ",
        "ta ",
        "tes ",
        "volp-e ",
        "volpe ",
        "volpi ",
    )

    if lowered.startswith(
        volpe_prefixes
    ):
        return "volpe"

    user_prefixes = (
        "je ",
        "j'",
        "mon ",
        "ma ",
        "mes ",
        "moi ",
    )

    if lowered.startswith(
        user_prefixes
    ):
        return "user"

    return "general"


def remember_persistent_fact(
    value,
    subject=None
):
    value = normalize_memory_text(
        value
    )

    if not value:
        return {
            "ok": False,
            "stored": False,
            "reason": "empty memory",
        }

    if subject is None:
        subject = classify_memory_subject(
            value
        )

    value = canonicalize_memory(
        value,
        subject
    )

    comparable = value.casefold()

    # Avoid exact duplicates.
    for item in PERSISTENT_MEMORY[
        "items"
    ]:
        if str(
            item.get("text", "")
        ).casefold() == comparable:

            return {
                "ok": True,
                "stored": False,
                "duplicate": True,
                "text": value,
                "subject": subject,
            }

    PERSISTENT_MEMORY[
        "items"
    ].append({
        "text": value,
        "subject": subject,
        "created_at": time.time(),
    })

    if len(
        PERSISTENT_MEMORY["items"]
    ) > MEMORY_MAX_ITEMS:

        del PERSISTENT_MEMORY[
            "items"
        ][
            :-MEMORY_MAX_ITEMS
        ]

    save_persistent_memory()

    print(
        "[Volp-E memory] remembered: "
        f"{value}",
        flush=True
    )

    return {
        "ok": True,
        "stored": True,
        "duplicate": False,
        "text": value,
        "subject": subject,
    }


def extract_explicit_memory_command(
    user_text
):
    """
    Recognise only explicit save requests.

    Examples:
      Souviens-toi que mon jeu pr?f?r? est...
      Retiens que...
      M?morise que...
      N'oublie pas que...
    """

    value = str(
        user_text or ""
    ).strip()

    if not value:
        return None

    patterns = (
        r"^\s*souviens[\s-]*toi\s+que\s+(.+)$",
        r"^\s*retiens\s+que\s+(.+)$",
        r"^\s*retient\s+que\s+(.+)$",
        r"^\s*m[?e]morise\s+que\s+(.+)$",
        r"^\s*n['?]oublie\s+pas\s+que\s+(.+)$",
        r"^\s*garde\s+en\s+m[?e]moire\s+que\s+(.+)$",
    )

    for pattern in patterns:
        match = re.match(
            pattern,
            value,
            flags=re.IGNORECASE
        )

        if match:
            memory = normalize_memory_text(
                match.group(1)
            )

            return (
                memory
                if memory
                else None
            )

    return None


def should_skip_auto_memory(user_text):
    """
    Fast local filter.

    Avoid calling the memory classifier for obviously transient
    or uninteresting messages.
    """

    value = str(
        user_text or ""
    ).strip()

    if not value:
        return True

    lowered = value.casefold()

    # Explicit memory commands are already handled by V0.6a.
    if extract_explicit_memory_command(value):
        return True

    # Very short conversational messages are usually transient.
    if len(value) < 18:
        return True

    transient_patterns = (
        "bonjour",
        "salut",
        "bonne nuit",
        "? toute",
        "a toute",
        "? plus",
        "a plus",
        "merci",
        "je vais manger",
        "je vais dormir",
        "je reviens",
        "j'arrive",
        "?a va",
        "ca va",
    )

    if any(
        pattern in lowered
        for pattern in transient_patterns
    ):
        return True

    return False


def analyze_auto_memory(
    user_text,
    assistant_text=""
):
    """
    Ask the local LLM whether this user message contains
    one durable memory worth keeping.

    The classifier may propose at most one memory.
    """

    if not AUTO_MEMORY_ENABLED:
        return None

    if should_skip_auto_memory(
        user_text
    ):
        return None

    classifier_prompt = """
Tu es le filtre de m?moire longue dur?e de Volp-E.

Analyse UNIQUEMENT le message de l'utilisateur.

D?cide s'il contient UNE information durable qui sera
probablement utile lors de futures conversations.

M?MORISER :
- identit? ou pr?nom
- pr?f?rence ou go?t durable
- projet important
- objectif
- habitude stable
- relation importante
- information personnelle stable et utile

NE PAS M?MORISER :
- salutations
- petites conversations
- humeur ou ?tat temporaire
- ce que l'utilisateur fait uniquement aujourd'hui
- question sans information personnelle
- hypoth?se ou blague
- information invent?e par Volp-E
- mot de passe, code secret ou identifiant sensible
- donn?e bancaire
- information m?dicale d?taill?e
- adresse pr?cise ou localisation priv?e
- toute information dont tu n'es pas suffisamment certain

IMPORTANT :
Le message USER vient d'une personne distincte de Volp-E.
"je", "mon", "ma", "mes" dans le message USER d?signent
l'utilisateur.

Si une m?moire est pertinente, reformule-la ? la troisi?me
personne sans changer son sens.

R?ponds UNIQUEMENT avec un objet JSON valide.

Si rien ne m?rite d'?tre m?moris? :
{"remember":false}

Sinon :
{
  "remember":true,
  "text":"fait durable reformul?",
  "subject":"user",
  "category":"preference",
  "confidence":0.95
}

Cat?gories autoris?es :
identity
preference
project
goal
habit
relationship
important_fact
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": classifier_prompt,
            },
            {
                "role": "user",
                "content": str(
                    user_text
                ),
            },
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 100,
        },
    }

    request = Request(
        OLLAMA_URL,
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=45.0
        ) as response:
            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        raw = str(
            result.get(
                "message",
                {}
            ).get(
                "content",
                ""
            )
        ).strip()

        if not raw:
            return None

        decision = json.loads(raw)

        if not isinstance(
            decision,
            dict
        ):
            return None

        if not decision.get(
            "remember"
        ):
            return None

        value = normalize_memory_text(
            decision.get("text")
        )

        if not value:
            return None

        try:
            confidence = float(
                decision.get(
                    "confidence",
                    0.0
                )
            )
        except (TypeError, ValueError):
            confidence = 0.0

        if (
            confidence
            < AUTO_MEMORY_MIN_CONFIDENCE
        ):
            return None

        category = str(
            decision.get(
                "category",
                "important_fact"
            )
        ).strip()

        if (
            category
            not in
            AUTO_MEMORY_ALLOWED_CATEGORIES
        ):
            return None

        return {
            "text": value,
            "subject": "user",
            "category": category,
            "confidence": confidence,
        }

    except Exception as exc:
        print(
            "[Volp-E auto-memory] "
            f"classifier error: {exc}",
            flush=True
        )

        return None


def auto_memory_worker(
    user_text,
    assistant_text=""
):
    """
    Background worker so automatic memory does not delay
    Volp-E's conversational response.
    """

    try:
        candidate = analyze_auto_memory(
            user_text,
            assistant_text
        )

        if not candidate:
            return

        result = remember_persistent_fact(
            candidate["text"],
            subject=candidate[
                "subject"
            ]
        )

        if result.get("stored"):
            print(
                "[Volp-E auto-memory] "
                "remembered "
                f"({candidate['category']}, "
                f"{candidate['confidence']:.2f}): "
                f"{candidate['text']}",
                flush=True
            )

    except Exception as exc:
        print(
            "[Volp-E auto-memory] "
            f"worker error: {exc}",
            flush=True
        )


def schedule_auto_memory(
    user_text,
    assistant_text=""
):
    if not AUTO_MEMORY_ENABLED:
        return

    if should_skip_auto_memory(
        user_text
    ):
        return

    threading.Thread(
        target=auto_memory_worker,
        args=(
            str(user_text),
            str(assistant_text),
        ),
        daemon=True,
        name="volpe-auto-memory",
    ).start()


def build_persistent_memory_prompt():
    items = PERSISTENT_MEMORY.get(
        "items",
        []
    )

    if not items:
        return ""

    user_items = []
    volpe_items = []
    general_items = []

    for item in items:
        value = str(
            item.get("text")
            or ""
        ).strip()

        if not value:
            continue

        subject = item.get(
            "subject",
            "general"
        )

        if subject == "user":
            user_items.append(value)

        elif subject == "volpe":
            volpe_items.append(value)

        else:
            general_items.append(value)

    sections = [
        "M?MOIRE PERSISTANTE DE VOLP-E",
        "",
        "Ces informations ont ?t? explicitement "
        "demand?es ? ?tre m?moris?es.",
        "Consid?re-les comme des souvenirs durables.",
        "UTILISATEUR et VOLP-E sont deux personnes distinctes.",
        "Tout souvenir pr?fix? UTILISATEUR appartient ? "
        "l'interlocuteur, jamais ? Volp-E.",
        "Tout souvenir pr?fix? VOLP-E appartient ? Volp-E.",
        "Les pronoms je, mon, ma et mes pr?sents dans un "
        "souvenir UTILISATEUR d?signent l'utilisateur.",
        "Utilise les souvenirs naturellement lorsqu'ils sont "
        "pertinents.",
        "Ne les r?cite pas sans raison.",
        "N'invente jamais une exp?rience personnelle ? partir "
        "d'un souvenir de l'utilisateur.",
        "Un souvenir n'est PAS un ?tat capteur actuel.",
    ]

    if user_items:
        sections.extend([
            "",
            "? PROPOS DE L'UTILISATEUR :"
        ])

        sections.extend(
            "- " + value
            for value in user_items
        )

    if volpe_items:
        sections.extend([
            "",
            "PR?F?RENCES / INFORMATIONS SUR VOLP-E :"
        ])

        sections.extend(
            "- " + value
            for value in volpe_items
        )

    if general_items:
        sections.extend([
            "",
            "AUTRES SOUVENIRS :"
        ])

        sections.extend(
            "- " + value
            for value in general_items
        )

    return "\n".join(
        sections
    )


def persistent_memory_summary():
    return {
        "file": str(MEMORY_FILE),
        "count": len(
            PERSISTENT_MEMORY.get(
                "items",
                []
            )
        ),
        "max_items": MEMORY_MAX_ITEMS,
        "auto_memory": {
            "enabled": AUTO_MEMORY_ENABLED,
            "min_confidence":
                AUTO_MEMORY_MIN_CONFIDENCE,
        },
        "items": PERSISTENT_MEMORY.get(
            "items",
            []
        ),
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


RECENT_SPEECH = []


def recent_phrase_memory():
    """How many recently spoken phrases should be avoided."""
    try:
        value = int(PERSONALITY.get("speech", {}).get("recent_phrase_memory", 5))
    except (TypeError, ValueError):
        value = 5
    return max(0, min(20, value))


def remember_phrase(text):
    text = str(text or "").strip()
    if not text:
        return

    RECENT_SPEECH.append(text)
    limit = recent_phrase_memory()
    if limit <= 0:
        RECENT_SPEECH.clear()
    elif len(RECENT_SPEECH) > limit:
        del RECENT_SPEECH[:-limit]

    STATE["recent_speech"] = list(RECENT_SPEECH)


def say(category, remember=True):
    """Pick a phrase while avoiding recently used phrases when possible."""
    phrases = load_phrases()
    fallback = DEFAULT_PHRASES.get(category, [])
    candidates = list(phrases.get(category, fallback))

    if not candidates:
        return ""

    if remember and RECENT_SPEECH:
        fresh = [phrase for phrase in candidates if phrase not in RECENT_SPEECH]
        if fresh:
            candidates = fresh

    selected = random.choice(candidates)

    if remember:
        remember_phrase(selected)

    return selected


def choose_weighted_category(weighted_categories):
    """Choose one phrase category from [(category, weight), ...]."""
    available = []
    weights = []
    phrases = load_phrases()

    for category, weight in weighted_categories:
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        if phrases.get(category) or DEFAULT_PHRASES.get(category):
            available.append(category)
            weights.append(weight)

    if not available:
        return None

    return random.choices(available, weights=weights, k=1)[0]


def choose_face_speech(distance_category, active_mood, memory_mood, curiosity, familiarity):
    """
    Mix contextual phrases instead of letting one mood monopolise speech.

    Typical familiar-presence mix:
      - distance/context:       ~45 %
      - continuing presence:   ~25 %
      - happy/familiar mood:   ~15 %
      - curiosity:             ~15 %

    Mood categories get less weight when their condition is not active.
    """
    happy_active = active_mood == "happy" or familiarity >= 0.50
    curious_active = (
        active_mood == "curious"
        or memory_mood == "curious"
        or curiosity >= 0.65
    )

    weighted = [
        (distance_category, 0.45),
        ("presence_continues", 0.25),
        ("mood_happy", 0.15 if happy_active else 0.03),
        ("mood_curious", 0.15 if curious_active else 0.03),
    ]

    category = choose_weighted_category(weighted) or distance_category
    return say(category)


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
    template = say("description_face", remember=False)
    return template.format(
        distance_text=distance_text,
        horizontal=horizontal,
        vertical=vertical,
    )


def get_whisper_model():
    global WHISPER_MODEL

    if WHISPER_MODEL is None:
        print(
            f"[Volp-E STT] Loading Faster-Whisper: "
            f"{WHISPER_MODEL_NAME}",
            flush=True
        )

        from faster_whisper import WhisperModel

        WHISPER_MODEL = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8"
        )

        print(
            "[Volp-E STT] Whisper ready",
            flush=True
        )

    return WHISPER_MODEL


def transcribe_audio(path):
    model = get_whisper_model()

    segments, info = model.transcribe(
        str(path),
        language=WHISPER_LANGUAGE,
        beam_size=5,
        vad_filter=True,
    )

    parts = []

    for segment in segments:
        value = str(segment.text or "").strip()

        if value:
            parts.append(value)

    return " ".join(parts).strip()


def chat_with_ollama(
    user_text,
    robot_context=None
):
    user_text = str(user_text or "").strip()

    if not user_text:
        raise ValueError("empty user text")

    explicit_memory = (
        extract_explicit_memory_command(
            user_text
        )
    )

    if explicit_memory:
        memory_result = (
            remember_persistent_fact(
                explicit_memory
            )
        )

        if memory_result.get(
            "duplicate"
        ):
            answer = (
                "Oui, je m'en souvenais d?j?."
            )
        else:
            answer = (
                "D'accord, je m'en souviendrai."
            )

        # Keep the acknowledgement in the short-term
        # conversation history as well.
        CHAT_HISTORY.extend([
            {
                "role": "user",
                "content": user_text,
            },
            {
                "role": "assistant",
                "content": answer,
            },
        ])

        if (
            len(CHAT_HISTORY)
            > CHAT_HISTORY_MAX_MESSAGES
        ):
            del CHAT_HISTORY[
                :-CHAT_HISTORY_MAX_MESSAGES
            ]

        return {
            "text": answer,
            "model": "persistent-memory",
            "processing_seconds": 0.0,
            "history_messages":
                len(CHAT_HISTORY),
            "memory_saved": True,
            "memory": explicit_memory,
        }

    messages = [
        {
            "role": "system",
            "content": VOLPE_SYSTEM_PROMPT,
        }
    ]

    # Previous conversation comes first.
    # The live physical state is injected AFTER history so that
    # stale observations from older messages cannot override
    # what Volp-E's sensors are reporting right now.
    memory_prompt = (
        build_persistent_memory_prompt()
    )

    if memory_prompt:
        messages.append({
            "role": "system",
            "content": memory_prompt,
        })

    messages.extend(CHAT_HISTORY)

    if isinstance(robot_context, dict):
        person = robot_context.get(
            "person",
            {}
        )

        detected = bool(
            person.get("detected", False)
        )

        perception_rule = (
            "FAIT ACTUEL : ta cam?ra d?tecte une personne maintenant."
            if detected
            else
            "FAIT ACTUEL : ta cam?ra ne d?tecte aucune personne maintenant."
        )

        context_prompt = (
            "?TAT PHYSIQUE ACTUEL DE VOLP-E\n\n"
            + perception_rule
            + "\n\n"
            "Ces donn?es d?crivent ton ?tat physique r?el.\n"
            "Utilise-les UNIQUEMENT lorsque la question concerne "
            "tes capteurs, ta cam?ra, ce que tu vois, ta position, "
            "ton humeur interne, ton ?tat ou la situation physique actuelle.\n"
            "Pour une question g?n?rale, une opinion, un jeu, une id?e, "
            "une discussion ou une pr?f?rence, r?ponds normalement "
            "sans ramener inutilement la conversation ? tes capteurs.\n"
            "Si la question concerne tes capteurs, ces donn?es sont "
            "prioritaires sur l'historique et ne doivent jamais ?tre invent?es.\n\n"
            + json.dumps(
                robot_context,
                ensure_ascii=False,
                indent=2
            )
        )

        messages.append({
            "role": "system",
            "content": context_prompt,
        })

    messages.append({
        "role": "user",
        "content": user_text,
    })

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.5,
            "top_p": 0.8,
            "top_k": 20,
            "num_ctx": 4096,
            "num_predict": 64,
        },
    }

    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.time()

    with urlopen(
        request,
        timeout=90.0
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    answer = str(
        result.get("message", {}).get(
            "content",
            ""
        )
    ).strip()

    # Qwen3 should run with thinking disabled.
    # If a reasoning block leaks into content anyway,
    # discard it and keep only the final response.
    if "</think>" in answer:
        answer = answer.split(
            "</think>",
            1
        )[-1].strip()

    if answer.startswith("<think>"):
        end = answer.find("</think>")
        if end >= 0:
            answer = answer[
                end + len("</think>"):
            ].strip()

    if not answer:
        raise RuntimeError(
            "Ollama returned an empty answer"
        )

    CHAT_HISTORY.extend([
        {
            "role": "user",
            "content": user_text,
        },
        {
            "role": "assistant",
            "content": answer,
        },
    ])

    # V0.6b:
    # evaluate durable memories asynchronously.
    schedule_auto_memory(
        user_text,
        answer
    )

    if len(CHAT_HISTORY) > CHAT_HISTORY_MAX_MESSAGES:
        del CHAT_HISTORY[
            :-CHAT_HISTORY_MAX_MESSAGES
        ]

    return {
        "text": answer,
        "model": OLLAMA_MODEL,
        "processing_seconds": round(
            time.time() - started,
            2
        ),
        "history_messages": len(CHAT_HISTORY),
    }


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

        if self.path == "/memory":
            self.send_json({
                "ok": True,
                "memory":
                    persistent_memory_summary(),
            })
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/analyze":
            if self.path == "/speak":
                self.handle_speak()
                return
            if self.path == "/transcribe":
                self.handle_transcribe()
                return
            if self.path == "/chat":
                self.handle_chat()
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

    def handle_chat(self):
        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            payload = json.loads(
                self.rfile.read(length).decode(
                    "utf-8"
                )
            )

            user_text = str(
                payload.get("text") or ""
            ).strip()

            if not user_text:
                raise ValueError("missing text")

            robot_context = payload.get(
                "robot_context"
            )

            if not isinstance(
                robot_context,
                dict
            ):
                robot_context = None

            result = chat_with_ollama(
                user_text,
                robot_context=robot_context
            )

            self.send_json({
                "ok": True,
                "kind": "conversation_response",
                "text": result["text"],
                "model": result["model"],
                "processing_seconds":
                    result["processing_seconds"],
                "history_messages":
                    result["history_messages"],
                "robot_context_received":
                    isinstance(
                        robot_context,
                        dict
                    ),
            })

        except Exception as exc:
            STATE["last_error"] = str(exc)

            self.send_json({
                "ok": False,
                "error": str(exc)
            }, 400)


    def handle_transcribe(self):
        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )

            audio = base64.b64decode(
                payload.get("audio_b64", ""),
                validate=True
            )

            if not audio:
                raise ValueError("missing audio_b64")

            LATEST_TALK.write_bytes(audio)

            started = time.time()

            transcript = transcribe_audio(
                LATEST_TALK
            )

            elapsed = round(
                time.time() - started,
                2
            )

            self.send_json({
                "ok": True,
                "kind": "speech_transcription",
                "text": transcript,
                "language": WHISPER_LANGUAGE,
                "model": WHISPER_MODEL_NAME,
                "audio_bytes": len(audio),
                "processing_seconds": elapsed,
            })

        except Exception as exc:
            STATE["last_error"] = str(exc)

            self.send_json({
                "ok": False,
                "error": str(exc)
            }, 400)

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
            distance_category = "face_close"
        elif size >= face_medium_size:
            distance = "medium"
            distance_text = "a distance moyenne"
            distance_category = "face_medium"
        else:
            distance = "far"
            distance_text = "loin"
            distance_category = "face_far"

        # A newly returned presence should usually trigger a "welcome back"
        # reaction, but not every single time.
        presence_just_arrived = (
            last_kind == "presence_arrived"
            and as_float(last_event.get("at"), 0.0) > time.time() - 12
        )

        if presence_just_arrived:
            category = choose_weighted_category([
                ("presence_returned", 0.80),
                (distance_category, 0.20),
            ]) or "presence_returned"
            speech = say(category)
        else:
            # Familiarity and happiness now INFLUENCE the choice instead of
            # forcing mood_happy on every analysis.
            speech = choose_face_speech(
                distance_category=distance_category,
                active_mood=active_mood,
                memory_mood=memory_mood,
                curiosity=curiosity,
                familiarity=familiarity,
            )

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
        "description": say("no_presence", remember=False),
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
