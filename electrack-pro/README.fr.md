⚡ ElecTrack Pro — Plateforme SaaS de Gestion d'Interventions Terrain pour Infrastructures Électriques

[🇬🇧 English version](README.md)

`AppSheet` `Google Apps Script` `Google Sheets` `SaaS Multi-Tenant` `Sécurité par Rôle`

## Présentation

Solution SaaS réutilisable de gestion d'interventions terrain sur chantiers d'infrastructures électriques, construite sur **AppSheet + Google Sheets + Google Apps Script**. Conçue non pas comme un simple formulaire de collecte, mais comme un **produit multi-client dès la conception** : aucun élément spécifique à un client codé en dur, ni dans le modèle de données, ni dans les formules, ni dans les scripts d'automatisation.

La plateforme pilote actuellement le suivi terrain de chantiers d'électrification pour un client national du secteur de l'énergie, sur **55 localités réparties dans 4 départements**, avec une hiérarchie de données complète (Projet → Géo → Localité → Intervention → Détail) et une gestion des accès par rôle : **Super Admin, Admin, Chef de Mission, et Superviseur restreint par zone**.

Développée par Medico Diomande — Ingénieur électromécanicien (10 ans d'expérience terrain sur des projets d'électrification financés par la Banque Mondiale / AFD / BAD) devenu architecte technique. Cette expertise métier se retrouve directement dans le produit : le modèle de données, la logique de calcul d'avancement et les règles de sécurité reflètent la réalité du terrain, pas une architecture générique.

## Impact Métier

- → Remplace les tableurs éparpillés et les rapports papier par une plateforme unique et gouvernée : avancement des chantiers en temps réel, suivi pondéré, réconciliation des matériaux
- → Alertes email automatisées sur l'inactivité des chantiers et les anomalies de tâches — plus de relance manuelle sur les chantiers à l'arrêt
- → Isolation des données par rôle : chaque superviseur terrain ne voit que sa zone d'affectation — aucune fuite de données entre projets
- → Architecture pensée dès le départ pour la revente multi-client, pas pour un déploiement unique sur-mesure

## Fonctionnalités Clés

- → Suivi d'avancement pondéré (`Avancement_Pondéré`) calculé par localité à partir de la complétion des tâches et de poids configurables
- → Pipeline automatisé de snapshot et de reporting (Apps Script, déclencheurs planifiés) alimentant classements, récapitulatifs et tableaux de consommation de matériaux
- → Détection d'anomalies et alertes automatiques envoyées aux bons destinataires selon la configuration du projet, sans email codé en dur
- → Géolocalisation des chantiers proprement distinguée de la position du soumetteur du formulaire (une nuance subtile mais critique en collecte de données terrain)
- → Rattachement utilisateur-projet géré via une véritable table de jointure, et non une liste fragile séparée par virgules

## Points Forts Architecturaux

| Enjeu | Approche |
|---|---|
| **Multi-tenant** | Un classeur Google Sheets dédié par client (v2) — élimine structurellement le risque de fuite de données entre clients, au-delà du simple filtre |
| **Sécurité** | Chaque table filtrée par `Actif=TRUE` + rôle + périmètre zone/projet ; l'auto-référence circulaire sur la table Utilisateurs résolue via une table miroir en lecture seule |
| **Automatisation** | Couche Apps Script (et non les Bots AppSheet) pour l'envoi d'emails, avec verrouillage anti-chevauchement d'exécutions et wrappers de réessai sur toutes les lectures Sheets |
| **Intégrité des données** | Clés hexadécimales stables — jamais de texte d'affichage modifiable — pour éviter la rupture silencieuse d'intégrité référentielle au renommage |

## Leçons Apprises (extraits)

Pièges réels rencontrés et documentés en durcissant la plateforme pour un déploiement commercial :

- **`LOOKUP()` échoue silencieusement sur les colonnes de type Ref dans AppSheet** — elle retourne la première ligne de la table cible au lieu de générer une erreur. Solution fiable : `ANY(SELECT(Table[col_retour], [col_clé] = [_THISROW].[col_ref]))`.
- **Conflit App Formula + Initial Value** : dériver une clé étrangère par App Formula à partir d'une colonne non encore renseignée au moment de la saisie casse silencieusement tous les `Valid_If` en aval. Correction : ne conserver que l'expression Initial Value.
- **La précision décimale compte pour les calculs en chaîne** : une colonne virtuelle de type Pourcentage tronquée à 2 décimales a propagé silencieusement une erreur d'arrondi dans une formule d'avancement pondéré dépendante — corrigé en augmentant la précision, pas en revérifiant le calcul.
- **AppSheet ne peut pas référencer une table dans son propre filtre de sécurité** — résolu via une table miroir en lecture seule.

## Stack Technique

```
Frontend :      AppSheet (application no-code mobile + web)
Backend :       Google Sheets (modèle de données structuré multi-table)
Automatisation : Google Apps Script (déclencheurs planifiés, alertes email, pipeline de snapshot)
```

## Pourquoi Mon Parcours Fait la Différence

Dix ans à piloter des chantiers d'électrification sur des projets financés par la Banque Mondiale, l'AFD et la BAD m'ont appris ce qui casse réellement un système de reporting terrain en pratique : connectivité peu fiable, superviseurs soumettant depuis une mauvaise localisation, réconciliation de matériaux qui doit survivre au renommage de données de référence. L'architecture d'ElecTrack Pro — le modèle de sécurité, les alertes automatisées, la logique d'avancement pondéré — est construite autour de ces cas réels, pas autour d'un tutoriel CRUD générique.

---

Auteur : Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Disponible pour missions à distance
