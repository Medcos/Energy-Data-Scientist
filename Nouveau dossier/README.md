# p2ae-rollout-forecast

Modélisation prédictive de l'avancement et de l'approvisionnement — Projet P2AE (SBEE Bénin, 4 départements, 55 localités).

Deuxième volet du portfolio de data science appliquée à l'énergie et aux infrastructures, après la maintenance prédictive (classification, F1 = 0,88, SHAP, dashboard Streamlit). Ce projet s'appuie sur les données réelles et vivantes du chantier P2AE que je pilote via ElecTrack Pro, pour construire un pipeline unique alimentant trois modèles légers :

- **A. Ressources** — quantité de matériel restant à livrer par localité × tâche (régression)
- **B. Avancement** — projection de l'avancement HTA/BT à S+2 / S+4 par département (régression temporelle)
- **C. Risque de retard** — probabilité qu'une localité prenne du retard sur son planning contractuel (classification)

## ⚠️ Note de confidentialité

Les données sources (`data/raw/Localites_raw.xlsx`) proviennent d'un projet réel financé par un bailleur international et contiennent des données personnelles (emails d'agents terrain, coordonnées GPS précises de sites et de bases-vie). **Ce fichier n'est jamais versionné** (voir `.gitignore`).

Seules des données **anonymisées et agrégées** sont publiées dans `data/processed/` :
- les emails sont remplacés par un identifiant stable (`agent_01`…`agent_07`), cohérent entre toutes les feuilles ;
- les coordonnées GPS précises et les numéros de téléphone sont supprimés (le département/la commune, déjà présents par ailleurs, suffisent à la démonstration) ;
- les noms complets sont supprimés.

Le détail de cette anonymisation (feuille par feuille, colonne par colonne) est documenté dans [`reports/audit_feuilles_localites.md`](reports/audit_feuilles_localites.md).

## Avancement du projet

- [x] **Jour 1** — Cadrage écrit, audit des 29 feuilles, extraction et anonymisation, construction de la table pivot
  → [`reports/cadrage_jour1.md`](reports/cadrage_jour1.md) · [`reports/audit_feuilles_localites.md`](reports/audit_feuilles_localites.md) · [`notebooks/01_extraction_anonymisation.ipynb`](notebooks/01_extraction_anonymisation.ipynb)
- [ ] Jour 2 — EDA ciblée + baselines
- [ ] Jour 3 — Modèles retenus + validation croisée temporelle + SHAP
- [ ] Jour 4 — Interprétabilité + synthèse métier
- [ ] Jour 5 — Dashboard Streamlit + déploiement
- [ ] Jour 6 (bonus) — Segmentation K-Means + vérification confidentialité contractuelle + pseudonymisation localités/communes (D5) + packaging final

## Données produites (Jour 1)

Trois tables pivot complémentaires (décision de cadrage documentée dans `reports/cadrage_jour1.md`, section 4) :

| Fichier | Grain | Lignes | Modèle(s) alimenté(s) |
|---|---|---:|---|
| `data/processed/table_pivot_anonymisee.csv` | Localité × Tâche × Matériel | 997 | A |
| `data/processed/table_pivot_ressources_temporelle_anonymisee.csv` | Localité × Tâche × Date | 910 | A, C |
| `data/processed/table_avancement_departement_semaine_anonymisee.csv` | Département × Semaine | 100 | B, C |
| `data/processed/sheets_anonymises/*.csv` | (natif) | — | 29 feuilles sources anonymisées, référence |

## Structure du dépôt

```
p2ae-rollout-forecast/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                      # NON versionné
│   └── processed/                # données anonymisées/agrégées uniquement
├── notebooks/
│   └── 01_extraction_anonymisation.ipynb
├── src/
│   ├── anonymize.py              # anonymisation réutilisable
│   └── features.py               # construction des tables pivot
├── scripts/
│   └── build_notebook_01.py      # génère le notebook 01 à partir de cellules versionnées
├── models/
├── app/
└── reports/
    ├── cadrage_jour1.md
    └── audit_feuilles_localites.md
```

## Limites méthodologiques assumées

- 55 localités, 20 semaines d'historique : échantillon volontairement restreint. L'objectif n'est pas une précision de niveau production, mais une méthodologie rigoureuse (baseline, validation temporelle, métriques métier, interprétabilité) appliquée à un cas réel.
- La trajectoire théorique de référence (table `avancement_departement_semaine`) est ancrée sur la date administrative de démarrage du marché, antérieure de plusieurs mois au début du suivi terrain — voir `reports/cadrage_jour1.md` (décision D4) pour le détail et la correction prévue au Jour 3.
- **Noms de localités/communes conservés en clair dans les données de travail** (`data/processed/`), décision assumée le 27/08/2026 (D5) : ce ne sont pas des données personnelles, mais leur croisement avec des données de performance nécessite une vérification de confidentialité contractuelle avant toute publication — action reportée au Jour 6, voir checklist ci-dessous.
