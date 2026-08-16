# Carnet de bord Volp-E

## 2026-08-16

- Passage du visage principal sur un rendu framebuffer PNG, sans Chromium, pour gagner en stabilite sur Raspberry Pi 3A+.
- Ajout d'une bibliotheque d'expressions PNG pour les yeux, avec assets pre-calcules pour l'affichage rapide.
- Stabilisation de la vision avec camera V4L2, Coral USB et suivi du regard.
- Ajout d'un cerveau externe optionnel sur PC pour analyser la scene et renvoyer des intentions.
- Ajout des pensees affichees sous les yeux et declenchement automatique de phrases.
- Ajout d'une memoire courte en RAM : presence, retour, proximite, perte de cible et etat d'attention.
- Ajout d'une humeur active derivee de l'energie, curiosite, familiarite et attention.
- Ajout d'une personnalite configurable dans `config/personality.json`.
- Ajout d'une voix hybride : Piper cote PC quand disponible, secours local avec `espeak-ng` sur la Raspberry Pi.
- Configuration audio compatible avec une sortie forcee via `VOLPE_APLAY_DEVICE`, par exemple `plughw:1,0`.

Notes materiel :

- Premier montage fonctionnel de la tete imprimee en PETG.
- Integration de l'ecran, Raspberry Pi, Coral USB, camera et haut-parleur jack.
- Refroidissement a prevoir avant usage prolonge.

16–17 août 2026 — Remise à plat et grosse évolution logicielle

Cette session marque une étape importante du projet : la version fonctionnelle réellement utilisée par Volp-E a été récupérée depuis la Raspberry Pi après qu'une copie locale du projet ait été altérée.

Sauvegarde et GitHub

Récupération de la version fonctionnelle présente dans /opt/volp-e.

Sauvegarde des services systemd utilisés par Volp-E.

Sauvegarde des paquets Python et système de la Raspberry Pi.

Reconstruction d'un dépôt GitHub propre depuis la version fonctionnelle.

Conservation des STL, de la documentation et de l'historique Git.

Nettoyage des fichiers temporaires, backups et dépendances tierces inutiles dans le dépôt.

Visage et vision

Intégration du nouveau système de visage Face V2.

Remplacement des anciens assets de visage par les nouveaux calques et PNG.

Ajout du modèle mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite.

Conservation du fonctionnement Coral / PyCoral côté Raspberry Pi.

Personnalité

Remplacement des phrases de démonstration générées par IA.

Première banque phrases.json entièrement personnelle.

Réorganisation de la sélection des phrases dans le Desktop Brain.

La familiarité n'impose plus automatiquement mood_happy.

Mélange pondéré entre distance, continuité de présence, humeur et curiosité.

Ajout d'une mémoire anti-répétition des dernières phrases utilisées.

Voix

Test d'une nouvelle voix Piper masculine.

Adoption de fr_FR-tom-medium comme voix du Desktop Brain.

Conservation du fallback Windows TTS / espeak-ng si nécessaire.

Validation du fonctionnement de Tom Medium avec le serveur /speak.

Lancement Windows

Ajout d'un lanceur start-volpe-desktop-brain.cmd.

Le lanceur sélectionne automatiquement Tom Medium.

Le Desktop Brain peut être démarré à la demande via un simple raccourci Bureau.

Aucun démarrage automatique Windows n'est activé.

État en fin de session

Volp-E est opérationnel avec :

Raspberry Pi et services système fonctionnels ;

Face V2 ;

vision et suivi de présence ;

Desktop Brain sur PC ;

banque de phrases personnelle ;

sélection de phrases plus variée ;

anti-répétition ;

voix masculine Tom Medium ;

dépôt GitHub propre et documenté.

