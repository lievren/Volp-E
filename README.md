# Volp-E Raspberry Pi starter

Socle actuel du cerveau de Volp-E.

Ce paquet installe :

- visage SVG anime en paysage pour ecran 5 pouces ;
- serveur local `volpe-brain` sur `http://127.0.0.1:8765` ;
- detection camera via Coral/PyCoral ;
- mode veille automatique apres 5 minutes sans presence ;
- client optionnel vers un cerveau externe sur PC.
- autologin console sur `tty1` pour lancer le visage sans clavier.

## Installation sur la Raspberry

```bash
cd ~/volp-e-pi
sudo ./install.sh
sudo reboot
```

## Mise a jour rapide

Quand les paquets systeme sont deja installes, utiliser ceci au lieu de `install.sh` :

```bash
cd ~/volp-e-pi
sudo ./update.sh
```

## Services

```bash
sudo systemctl status volpe-brain.service --no-pager
sudo systemctl status volpe-vision.service --no-pager
```

## Modes visage

```bash
curl 'http://127.0.0.1:8765/api/mode?mode=normal'
curl 'http://127.0.0.1:8765/api/mode?mode=sleepy'
curl 'http://127.0.0.1:8765/api/mode?mode=alert'
curl 'http://127.0.0.1:8765/api/mode?mode=standby'
curl 'http://127.0.0.1:8765/api/state'
```

## Cerveau externe sur PC

Sur le PC, lancer :

```powershell
cd C:\Users\renau\Documents\Codex\2026-05-20\files-mentioned-by-the-user-visage\volp-e-pi\desktop-brain
.\start-desktop-brain.ps1
```

Le serveur PC ecoute sur :

```txt
http://0.0.0.0:8787
```

Depuis la Pi, configurer l'adresse IP du PC dans `/etc/default/volp-e`.
Exemple si le PC est `IP_DU_PC` :

```bash
sudo nano /etc/default/volp-e
```

Mettre :

```bash
VOLPE_EXTERNAL_BRAIN_URL=http://IP_DU_PC:8787
```

Puis :

```bash
sudo systemctl restart volpe-brain.service
curl 'http://127.0.0.1:8765/api/external/check'
curl 'http://127.0.0.1:8765/api/analyze_scene'
curl 'http://127.0.0.1:8765/api/think'
```

Le serveur PC sauvegarde la derniere image recue ici :

```txt
desktop-brain/latest_scene.jpg
```

Le cerveau PC repond maintenant avec une intention structuree :

```json
{
  "description": "Presence detectee a distance moyenne. Position: center/center.",
  "mood": "curious",
  "suggested_mode": "alert",
  "speech": "Je te vois devant moi.",
  "attention": {
    "priority": "person",
    "x": 0.0,
    "y": 0.0,
    "size": 0.5
  },
  "actions": [
    {"type": "face_mode", "mode": "alert"}
  ]
}
```

La Pi stocke cette reponse dans `/api/state`, section `thought`, et applique le mode visage conseille. Quand une presence est detectee, une analyse automatique est declenchee au maximum toutes les 30 secondes.

La Pi envoie aussi `face_recent`, `vision_age` et `memory` au cerveau PC. Si une analyse arrive en retard et propose `normal` alors qu'une presence est active, la Pi garde le visage en `alert`.

## Memoire courte

Volp-E garde une memoire RAM des derniers evenements, visible dans `/api/state`, section `memory`.

Elle retient notamment :

- arrivee d'une presence ;
- perte d'une presence ;
- presence proche ;
- entree en veille ;
- derniere analyse recue du cerveau PC.

Cette memoire ne s'ecrit pas en boucle sur la carte SD. Elle sert deja a calculer une humeur courte (`calm`, `curious`, `attentive`, `searching`, `sleepy`, `happy`, `dreaming`) et a enrichir les phrases du cerveau PC.

Elle expose aussi quelques curseurs de personnalite :

- `energy` : energie interne, baisse dans le calme et remonte avec la presence ;
- `curiosity` : monte quand quelque chose attire son attention ;
- `familiarity` : augmente doucement quand une presence revient souvent ;
- `attention` : cible actuelle de son attention (`person`, `person_close`, `searching`, `ambient`, `dream`).

## Personnalite configurable

La personnalite de Volp-E se regle dans :

```txt
config/personality.json
```

Ce fichier pilote deja :

- le nom et la prononciation vocale (`name`, `pronunciation`) ;
- le profil global (`profile`, `description`) ;
- les curseurs de ton (`warmth`, `curiosity`, `playfulness`, `talkativeness`, etc.) ;
- les delais de parole et de pensee ;
- la vitesse a laquelle la memoire courte gagne ou perd energie, curiosite et familiarite ;
- les seuils d'attention camera ;
- une premiere table de correspondance pour les futures expressions PNG.

Apres modification sur la Pi :

```bash
cd ~/volp-e-pi
sudo ./update.sh
sudo systemctl restart volpe-brain.service
curl 'http://127.0.0.1:8765/api/personality'
```

Apres modification cote PC, redemarrer simplement :

```powershell
cd desktop-brain
.\start-desktop-brain.ps1
```

Le cerveau PC expose aussi :

```txt
http://127.0.0.1:8787/personality
```

## Banque de phrases

Le cerveau PC lit les phrases dans :

```txt
desktop-brain/phrases.json
```

Objectif conseille pour une premiere vraie personnalite :

- `face_close` : 20 phrases quand quelqu'un est tres proche.
- `face_medium` : 20 phrases quand quelqu'un est devant lui a distance normale.
- `face_far` : 15 phrases quand une presence est plus loin.
- `no_presence` : 15 phrases quand la scene est calme.
- `presence_returned` : 10 phrases quand quelqu'un revient apres une courte absence.
- `presence_continues` : 10 phrases quand Volp-E suit deja quelqu'un.
- `presence_lost` : 10 phrases quand une presence sort du champ.
- `mood_happy` : 10 phrases quand Volp-E est content ou reconnait une presence familiere.
- `mood_sleepy` : 10 phrases quand son energie baisse.
- `mood_curious` : 10 phrases quand sa curiosite monte.
- `description_face` : 10 phrases d'analyse interne avec `{distance_text}`, `{horizontal}`, `{vertical}`.

Pour l'instant, vise des phrases courtes, lisibles en 1 ou 2 lignes sur l'ecran. Ton doux, curieux, un peu robot compagnon.

## Voix hybride

Quand une phrase est recue du cerveau PC, la Pi essaie d'abord de demander une voix plus naturelle au serveur desktop (`/speak`). Si le PC n'est pas joignable, Volp-E parle quand meme avec `espeak-ng` sur la Raspberry.

Sur le PC, le serveur desktop utilise Piper si `desktop-brain/piper/piper.exe` et la voix `desktop-brain/voices/fr_FR-siwis-medium.onnx` sont presents. Sinon, il tente la voix Windows. Le texte affiche reste intact, mais la synthese vocale remplace `Volp-E` par `Volpi` pour eviter la prononciation `volp eu`.

Les pensees recues du cerveau externe declenchent automatiquement la voix. La Pi sauvegarde le dernier son recu dans `/tmp/volpe-speech.wav`, puis le joue avec `aplay`, comme le test manuel. Si une autre sortie audio doit etre forcee, ajoute par exemple `VOLPE_APLAY_DEVICE=plughw:1,0` dans `/etc/default/volp-e`, puis redemarre `volpe-brain.service`.

Installation de Piper sur Windows :

```powershell
cd desktop-brain
.\install-piper-windows.ps1
.\start-desktop-brain.ps1
```

Test rapide sur la Pi :

```bash
curl 'http://127.0.0.1:8765/api/say?text=Bonjour%20je%20suis%20Volp-E'
curl 'http://127.0.0.1:8765/api/state'
aplay /tmp/volpe-speech.wav
```

Dans `/api/state`, la section `voice.last_engine` indique `desktop` si le PC a genere la voix, ou `espeak-ng` si la Pi a utilise la voix locale de secours. `voice.last_desktop_engine` indique ensuite `piper` ou `windows-sapi`.

## Prochaines etapes

- brancher une vraie analyse image cote PC ;
- remplacer la voix desktop basique par une voix TTS plus naturelle ;
- ajouter Arduino Uno en liaison serie pour tete, bras et roues ;
- transformer la detection visage en consignes pan/tilt.
