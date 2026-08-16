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

