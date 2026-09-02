# Cadrage écrit — Jour 1
## Modélisation prédictive P2AE (SBEE Bénin) — `p2ae-rollout-forecast`

**Date d'exécution :** 27 août 2026
**Objectif du jour (feuille de route, section 6 du plan) :** cadrage écrit + audit des 29 feuilles + extraction et anonymisation immédiate + construction de la table pivot (section 4).
**Livrables produits :** ce document, `reports/audit_feuilles_localites.md`, `data/processed/table_pivot_anonymisee.csv` (+ deux tables complémentaires, voir décision D2), `notebooks/01_extraction_anonymisation.ipynb`.

---

## 1. Reformulation de l'objectif du jour

Avant d'écrire une ligne de code, trois questions cadrent le travail :

1. **Que contient réellement `Localités.xlsx` ?** Le plan annonçait 10 feuilles utiles sur 29 ; il fallait vérifier si les 19 autres apportaient une information exploitable ou constituaient du bruit applicatif (paramétrage de l'app ElecTrack Pro, tables de filtre UI, etc.).
2. **Où se trouve exactement la donnée personnelle ?** Le plan pointait des emails d'agents et des coordonnées GPS ; il fallait les localiser précisément, feuille par feuille, avant tout export.
3. **Quel grain donner à la table pivot ?** Le plan visait un grain unique Localité × Tâche × Date. Il fallait vérifier si les données sources le permettent réellement.

## 2. Ce que l'audit a confirmé par rapport au plan

- Les volumétries annoncées sont exactes : 55 localités (Atacora 14, Borgou 16, Alibori 11, Donga 14), 997 lignes utiles dans `Helper_Calcul`, ~636 interventions, ~1 580 lignes de détail, 100 points hebdomadaires d'avancement (20 semaines × 5 niveaux géo, S16 à S35-2026).
- Le déséquilibre de classe annoncé pour la cible « retard » est confirmé et même précisé : **52 localités « En Cours », 2 « Terminé », 1 seule « Non Démarré »** sur 55 — un déséquilibre encore plus marqué qu'anticipé, qui renforce la nécessité déjà actée dans le plan (F1/Recall/matrice de confusion, jamais l'accuracy seule).
- `Helper_Calcul` est bien, comme annoncé, une table quasiment prête à l'emploi — elle a servi de **socle direct** à la table pivot A.

## 3. Ce que l'audit a révélé et que le plan ne mentionnait pas

1. **19 feuilles supplémentaires, non documentées dans le plan initial**, correspondant au paramétrage interne de l'application ElecTrack Pro (`Projets_Config`, `Geo_Config`, `Categories_Taches`, `Type_Travaux`, `Referentiels_Snapshot`, `Filtre_Rapport`, `Filtre_Performance`, `Roles`, `Utilisateurs_Projets`, `Photos_Chantier`, tables `Recap_*` supplémentaires). La plupart sont hors périmètre du pipeline prédictif ; deux (`Catalogue_Materiel`, `Anomalies_Taches`) se sont révélées utiles et ont été intégrées à la table pivot.
2. **Incohérence d'échelle entre deux feuilles portant le même type d'information** : `Top_Localites` exprime l'avancement en fraction (0–1) alors que `Historique_Avnt_Geo` l'exprime en pourcentage (0–100), bien que les deux colonnes s'appellent `Avancement_HTA_%`. C'est exactement le type de piège silencieux que le guide Régression/Classification/Clustering déjà en votre possession met en garde (données de qualité variable, saisie hétérogène). **Décision : standardisation en pourcentage (0–100) partout**, `Top_Localites` étant reconverti (× 100) dans la table pivot.
3. **Deux modes de saisie terrain coexistent** dans `Details_Intervention` (`➕ Saisie du jour` vs `🎯 Cumul total à date`), avec une colonne `Quantite_Nette_Calculee` déjà calculée pour absorber cette différence. Utilisée telle quelle plutôt que de recalculer un delta manuellement — recalculer à la main aurait recréé exactement le type de bug de mise à l'échelle déjà rencontré sur le `RobustScaler` du projet précédent.
4. **Un cinquième « département »** apparaît dans `Historique_Avnt_Geo` : la valeur `Toutes` (agrégat national des 4 départements). Elle est conservée dans la table pivot C mais sa trajectoire théorique n'est pas calculable (pas de date de fin contractuelle unique associée) — les colonnes correspondantes y sont donc `NaN`, intentionnellement.
5. **Emails et téléphones sont concentrés sur 7 personnes seulement**, réutilisées de façon identique dans 6 feuilles (`Utilisateurs`, `Roles`, `Utilisateurs_Projets`, `Filtre_Performance`, `Interventions`, `Journal_Chantier`) — un seul mapping `email → agent_id` suffit donc pour anonymiser l'ensemble du classeur de façon cohérente.

## 4. Décisions de cadrage assumées

**D1 — Portée de l'audit.** Seules les feuilles réellement mobilisées par le pipeline prédictif (10 sur 29, listées dans le rapport d'audit) sont analysées en profondeur. Les 19 autres sont recensées (nom, volumétrie, présence de PII) mais non exploitées ce jour — elles relèvent du paramétrage applicatif d'ElecTrack Pro, hors sujet du modèle.

**D2 — Trois tables pivot plutôt qu'une seule.** La spécification initiale (grain unique Localité × Tâche × Date) s'est heurtée à une réalité des données : deux grains natifs distincts coexistent (Localité × Tâche × Matériel dans `Objectifs`/`Helper_Calcul` ; Département × Semaine dans `Historique_Avnt_Geo`), et les fusionner de force aurait introduit une fausse précision (dupliquer un avancement départemental hebdomadaire sur chaque tâche de chaque localité du département, sans que la donnée le justifie). Trois tables complémentaires et documentées sont donc produites plutôt qu'une table unique masquant cette hétérogénéité — cohérent avec le principe déjà énoncé dans le plan lui-même : *« un point à énoncer clairement dans le README plutôt qu'à masquer »*.

- `table_pivot_anonymisee.csv` — grain **Localité × Tâche × Matériel** (997 lignes), la table de référence pour le Modèle A (ressources).
- `table_pivot_ressources_temporelle_anonymisee.csv` — grain **Localité × Tâche × Date** (910 lignes), reconstruite depuis le journal d'interventions ; prépare le terrain temporel pour les Modèles A (évolution) et C (risque).
- `table_avancement_departement_semaine_anonymisee.csv` — grain **Département × Semaine** (100 lignes), avec trajectoire théorique linéaire et écart à la référence contractuelle ; prépare les Modèles B et C.

**D3 — Anonymisation par remplacement, pas par masquage partiel.** Les emails sont remplacés par un identifiant stable `agent_NN` (traçabilité analytique conservée : un même agent porte le même identifiant dans toutes les feuilles) plutôt que supprimés, car le rôle et la zone d'affectation restent des signaux potentiellement utiles (ex. charge de travail par superviseur). Les coordonnées GPS précises et les numéros de téléphone sont en revanche **supprimés purement**, sans conversion (le plan autorisait l'arrondi ou la suppression ; la suppression a été retenue car le département/commune, déjà présent par ailleurs, suffit à toute analyse envisagée).

**D4 — Limite méthodologique assumée sur la trajectoire théorique (table C).** La trajectoire de référence est calculée entre la date de démarrage administratif du marché (18/11/2024, remise de site) et la date de fin contractuelle du Gantt par département. Le suivi ElecTrack Pro, lui, ne commence qu'en avril 2026 (S16-2026). Il en résulte un écart mécaniquement très négatif en début de série observée (jusqu'à -56 points), qui **ne signifie pas que le chantier a 56 points de retard réel** : il reflète le fait que la trajectoire linéaire inclut la période d'activités préliminaires (assurances, études d'exécution, approvisionnement matériel) durant laquelle l'avancement physique visible est nul par construction. Cette limite est documentée explicitement plutôt que corrigée aujourd'hui ; son traitement (ancrer la trajectoire sur le début réel des travaux physiques par département, ex. date de piquetage/fouille) est reporté à la construction du Modèle C (Jour 3), pour rester dans le temps imparti au Jour 1.

**D5 — Anonymisation différée des noms de localités/communes (ajoutée après le Jour 1, avant le Jour 2).** Question soulevée à juste titre : les noms de localités, communes et départements ne sont pas des données personnelles (PII) au sens du Jour 1 — ce sont des divisions administratives publiques du Bénin — mais leur croisement avec des données de performance (avancement, retard, anomalies) nommément attribuées à une localité constitue un risque de **confidentialité contractuelle/institutionnelle** distinct, sur un marché financé par un bailleur international. Ce risque était déjà anticipé sans être tranché à la section 2.2.3 du plan initial (*« vérifier qu'il n'existe pas de clause de confidentialité contractuelle sur les données du LRA/P2AE avant publication »*) — vérification qui reste à la charge du porteur du projet, hors du périmètre de ce que l'assistant peut trancher.

**Décision retenue :** deux niveaux de données, sur le même principe que l'anonymisation PII du Jour 1.
- **Données de travail (privées, `data/processed/`)** : noms réels de localités/communes conservés — nécessaires à la valeur opérationnelle de l'analyse pour ElecTrack Pro, ne quittent jamais la machine locale.
- **Données publiques (portfolio, dépôt GitHub, démo Streamlit, Jour 5-6)** : les localités et communes devront être pseudonymisées (`Localite_A`, `Localite_B`…) avant toute publication ; les départements (Atacora, Borgou, Alibori, Donga) resteront probablement en clair, s'agissant d'une information publique déjà associée au P2AE. **Action ajoutée à la checklist de clôture (Jour 6)** : vérifier la clause contractuelle avant publication, et implémenter la pseudonymisation localité/commune si nécessaire (fonction à ajouter à `src/anonymize.py`, sur le même principe que le mapping `email → agent_id`).

## 5. Ce qui est repoussé à demain (Jour 2)

- L'EDA ciblée (distributions, corrélations, cohérence prévu/réalisé) sur les trois tables produites aujourd'hui.
- Les trois baselines (régression linéaire, tendance simple, régression logistique).
- L'affinement de la cible « retard » (au-delà de la trajectoire théorique posée aujourd'hui).

## 6. Rappel — confidentialité

Conformément à la section 2.2 du plan : le fichier source `data/raw/Localites_raw.xlsx` reste local et n'est jamais committé (`.gitignore` mis à jour). Seules les données anonymisées de `data/processed/` sont destinées à un dépôt public.
