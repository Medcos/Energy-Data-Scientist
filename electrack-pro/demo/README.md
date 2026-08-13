# Démo

Ce dossier accueille le lien vidéo ou le GIF de démonstration d'ElecTrack Pro. Comme pour `docs/screenshots/`, je n'ai pas accès à ton interface AppSheet réelle — cette partie reste à produire de ton côté. Voici comment structurer ça efficacement.

## Format recommandé : GIF court + lien vidéo complet

Un repo GitHub affiche un GIF directement dans le README (contrairement à une vidéo, qui n'a pas de lecteur natif) — c'est ce qui capte l'attention en premier lors d'une visite rapide. La vidéo complète (Loom, YouTube non listé) vient en complément pour qui veut creuser.

## Ce qu'il faut montrer, dans l'ordre

1. **Le problème en une phrase** (à l'oral dans la vidéo, ou en légende du GIF) : "Suivi terrain de chantiers d'électrification sur plusieurs zones, sans tableur éclaté"
2. **Saisie terrain** (mobile) — un superviseur enregistre une intervention en quelques taps. C'est le moment le plus parlant pour un client non technique.
3. **Bascule vers le tableau de bord** — la même donnée apparaît immédiatement dans l'avancement pondéré par localité
4. **Vue par rôle** — montrer rapidement qu'un Superviseur ne voit que sa zone, alors qu'un Admin voit tout
5. **Un email d'alerte reçu** (inactivité ou anomalie) — preuve que l'automatisation tourne réellement, pas juste l'interface

Durée cible : 60–90 secondes pour le GIF/vidéo courte. Une version longue (3–5 min) peut aller plus loin sur l'architecture si tu la portes toi-même à l'oral.

## Anonymisation

Mêmes règles que pour `docs/screenshots/` : aucun nom de client, de localité réelle, ou email réel visible à l'écran. Utilise un compte de démonstration ou floute les zones sensibles au montage.

## Intégration dans le README principal

Une fois le GIF prêt, ajoute-le en haut du `README.md` (juste après le titre, avant la section Overview) avec :

```markdown
![Démo ElecTrack Pro](demo/demo.gif)

🎥 [Voir la démo complète (2 min)](https://loom.com/share/ton-lien)
```

Placé tout en haut, c'est la première chose qu'un recruteur ou un client potentiel voit en ouvrant le repo — avant même de lire une ligne de texte.

## Outils suggérés pour l'enregistrement

- **GIF** : ScreenToGif (Windows) ou Kap (Mac) — export direct en `.gif` optimisé pour le web (viser <10 Mo pour un chargement rapide sur GitHub)
- **Vidéo complète** : Loom (lien partageable en un clic, pas besoin d'héberger le fichier toi-même)
