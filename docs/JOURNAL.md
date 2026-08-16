# Journal de bord — Volp-E

Ce fichier conserve les étapes importantes de l'évolution du projet.

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

