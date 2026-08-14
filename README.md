# Volp-E

Volp-E est un projet de robot compagnon compact, expressif et évolutif, combinant robotique, impression 3D, vision par ordinateur et intelligence artificielle.

L'objectif n'est pas seulement de construire un robot capable de bouger ou d'exécuter des commandes, mais de créer un petit compagnon qui donne réellement l'impression d'être présent : il regarde, réagit, se déplace, manipule son environnement et pourra progressivement développer de nouvelles interactions.

Le projet est développé progressivement, en privilégiant des fonctions simples, fiables et modulaires plutôt qu'un système trop complexe essayant de tout faire en même temps.

## Vision

Volp-E doit rester :

- compact ;
- relativement simple à fabriquer ;
- évolutif ;
- modulaire ;
- expressif ;
- capable d'interagir avec son environnement réel.

À terme, Volp-E pourrait devenir à la fois :

- un robot compagnon ;
- une plateforme expérimentale de robotique ;
- un projet open source documenté ;
- un support pour apprendre la programmation, l'électronique et la conception 3D ;
- et potentiellement un véritable produit.

## Version actuelle

La version actuelle pose les bases du cerveau et du visage :

- visage animé en framebuffer pour écran 5 pouces ;
- serveur local `volpe-brain` sur `http://127.0.0.1:8765` ;
- détection caméra via Coral/PyCoral ;
- suivi du regard par mouvement des pupilles ;
- mode veille automatique après 5 minutes sans présence ;
- cerveau externe optionnel sur PC ;
- mémoire courte en RAM ;
- humeur active ;
- banque de phrases personnalisable.

Le rendu principal n'utilise plus Chromium : le visage est dessiné directement dans `/dev/fb0`, ce qui évite les pages blanches et réduit la charge sur une Raspberry Pi 3A+.

## Volp-E V2

L'objectif actuel est de construire une V2 compacte et fonctionnelle.

Dimensions visées pour le robot complet : environ 30 à 40 cm de hauteur.

La V2 doit idéalement être capable de :

- afficher un visage animé ;
- suivre une personne du regard ;
- orienter sa tête ;
- détecter certains objets avec sa caméra ;
- utiliser un bras robotique ;
- attraper un objet prédéfini ;
- se déplacer sur roues ;
- coordonner perception, navigation et manipulation.

## Tête

La tête actuelle mesure approximativement :

- 125 mm de large ;
- 40 mm de profondeur ;
- 80 mm de haut ;
- environ 400 g une fois complètement assemblée.

Elle contient notamment :

- un écran d'environ 5 pouces ;
- une caméra ;
- l'électronique nécessaire au visage ;
- un système pan/tilt.

Deux servomoteurs seront utilisés :

- pan : rotation gauche/droite ;
- tilt : mouvement haut/bas.

Pour le premier prototype, des MG996R seront utilisés. Une optimisation avec des servos plus petits pourra être étudiée plus tard afin de réduire le poids et la consommation électrique.

## Système de regard

Une fonction importante de Volp-E est le suivi du regard.

La caméra détecte la position d'une personne et le robot adapte :

- l'orientation de sa tête ;
- la position de ses yeux à l'écran.

### Utiliser le clignement pour masquer le calcul

Une idée importante du projet consiste à transformer les limites techniques en comportement naturel.

Au lieu de déplacer continuellement les yeux :

1. Volp-E regarde dans une direction.
2. Le système détecte qu'une nouvelle position doit être regardée.
3. Volp-E ferme les yeux.
4. Pendant le clignement, le système calcule la nouvelle position.
5. Les yeux se rouvrent directement dans la nouvelle direction.

Le délai informatique devient donc une animation naturelle du personnage. Cette limitation peut ainsi devenir une caractéristique de la personnalité de Volp-E.

## Bras robotique

La V2 utilisera probablement un bras simple composé de :

- 3 axes principaux ;
- 1 pince.

Soit environ 4 servomoteurs.

Pour le premier prototype, 4 MG996R seront utilisés. Le bras n'a pas vocation dans un premier temps à manipuler n'importe quel objet : l'objectif est d'obtenir une démonstration fiable dans un environnement connu.

## Détection et manipulation d'objets

Un premier scénario envisagé : Volp-E doit pouvoir reconnaître une boîte ou un petit objet spécialement conçu pour lui.

L'objet pourrait comporter :

- un motif visuel ;
- un symbole ;
- un marqueur ;
- ou un code facilement identifiable par la caméra.

L'objectif n'est donc pas immédiatement de faire de la reconnaissance universelle d'objets.

La logique pourrait être :

```text
Caméra -> Détection -> Navigation -> Positionnement -> Bras -> Préhension
```

Exemple :

1. Volp-E détecte une boîte.
2. Il estime sa position dans l'image.
3. Il s'oriente vers elle.
4. Il se déplace jusqu'à une position connue.
5. Il effectue éventuellement une correction de position.
6. Le bras exécute une trajectoire prédéfinie.
7. La pince attrape la boîte.
8. Volp-E peut ensuite la déplacer.

Cette approche permet de segmenter le problème en plusieurs tâches simples.

## Architecture électronique

### Raspberry Pi 3 A+

Responsabilités envisagées :

- caméra ;
- vision par ordinateur ;
- interface graphique ;
- visage ;
- logique principale ;
- comportement ;
- communication avec les autres modules.

### Google Coral USB Accelerator

Le Coral est utilisé pour accélérer certaines opérations liées à la vision ou à l'intelligence artificielle.

### Arduino Uno

Responsabilités envisagées :

- contrôle des servomoteurs ;
- contrôle moteur ;
- tâches temps réel ;
- exécution des commandes reçues du Raspberry Pi.

L'idée générale est de séparer clairement la réflexion et l'action :

```text
Le Raspberry Pi décide.
L'Arduino exécute.
```

## Matériel envisagé

Matériel actuellement disponible :

- 6 x MG996R ;
- 1 x petit servo SMS2309S ;
- 1 x TT Motor 2025 3-18.

Pour le premier montage :

- tête : 2 x MG996R ;
- bras : 4 x MG996R.

Les moteurs destinés aux roues seront achetés dans une seconde phase. Pour la locomotion, des moteurs DC avec réducteur seront probablement plus adaptés que des servomoteurs classiques.

## Mobilité

La base mobile n'est pas encore définitivement conçue.

La solution actuellement privilégiée est :

- deux roues motrices ;
- éventuellement une roulette folle ;
- moteurs DC avec réducteur.

Les chenilles ont également été envisagées, mais les roues semblent pour l'instant plus simples, compactes et adaptées à la V2.

## Architecture logicielle

Volp-E doit fonctionner avec plusieurs modules relativement indépendants.

```text
Caméra
  -> Perception
  -> Détection de cible
  -> Décision
  -> Navigation
  -> Positionnement
  -> Bras
  -> Préhension
```

Le principe est d'éviter un énorme programme central essayant de tout gérer simultanément. Chaque module possède une responsabilité claire.

Cela permettra également de remplacer plus tard le Raspberry Pi par un ordinateur plus puissant sans reconstruire toute l'architecture logicielle.

## Installation sur la Raspberry

```bash
cd ~/volp-e-pi
sudo ./install.sh
sudo reboot
```

## Mise à jour rapide

Quand les paquets système sont déjà installés, utiliser ceci au lieu de `install.sh` :

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
cd .\desktop-brain
.\start-desktop-brain.ps1
```

Le serveur PC écoute sur :

```txt
http://0.0.0.0:8787
```

Depuis la Pi, configurer l'adresse IP du PC dans `/etc/default/volp-e`.

```bash
sudo nano /etc/default/volp-e
```

Mettre :

```bash
VOLPE_EXTERNAL_BRAIN_URL=http://YOUR_PC_IP:8787
```

Puis :

```bash
sudo systemctl restart volpe-brain.service
curl 'http://127.0.0.1:8765/api/external/check'
curl 'http://127.0.0.1:8765/api/analyze_scene'
curl 'http://127.0.0.1:8765/api/think'
```

Le serveur PC sauvegarde la dernière image reçue ici :

```txt
desktop-brain/latest_scene.jpg
```

Ces fichiers de debug sont ignorés par Git.

Le cerveau PC répond avec une intention structurée :

```json
{
  "description": "Présence détectée à distance moyenne. Position: center/center.",
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

La Pi stocke cette réponse dans `/api/state`, section `thought`, et applique le mode visage conseillé. Quand une présence est détectée, une analyse automatique est déclenchée au maximum toutes les 30 secondes.

La Pi envoie aussi `face_recent`, `vision_age` et `memory` au cerveau PC. Si une analyse arrive en retard et propose `normal` alors qu'une présence est active, la Pi garde le visage en `alert`.

## Mémoire courte

Volp-E garde une mémoire RAM des derniers événements, visible dans `/api/state`, section `memory`.

Elle retient notamment :

- arrivée d'une présence ;
- perte d'une présence ;
- présence proche ;
- entrée en veille ;
- dernière analyse reçue du cerveau PC.

Cette mémoire ne s'écrit pas en boucle sur la carte SD. Elle sert déjà à calculer une humeur courte (`calm`, `curious`, `attentive`, `searching`, `sleepy`, `happy`, `dreaming`) et à enrichir les phrases du cerveau PC.

Elle expose aussi quelques curseurs de personnalité :

- `energy` : énergie interne, baisse dans le calme et remonte avec la présence ;
- `curiosity` : monte quand quelque chose attire son attention ;
- `familiarity` : augmente doucement quand une présence revient souvent ;
- `attention` : cible actuelle de son attention (`person`, `person_close`, `searching`, `ambient`, `dream`).

## Banque de phrases

Le cerveau PC lit les phrases dans :

```txt
desktop-brain/phrases.json
```

Objectif conseillé pour une première vraie personnalité :

- `face_close` : 20 phrases quand quelqu'un est très proche ;
- `face_medium` : 20 phrases quand quelqu'un est devant lui à distance normale ;
- `face_far` : 15 phrases quand une présence est plus loin ;
- `no_presence` : 15 phrases quand la scène est calme ;
- `presence_returned` : 10 phrases quand quelqu'un revient après une courte absence ;
- `presence_continues` : 10 phrases quand Volp-E suit déjà quelqu'un ;
- `presence_lost` : 10 phrases quand une présence sort du champ ;
- `mood_happy` : 10 phrases quand Volp-E est content ou reconnaît une présence familière ;
- `mood_sleepy` : 10 phrases quand son énergie baisse ;
- `mood_curious` : 10 phrases quand sa curiosité monte ;
- `description_face` : 10 phrases d'analyse interne avec `{distance_text}`, `{horizontal}`, `{vertical}`.

Pour l'instant, viser des phrases courtes, lisibles en 1 ou 2 lignes sur l'écran. Ton doux, curieux, un peu robot compagnon.

## Volp-E Adventures

Une des idées centrales apparues pendant le développement est de transformer Volp-E en interface physique d'un jeu.

Volp-E resterait un robot compagnon autonome, mais une seconde couche existerait : une aventure interactive vécue à travers le robot.

Le joueur pourrait découvrir progressivement une histoire grâce aux interactions avec Volp-E. Le robot pourrait utiliser :

- son écran ;
- ses yeux ;
- ses mouvements ;
- son bras ;
- ses déplacements ;
- des sons ;
- des objets réels ;
- des indices cachés ;
- des codes visuels.

Volp-E pourrait :

- afficher mystérieusement un symbole ;
- regarder régulièrement vers un endroit particulier ;
- demander qu'on lui apporte un objet ;
- reconnaître un objet physique appartenant au jeu ;
- révéler un message après une action ;
- transporter une petite boîte ;
- débloquer une nouvelle expression ;
- débloquer une nouvelle capacité ;
- lancer une quête ;
- donner des indices progressivement.

L'objectif serait d'obtenir quelque chose à mi-chemin entre robot compagnon, jeu narratif et objet interactif réel.

## Roadmap

### Phase 1 - Prototype mécanique

- [ ] Finaliser la nouvelle tête
- [ ] Finaliser le pan/tilt
- [ ] Tester le poids et l'équilibrage
- [ ] Monter les servos
- [ ] Concevoir le bras
- [ ] Tester la pince

### Phase 2 - Expression

- [ ] Créer les différents yeux
- [ ] Ajouter le clignement
- [x] Ajouter le suivi du regard
- [ ] Synchroniser regard et tête
- [ ] Créer plusieurs expressions

### Phase 3 - Vision

- [x] Détection d'une personne
- [x] Suivi d'une personne
- [ ] Détection d'un objet prédéfini
- [ ] Estimation de la position de la cible

### Phase 4 - Manipulation

- [ ] Programmer les mouvements du bras
- [ ] Définir une position de préhension
- [ ] Attraper une boîte prédéfinie
- [ ] Lever l'objet
- [ ] Déplacer l'objet

### Phase 5 - Mobilité

- [ ] Choisir les moteurs
- [ ] Concevoir la base
- [ ] Installer les roues
- [ ] Contrôler les moteurs avec l'Arduino
- [ ] Navigation vers une cible
- [ ] Positionnement devant un objet

### Phase 6 - Volp-E Adventures

- [ ] Définir l'univers
- [ ] Définir le système de progression
- [ ] Créer une première quête
- [ ] Ajouter des objets physiques interactifs
- [ ] Ajouter les premiers événements narratifs

## Documentation

Le développement de Volp-E sera progressivement documenté.

Supports envisagés :

- GitHub ;
- vidéos ;
- photos des prototypes ;
- modèles 3D ;
- fichiers STL ;
- code source ;
- schémas électroniques ;
- journal de développement.

L'objectif est de conserver une trace de chaque évolution du robot et de pouvoir suivre son développement de version en version.

## Philosophie

Volp-E est construit progressivement.

Chaque limitation peut devenir une idée. Chaque prototype peut apporter quelque chose à la version suivante.

Le but n'est pas de fabriquer immédiatement le robot parfait. Le but est de construire un robot un peu plus vivant à chaque version.

## Licence

Ce projet est actuellement distribué sous licence MIT.
Volp-E Adventures, l’univers narratif, les personnages, logos et éléments de jeu ne sont pas couverts par la licence MIT du code
