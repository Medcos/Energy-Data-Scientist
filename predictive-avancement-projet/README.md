# p2ae-rollout-forecast

Modélisation prédictive de l'avancement et de l'approvisionnement sur un chantier d'électrification rurale (SBEE Bénin, Afrique de l'Ouest, financement international) — 55 localités, 4 départements, échéance décembre 2026.

Deuxième volet d'un portfolio de data science appliquée à l'énergie et aux infrastructures, après un projet de maintenance prédictive (classification, F1 = 0,88, SHAP, dashboard Streamlit). Ce projet transforme un système de suivi de chantier réel en outil de pilotage prédictif, avec trois modèles légers partageant un même pipeline de données :

- **A. Ressources** — quantité de matériel restant à livrer par localité × tâche (régression)
- **B. Avancement** — projection de l'avancement à S+2 / S+4 par département (série temporelle)
- **C. Risque de retard** — localités en retard relatif par rapport à leurs pairs (classification)
- **D. Segmentation** — 4 profils de localités, sans étiquette préexistante (clustering, bonus)

**Résultats clés** — détail complet dans [`reports/synthese_resultats_publique.md`](reports/synthese_resultats_publique.md) :
- 7 unités / 1 376 mètres d'erreur moyenne (Modèle A) contre 20 unités / 2 637 m sans modèle
- 4,3 points de % d'erreur à 4 semaines (Modèle B) contre 7,3 en ne changeant rien
- 15 localités à risque relatif détectées à 93 % (Modèle C)
- Un groupe de localités isolé par le clustering (Modèle D) coïncide **exactement** avec un groupe identifié par une méthode totalement indépendante — une validation croisée qui ne devait rien au hasard

## 🔒 Note de confidentialité

Ce dépôt contient des données **pseudonymisées** issues d'un projet réel financé par un bailleur international. Les noms de localités et de communes sont remplacés par des identifiants génériques (`Localite_001`…`Localite_055`, `Commune_A`…`Commune_I`) ; seuls les départements (division administrative publique du Bénin) restent en clair. Les modèles fournis (`models/public/`) ont été **ré-entraînés sur ces données pseudonymisées** — aucun encodeur catégoriel du dépôt ne contient de nom réel. Le détail de cette politique de confidentialité (décision D5) est documenté dans [`reports/cadrage_jour1.md`](reports/cadrage_jour1.md).

*(Les notebooks d'analyse détaillée avec données réelles restent un usage interne, non publié — voir la section suivante.)*

## Démo

```bash
pip install -r requirements.txt
P2AE_PUBLIC_MODE=1 streamlit run app/streamlit_app.py
```

Dashboard à 3 pages : Ressources, Avancement, Risques. Lien de démo en ligne : *energy-data-scientist-mdz2vr9ozqxhey3t5nprkh*.

## Structure du dépôt

```
p2ae-rollout-forecast/
├── README.md
├── requirements.txt
├── app/
│   └── streamlit_app.py          # dashboard 3 pages (mode public via P2AE_PUBLIC_MODE=1)
├── src/
│   ├── anonymize.py              # anonymisation PII + pseudonymisation localités/communes
│   └── features.py               # construction des tables pivot
├── data/
│   └── public/                   # données pseudonymisées uniquement
├── models/
│   └── public/                   # modèles ré-entraînés sur données pseudonymisées
└── reports/
    ├── synthese_resultats_publique.md
    └── figures/
```

## Méthodologie

Approche en 6 étapes, détaillée dans `reports/synthese_resultats_publique.md` : cadrage et audit des données, EDA avec détection et correction de deux anomalies de saisie réelles, baselines simples avant modèles complexes (Ridge, tendance linéaire, régression logistique), comparaison chiffrée à un Gradient Boosting testé sur chaque volet (retenu dans 1 cas sur 4 seulement — la simplicité l'a emporté ailleurs, sur preuve et non par principe), interprétabilité SHAP systématique, et enfin dashboard + segmentation bonus.

**Limite assumée :** échantillon restreint (55 localités, 20 semaines de suivi). L'objectif est de démontrer une méthodologie rigoureuse — baseline, validation temporelle, métriques métier, interprétabilité — appliquée à un cas réel, pas d'atteindre une précision de niveau production.

## Stack technique

Python · pandas · scikit-learn (Ridge, Gradient Boosting, régression logistique, K-Means) · SHAP · Streamlit · matplotlib.
