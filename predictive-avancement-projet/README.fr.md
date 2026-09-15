# ⚡ Prévision d'Avancement et d'Approvisionnement

[🇬🇧 English version](README.md)

`Python` `pandas` `scikit-learn` `SHAP` `Streamlit`

📂 **Data Science & Predictive Analytics** — Projet 2/3 · [Accueil du portfolio](../README.fr.md) · [← Maintenance Prédictive](../predictive-maintenance-electrical-grid) · Suivant : [Agent de Relance de Chantier →](../smart-jobsite-relaunch-agent)

## Présentation

Modélisation prédictive de l'avancement et de l'approvisionnement sur un chantier d'électrification rurale (SBEE Bénin, Afrique de l'Ouest, financement international) — 55 localités, 4 départements, échéance décembre 2026.

Deuxième volet du parcours Data Science & Predictive Analytics, après [Maintenance Prédictive pour Machines Industrielles](../predictive-maintenance-electrical-grid). Ce projet transforme un système de suivi de chantier réel en outil de pilotage prédictif, avec trois modèles légers partageant un même pipeline de données, plus une segmentation bonus :

- **A. Ressources** — quantité de matériel restant à livrer par localité × tâche (régression)
- **B. Avancement** — projection de l'avancement à S+2 / S+4 par département (série temporelle)
- **C. Risque de retard** — localités en retard relatif par rapport à leurs pairs (classification)
- **D. Segmentation** — 4 profils de localités, sans étiquette préexistante (clustering, bonus)

Développé par Medico Diomande — Ingénieur électromécanicien (10 ans d'expérience terrain sur des projets d'électrification financés par la Banque Mondiale / AFD / BAD) + Data Scientist. Dix ans à cadrer et suivre des chantiers d'électrification ont directement orienté le choix des cibles à modéliser et permis de distinguer les anomalies de saisie du vrai signal dans les données.

## Impact métier

- → 7 unités / 1 376 mètres d'erreur moyenne sur la prévision de matériel (Modèle A) contre 20 unités / 2 637 m sans modèle — réduit le sur-approvisionnement et les ruptures de dernière minute
- → 4,3 points de % d'erreur à 4 semaines sur la projection d'avancement (Modèle B) contre 7,3 en ne changeant rien — donne aux planificateurs un horizon d'alerte précoce fiable
- → 93 % des localités à risque correctement signalées (Modèle C, 15/55 localités) — transforme un suivi réactif en suivi proactif
- → Un clustering non supervisé (Modèle D) isole un groupe de localités qui coïncide **exactement** avec un groupe identifié par une méthode totalement indépendante — un signal de validation croisée qui ne devait rien au hasard

Détail complet dans [`reports/synthese_resultats_publique.md`](reports/synthese_resultats_publique.md) (chiffres clés résumés ci-dessus).

## 🔒 Note de confidentialité

Ce dépôt contient des données **pseudonymisées** issues d'un projet réel financé par un bailleur international. Les noms de localités et de communes sont remplacés par des identifiants génériques (`Localite_001`…`Localite_055`, `Commune_A`…`Commune_I`) ; seuls les départements (division administrative publique du Bénin) restent en clair. Les modèles fournis (`models/public/`) ont été **ré-entraînés sur ces données pseudonymisées** — aucun encodeur catégoriel du dépôt ne contient de nom réel.

*(Les notebooks d'analyse détaillée avec données réelles restent un usage interne, non publié — voir la structure du dépôt ci-dessous.)*

## Démo

**🔗 Application en ligne : https://energy-data-scientist-mdz2vr9ozqxhey3t5nprkh.streamlit.app**

```bash
pip install -r requirements.txt
PUBLIC_MODE=1 streamlit run app/streamlit_app.py
```

Dashboard à 3 pages : Ressources, Avancement, Risques.

## Structure du dépôt

```
predictive-avancement-projet/
├── README.md                     # version anglaise (par défaut)
├── README.fr.md                  # ce fichier
├── requirements.txt
├── app/
│   └── streamlit_app.py          # dashboard 3 pages (mode public via PUBLIC_MODE=1)
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

## Pourquoi mon expérience fait la différence

La méthodologie en 6 étapes est une bonne pratique standard en data science. Ce qui l'est moins, c'est de savoir, après dix ans à piloter des chantiers d'électrification, quels chiffres d'un export de suivi de chantier relèvent du vrai signal et lesquels sont des artefacts de saisie — les deux anomalies détectées et corrigées pendant l'EDA viennent de cette expérience terrain, pas d'une règle générique de détection d'outliers. Cette même expérience a orienté la cible du Modèle C : l'étiquette d'origine était dégénérée (100 % positive), remplacée par une sous-performance relative par rapport au quartile du département — une métrique qui correspond à la façon dont un chef de mission juge réellement « quelles localités nécessitent une attention ».

---

Auteur : Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Disponible pour missions à distance
