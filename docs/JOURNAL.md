# Journal de bord — Volp-E

Ce fichier conserve les étapes importantes de l'évolution du projet.

## 16 août 2026 — Base matérielle, visage framebuffer et architecture

Cette première phase a posé les bases matérielles et logicielles de la version actuelle de Volp-E.

### Affichage, vision et comportement

* Passage du visage principal sur un rendu **framebuffer PNG**, sans Chromium, afin de gagner en stabilité sur Raspberry Pi 3A+.
* Ajout d'une bibliothèque d'expressions PNG pour les yeux, avec des assets précalculés pour un affichage rapide.
* Stabilisation de la vision avec caméra V4L2, Coral USB et suivi du regard.
* Ajout d'un cerveau externe optionnel sur PC capable d'analyser la scène et de renvoyer des intentions.
* Ajout des pensées affichées sous les yeux et du déclenchement automatique de phrases.
* Ajout d'une mémoire courte en RAM : présence, retour, proximité, perte de cible et état d'attention.
* Ajout d'une humeur active dérivée de l'énergie, de la curiosité, de la familiarité et de l'attention.
* Ajout d'une personnalité configurable dans `config/personality.json`.

### Audio

* Ajout d'une voix hybride : Piper côté PC lorsqu'il est disponible, avec secours local via `espeak-ng` sur la Raspberry Pi.
* Ajout d'une configuration audio permettant de forcer la sortie avec `VOLPE_APLAY_DEVICE`, par exemple `plughw:1,0`.

### Matériel

* Premier montage fonctionnel de la tête imprimée en PETG.
* Intégration de l'écran, de la Raspberry Pi, du Coral USB, de la caméra et du haut-parleur jack.
* Refroidissement identifié comme point à prévoir avant un usage prolongé.

## 16–17 août 2026 — Remise à plat et grosse évolution logicielle

Cette session marque une étape importante du projet : la version fonctionnelle réellement utilisée par Volp-E a été récupérée depuis la Raspberry Pi après qu'une copie locale du projet ait été altérée.

### Sauvegarde et GitHub

* Récupération de la version fonctionnelle présente dans `/opt/volp-e`.
* Sauvegarde des services `systemd` utilisés par Volp-E.
* Sauvegarde des paquets Python et système de la Raspberry Pi.
* Reconstruction d'un dépôt GitHub propre depuis la version fonctionnelle.
* Conservation des STL, de la documentation et de l'historique Git.
* Nettoyage des fichiers temporaires, backups et dépendances tierces inutiles dans le dépôt.

### Visage et vision

* Intégration du nouveau système de visage **Face V2**.
* Remplacement des anciens assets de visage par les nouveaux calques et PNG.
* Ajout du modèle `mobilenet\_ssd\_v2\_coco\_quant\_postprocess\_edgetpu.tflite`.
* Conservation du fonctionnement Coral / PyCoral côté Raspberry Pi.

### Personnalité

* Remplacement des phrases de démonstration générées par IA.
* Première banque `phrases.json` entièrement personnelle.
* Réorganisation de la sélection des phrases dans le Desktop Brain.
* La familiarité n'impose plus automatiquement `mood\_happy`.
* Mélange pondéré entre distance, continuité de présence, humeur et curiosité.
* Ajout d'une mémoire anti-répétition des dernières phrases utilisées.

### Voix

* Test d'une nouvelle voix Piper masculine.
* Adoption de **fr\_FR-tom-medium** comme voix du Desktop Brain.
* Conservation du fallback Windows TTS / `espeak-ng` si nécessaire.
* Validation du fonctionnement de Tom Medium avec le serveur `/speak`.

### Lancement Windows

* Ajout d'un lanceur `start-volpe-desktop-brain.cmd`.
* Le lanceur sélectionne automatiquement Tom Medium.
* Le Desktop Brain peut être démarré à la demande via un simple raccourci Bureau.
* Aucun démarrage automatique Windows n'est activé.

### État en fin de session

Volp-E est opérationnel avec :

* Raspberry Pi et services système fonctionnels ;
* Face V2 ;
* vision et suivi de présence ;
* Desktop Brain sur PC ;
* banque de phrases personnelle ;
* sélection de phrases plus variée ;
* anti-répétition ;
* voix masculine Tom Medium ;
* dépôt GitHub propre et documenté.

## 18 août 2026 — API de contrôle, application mobile et conversation locale

Cette session transforme Volp-E en système réellement pilotable depuis le téléphone et ajoute une chaîne complète de conversation locale, sans service d'IA payant.

### API de contrôle sur la Raspberry Pi

* Passage de l'API de contrôle sur une adresse réseau accessible depuis le LAN, tout en conservant les paramètres locaux dans `/etc/default/volp-e`.
* Ajout d'un endpoint `/api/status` pour exposer l'état de la Raspberry Pi, du Desktop Brain, de la caméra, de l'Arduino et du Coral.
* Ajout d'un endpoint `/api/system` pour remonter la température CPU, la charge système, l'utilisation de la RAM, l'espace disque et l'uptime.
* Conservation d'une architecture où la Raspberry Pi sert de **gateway centrale** entre l'application, le Desktop Brain et les futurs contrôleurs matériels.

### Application mobile / cockpit Cyberpunk

* Transformation de l'interface web en application ajoutable à l'écran d'accueil du téléphone.
* Ajout du manifest et des icônes Volp-E.
* Refonte graphique complète dans un style sombre et néon inspiré des interfaces cyberpunk.
* Compactage de la page principale pour tenir sur un écran de téléphone sans défilement.
* Organisation du cockpit avec :
  * en-tête Volp-E compact et statut online ;
  * **Core Status** et **System Telemetry** côte à côte ;
  * aperçu caméra ;
  * boutons **Camera**, **Voice Control** et **Talk**.
* Uniformisation progressive de l'interface en anglais.

### Caméra

* Ajout de `/api/camera/frame` pour récupérer une image JPEG instantanée.
* Ajout de `/api/camera/stream` pour exposer un flux MJPEG en direct.
* Réutilisation de l'image déjà produite par le système de vision afin de ne pas ouvrir une seconde fois `/dev/video0`.
* Ajout d'une page **Optical Feed** dédiée au flux live.
* Ajout d'un aperçu caméra sur la page d'accueil, actualisé automatiquement toutes les 15 secondes.
* Mise au point physique de la caméra réalisée directement depuis le téléphone grâce au flux live.

### Voice Control

* Ajout d'une page **Voice Control** permettant d'envoyer du texte à Volp-E.
* Connexion de cette interface à `/api/say`.
* Validation de la chaîne :
  * téléphone → API Raspberry Pi ;
  * Desktop Brain ;
  * Piper ;
  * retour audio vers la Raspberry Pi ;
  * lecture sur le haut-parleur de Volp-E.
* Ajout de commandes vocales rapides et d'un journal de transmissions.

### Talk Control et capture du microphone

* Ajout d'une page **Talk Control** avec bouton `HOLD TO TALK`.
* Le téléphone agit comme télécommande tandis que l'enregistrement utilise le microphone physique de Volp-E.
* Ajout des endpoints :
  * `/api/talk/start` ;
  * `/api/talk/stop` ;
  * `/api/talk/status`.
* Détection et configuration du microphone USB sur `plughw:2,0`.
* Enregistrement des prises de parole dans `/tmp/volpe-talk.wav`.
* Validation de la capture et de la lecture audio depuis la Raspberry Pi.

### Speech-to-Text

* Installation de **Faster-Whisper** sur le Desktop Brain.
* Ajout d'un endpoint `/transcribe` sur le PC.
* Ajout de `/api/talk/process` sur la Raspberry Pi pour envoyer automatiquement l'enregistrement au Desktop Brain.
* Affichage de la transcription directement dans l'interface Talk.
* Ajout d'un prétraitement audio avec FFmpeg avant transcription :
  * filtre passe-haut ;
  * filtre passe-bas ;
  * réduction légère du bruit ;
  * normalisation dynamique.
* Le prétraitement améliore nettement l'exploitation du microphone sans augmenter davantage son gain matériel.

### Cerveau conversationnel local

* Installation d'**Ollama** sur le PC.
* Adoption de **Qwen3 1.7B** comme premier modèle conversationnel local léger.
* Ajout d'un endpoint `/chat` au Desktop Brain.
* Ajout d'une personnalité système spécifique à Volp-E : réponses en français, courtes, naturelles, curieuses et adaptées à un robot compagnon.
* Ajout d'une petite mémoire de conversation côté Desktop Brain.
* Ajout de `/api/talk/think` sur la Raspberry Pi.
* Validation de la chaîne complète :

`Microphone → FFmpeg → Faster-Whisper → Qwen3/Ollama → Piper → haut-parleur`

* L'interface Talk affiche désormais les états **PROCESSING → THINKING → RESPONDING** ainsi que la transcription et la réponse générée.
* Volp-E peut maintenant recevoir une phrase orale, la comprendre, générer une réponse localement et la prononcer.

### Gestion des paroles automatiques

* Réduction drastique de la fréquence des paroles spontanées.
* Passage de `min_interval_seconds` à **180 secondes**.
* Passage de `think_cooldown_seconds` à **120 secondes**.
* Ajout d'une priorité de conversation empêchant les phrases automatiques d'interrompre une interaction Talk.
* Les états `listening`, `processing`, `thinking` et `responding` verrouillent le canal vocal.
* Après une réponse manuelle, les paroles automatiques restent bloquées pendant environ **20 secondes**.

### État en fin de session

Volp-E dispose maintenant de :

* un cockpit mobile plein écran ;
* télémétrie système en direct ;
* aperçu caméra et flux live ;
* contrôle vocal par texte ;
* capture du microphone physique ;
* transcription locale ;
* modèle conversationnel local gratuit ;
* synthèse vocale Piper ;
* priorité correcte entre conversation et comportements autonomes ;
* une chaîne conversationnelle entièrement locale, sans coût par requête.

