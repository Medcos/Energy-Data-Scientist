# ⚡ Maintenance Prédictive pour Machines Industrielles

[🇬🇧 English version](README.md)

`Python 3.11+` `scikit-learn >=1.3,<1.6` `XGBoost 2.0+` `Application Streamlit`

📂 **Data Science & Predictive Analytics** — Projet 1/3 · [Accueil du portfolio](../README.fr.md) · Suivant : [Prévision d'avancement et d'approvisionnement →](../predictive-avancement-projet)

> **À propos des données — à lire d'abord.** Malgré le nom du dossier (`predictive-maintenance-electrical-grid`, conservé pour que les liens existants et la démo en ligne continuent de fonctionner), ce projet n'utilise **pas** de données de réseau électrique. Il utilise le jeu public **AI4I 2020 Predictive Maintenance Dataset** (S. Matzka, UCI Machine Learning Repository, licence CC BY 4.0, [DOI 10.24432/C5HS5C](https://doi.org/10.24432/C5HS5C)) : **10 000 relevés synthétiques de machines industrielles** (température de l'air et du procédé, vitesse de rotation, couple, usure d'outil), 339 pannes (3,4 %). La plupart des étiquettes de panne (287 sur 339) sont produites par des règles publiées : les résultats ci-dessous illustrent une méthode sur un jeu public de référence, pas une performance sur des équipements réels. Voir [Fiabilité et limites](#fiabilité-et-limites).

## Aperçu

Système de machine learning à deux niveaux pour prédire les pannes de machines industrielles (température, vitesse de rotation, couple, usure outil) et identifier la cause racine parmi 5 modes de panne. Le Niveau 1 (classification binaire) atteint un **AUC-ROC de 0,98** et un **F1 de 0,88 tel que publié dans les notebooks — 0,84 ± 0,03 quand le seuil de décision est choisi sans le jeu de test** (voir [Fiabilité et limites](#fiabilité-et-limites)). Le Niveau 2 (classification multi-label) identifie le mode de panne spécifique (Surchauffe, Puissance, Surcontrainte, Usure outil, Aléatoire) avec un F1 allant jusqu'à 1,00 selon le mode ; ce score maximal concerne la panne de puissance, que ce jeu définit par un seuil de puissance.

Développé par Medico Diomande — Ingénieur Électromécanicien (10 ans d'expérience terrain sur des projets d'électrification financés par la Banque Mondiale / AFD / BAD) + Data Scientist. Cette expertise métier nourrit le feature engineering (puissance, stress thermique dérivés de lois physiques).

## Impact métier

- → Système de décision en deux étapes : « La machine va-t-elle tomber en panne ? » puis « Pourquoi ? » pour une action de maintenance ciblée
- → Feature engineering ancré dans la physique, contrôlé par analyse SHAP (`power_kw` explique à lui seul l'étiquette de panne de puissance, que ce jeu définit par un seuil de puissance)
- → Seuils de décision réglés par mode de panne plutôt qu'un seuil générique à 0,5 (réglés sur le jeu de test : le gain est optimiste)
- → Dashboard Streamlit interactif pour les parties prenantes non techniques — démo live, sans notebook requis

## Fonctionnalités clés

- → Feature engineering métier (`temp_diff`, `power_kw = T × ω`, `thermal_stress`)
- → Comparaison SMOTE vs pondération de classe — la pondération de classe a été retenue après tests empiriques (SMOTE dégradait la precision des modèles à base d'arbres)
- → 3 modèles comparés par niveau : Régression Logistique, Random Forest, Gradient Boosting
- → Optimisation du seuil de décision par label sur la courbe Precision-Recall (maximisation du F1, sur le jeu de test)
- → Interprétabilité SHAP pour les deux niveaux, contrôlant la cohérence physique des mécanismes appris
- → Dashboard Streamlit en ligne : [maintenance-predictive-medico.streamlit.app](https://maintenance-predictive-medico.streamlit.app/)

## Résultats — Niveau 1 (Prédiction de panne), tels que publiés dans les notebooks

| Modèle | Precision | Recall | F1 | AUC-ROC |
|---|---|---|---|---|
| Régression Logistique | 0,18 | 0,85 | 0,30 | 0,93 |
| Random Forest | 0,94 | 0,66 | 0,78 | 0,97 |
| **Gradient Boosting ★** | **0,93** | **0,82** | **0,88** | **0,98** |

Ligne Gradient Boosting : seuil de décision 0,4236, réglé sur le jeu de test. Voir [Fiabilité et limites](#fiabilité-et-limites) pour une réexécution.

## Résultats — Niveau 2 (Identification du mode de panne), tels que publiés dans les notebooks

| Mode | Cause | F1-score | Seuil |
|---|---|---|---|
| HDF | Surchauffe / dissipation thermique | 0,98 | 0,785 |
| PWF | Puissance anormale | 1,00 | 0,9998 |
| OSF | Surcontrainte mécanique | 0,94 | 0,206 |
| TWF | Usure de l'outil | règle heuristique | basé usure |
| RNF | Panne aléatoire | non prédictible | — |

Les seuils sont réglés sur le jeu de test. Le score de 1,00 sur PWF est tautologique : l'étiquette PWF est définie par un seuil de puissance, et `power_kw` est cette puissance.

## Fiabilité et limites

Une réexécution des notebooks (octobre 2026, scikit-learn 1.9.1, découpage stratifié 80/20) reproduit la Régression Logistique et le Gradient Boosting, et donne ce qui suit.

| Question | Résultat |
|---|---|
| Une règle simple fait-elle aussi bien ? | Une règle physique à 3 conditions (sans apprentissage ; seuils publiés avec le jeu) atteint précision 1,00, rappel 0,84, F1 0,91 sur le jeu de test (F1 0,92 sur les 10 000 relevés), au-dessus du Gradient Boosting (0,87). Elle gagne par construction : 287 des 339 étiquettes de panne sont générées par ces règles. |
| Le F1 = 0,88 est-il fiable ? | Il repose sur un seuil de décision (0,4236) réglé sur le jeu de test. Reproduit : F1 0,87 (55 des 68 pannes du test, contre 56 publiées). Avec le seuil choisi dans l'entraînement, la validation croisée 5 plis × 3 donne un F1 de 0,84 ± 0,03 ; l'intervalle bootstrap à 95 % sur les 68 pannes du test va de 0,79 à 0,92. |
| Random Forest | La réexécution donne un rappel de 0,79 (publié : 0,66) ; la cause n'est pas identifiée. |
| Niveau 2 | Les seuils par mode sont aussi réglés sur le jeu de test. TWF et RNF ne sont pas prédits par le modèle. |
| Combien de pannes faut-il ? | Sur ce jeu : F1 0,67 avec 27 pannes d'entraînement, 0,76 avec 54, 0,81 avec 108, 0,87 avec 271. |
| Journal de maintenance incomplet | Si 20 % des pannes manquent aux étiquettes d'entraînement, le rappel passe de 0,81 à 0,67 ; à 40 %, à 0,43. |
| `thermal_stress` | N'apporte rien (importance par permutation négative). |

Ce projet démontre une méthode — référence simple, protocole de seuil propre, marge d'erreur — sur un jeu public de référence, pas un résultat validé sur des équipements réels. Les chiffres ci-dessus ne se transposent pas à d'autres actifs : ils se mesurent sur l'historique des équipements concernés.

`data/AEP_hourly.csv` (une série de charge horaire) n'est utilisé par aucun notebook ni par l'application.

## Utilisation

```
git clone https://github.com/Medcos/Energy-Data-Scientist.git
cd Energy-Data-Scientist/predictive-maintenance-electrical-grid
pip install -r requirements.txt
streamlit run maintenance_predictive/app.py
```

## Pourquoi mon expérience fait la différence

La feature `power_kw` n'existait pas dans le dataset original. Elle a été dérivée d'une connaissance d'ingénierie électromécanique : la puissance mécanique calculée à partir du couple et de la vitesse de rotation (P = T × ω), une relation fondamentale en diagnostic de machines tournantes. Sur ce jeu synthétique, elle capture entièrement l'étiquette de panne de puissance, car cette étiquette est définie par un seuil de puissance : un contrôle de la physique, pas une preuve de performance sur des équipements réels.

De même, `temp_diff` (différentiel de température process/ambiant) figure parmi les prédicteurs les plus importants de l'analyse SHAP publiée, reflétant l'efficacité de dissipation thermique — un concept familier issu de l'exploitation de réseaux électriques HTA/BTA.

---

Auteur : Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Disponible pour missions à distance
