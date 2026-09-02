# Audit des 29 feuilles — `Localités.xlsx` (ElecTrack Pro / P2AE)

**Date :** 27 août 2026  |  **Fichier source :** `data/raw/Localites_raw.xlsx` (non versionné)

## 1. Vue d'ensemble

- **29 feuilles** au total (conforme au plan).

- **7 feuilles** contiennent des données personnelles identifiables (email, nom, GPS précis, téléphone).

- **10 feuilles** sont directement mobilisées par le pipeline prédictif de ce projet ; les 19 autres relèvent du paramétrage applicatif d'ElecTrack Pro (rôles UI, filtres, configuration géo/projet) et sont hors périmètre.


## 2. Tableau complet des 29 feuilles

| Feuille | Lignes | Colonnes | Lignes vides | % cellules manquantes | PII | Usage dans le pipeline |
|---|---:|---:|---:|---:|:---:|---|
| `Anomalies_Taches` | 6 | 7 | 0 | 0.0% | Non | Écarts terrain signalés (A, C) |
| `Catalogue_Materiel` | 28 | 8 | 0 | 0.0% | Non | Référentiel matériel/unités (A) |
| `Categories_Taches` | 3 | 4 | 0 | 0.0% | Non | — |
| `Details_Intervention` | 1584 | 15 | 3 | 18.9% | Non | Journal quantités réalisées horodaté (B) |
| `Filtre_Performance` | 7 | 9 | 0 | 39.7% | Oui | — |
| `Filtre_Rapport` | 1 | 3 | 0 | 0.0% | Non | — |
| `Geo_Config` | 9 | 5 | 0 | 0.0% | Non | — |
| `Helper_Calcul` | 997 | 15 | 0 | 0.0% | Non | Jointure Objectifs x Localités x Tâches déjà prête (A) |
| `Historique_Avnt_Geo` | 100 | 8 | 0 | 0.0% | Non | Série hebdomadaire avancement (B, C) |
| `Interventions` | 637 | 11 | 1 | 8.1% | Oui | — |
| `Journal_Chantier` | 36 | 15 | 0 | 21.3% | Oui | Effectif/météo/difficultés (bonus, clairsemé) |
| `Localités` | 55 | 9 | 0 | 11.1% | Oui | Référentiel des 55 localités (A) |
| `Objectifs` | 1003 | 10 | 6 | 10.4% | Non | Quantités prévues (A, B) |
| `Parametres_Poids` | 13 | 7 | 0 | 0.0% | Non | Pondération des tâches (A) |
| `Photos_Chantier` | 31 | 4 | 0 | 12.9% | Non | — |
| `Projets_Config` | 1 | 11 | 0 | 0.0% | Non | — |
| `Recap_Departements` | 5 | 12 | 0 | 1.7% | Non | — |
| `Recap_Departements_Prevus` | 5 | 12 | 0 | 1.7% | Non | — |
| `Recap_Localites` | 55 | 15 | 0 | 0.0% | Non | — |
| `Recap_Localites_Prevus` | 55 | 15 | 0 | 0.0% | Non | — |
| `Recap_Materiaux_Realisés` | 28 | 8 | 0 | 0.0% | Non | — |
| `Recap_Objectifs` | 28 | 9 | 0 | 0.0% | Non | — |
| `Referentiels_Snapshot` | 110 | 2 | 0 | 0.0% | Non | — |
| `Roles` | 7 | 4 | 0 | 0.0% | Oui | — |
| `Top_Localites` | 55 | 10 | 0 | 0.0% | Non | Avancement % et statut par localité (A, C) |
| `Top_Localites_Tri` | 55 | 10 | 0 | 0.0% | Non | — |
| `Type_Travaux` | 6 | 5 | 0 | 0.0% | Non | — |
| `Utilisateurs` | 7 | 7 | 0 | 10.2% | Oui | — |
| `Utilisateurs_Projets` | 7 | 3 | 0 | 0.0% | Oui | — |

## 3. Détail des colonnes sensibles identifiées

| Feuille | Colonne | Type de PII | Valeurs non nulles | Traitement appliqué |
|---|---|---|---:|---|
| `Filtre_Performance` | `Email_Utilisateur` | email | 7 | email -> agent_id |
| `Filtre_Performance` | `Nom_Complet` | nom | 7 | colonne supprimée |
| `Interventions` | `Coordonnees_GPS` | GPS | 635 | colonne supprimée |
| `Interventions` | `Utilisateur` | email | 636 | email -> agent_id |
| `Journal_Chantier` | `Localisation` | GPS | 29 | colonne supprimée |
| `Journal_Chantier` | `Utilisateur` | email | 36 | email -> agent_id |
| `Localités` | `Coordonnees_GPS` | GPS | 55 | colonne supprimée |
| `Roles` | `Email` | email | 7 | email -> agent_id |
| `Roles` | `Nom_Complet` | nom | 7 | colonne supprimée |
| `Utilisateurs` | `Email` | email | 7 | email -> agent_id |
| `Utilisateurs` | `Nom_Complet` | nom | 7 | colonne supprimée |
| `Utilisateurs` | `Telephone` | téléphone | 2 | colonne supprimée |
| `Utilisateurs_Projets` | `Email_User` | email | 7 | email -> agent_id |

## 4. Anomalies et points de vigilance détectés

1. **Échelle incohérente de l'avancement** entre `Top_Localites` (fraction 0–1) et `Historique_Avnt_Geo` (pourcentage 0–100), malgré un nommage de colonne identique (`Avancement_HTA_%`). Corrigé par standardisation en pourcentage dans les tables pivot.
2. **6 lignes entièrement vides** dans `Objectifs`, **3** dans `Details_Intervention`, **1** dans `Interventions` — artefacts d'export Excel, supprimés lors de l'extraction.
3. **`Journal_Chantier` est clairsemé** (36 lignes, `Effectif` souvent vide, `Localisation` renseignée dans 29/36 lignes seulement) — traité comme enrichissement optionnel non bloquant, conformément au plan.
4. **Doublon de désignation** dans `Catalogue_Materiel` (une désignation apparaît deux fois) — sans impact sur les jointures utilisées (faites sur `ID_Materiel`, unique).
5. **Une valeur `Toutes`** dans la colonne département de `Historique_Avnt_Geo` (agrégat national, 20 lignes sur 100) — conservée mais sans trajectoire théorique calculable (pas de date de fin contractuelle unique).
6. **Jointure `Objectifs` → `Helper_Calcul` : 6 lignes orphelines**, entièrement dues aux lignes vides du point 2 ci-dessus (aucune vraie perte de données une fois le nettoyage appliqué).

## 5. Feuilles hors périmètre (paramétrage applicatif, non exploitées ce jour)

`Projets_Config`, `Geo_Config`, `Categories_Taches`, `Type_Travaux`, `Referentiels_Snapshot`, `Filtre_Rapport`, `Filtre_Performance`, `Roles`, `Utilisateurs_Projets`, `Photos_Chantier`, `Recap_Departements`, `Recap_Departements_Prevus`, `Recap_Localites`, `Recap_Localites_Prevus`, `Recap_Materiaux_Realisés`, `Recap_Objectifs`, `Top_Localites_Tri`.

Elles ont néanmoins été anonymisées et exportées (`data/processed/sheets_anonymises/`) par souci d'exhaustivité et pour rester disponibles si un besoin apparaît en Jour 2 ou 3.
