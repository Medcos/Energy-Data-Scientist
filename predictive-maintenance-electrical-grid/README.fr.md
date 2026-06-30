⚡ Maintenance Prédictive pour Machines Industrielles

[🇬🇧 English version](README.md)

`Python 3.11+` `scikit-learn 1.6` `XGBoost 2.0` `Application Streamlit`

## Aperçu

Système de machine learning à deux niveaux pour prédire les pannes de machines industrielles (température, vitesse de rotation, couple, usure outil) et identifier la cause racine parmi 5 modes de panne. Le Niveau 1 (classification binaire) atteint un **AUC-ROC de 0,98** et un **F1 = 0,88** pour la détection de panne. Le Niveau 2 (classification multi-label) identifie le mode de panne spécifique (Surchauffe, Puissance, Surcontrainte, Usure outil, Aléatoire) avec un **F1 allant jusqu'à 1,00** selon le mode.

Développé par Medico Diomande — Ingénieur Électromécanicien (10 ans d'expérience terrain sur des projets d'électrification financés par la Banque Mondiale / AFD / BAD) + Data Scientist. Cette expertise métier nourrit directement le feature engineering (puissance, stress thermique dérivés de lois physiques).

## Impact métier

- → Système de décision en deux étapes : « La machine va-t-elle tomber en panne ? » puis « Pourquoi ? » pour une action de maintenance ciblée
- → Feature engineering ancré dans la physique, validé par analyse SHAP (power_kw explique à lui seul 100% du signal de panne de puissance)
- → Seuils de décision optimisés par mode de panne plutôt qu'un seuil générique à 0,5, améliorant le F1 jusqu'à +15%
- → Dashboard Streamlit interactif pour les parties prenantes non techniques — démo live, sans notebook requis

## Fonctionnalités clés

- → Feature engineering métier (`temp_diff`, `power_kw = T × ω`, `thermal_stress`)
- → Comparaison SMOTE vs pondération de classe — la pondération de classe a été retenue après tests empiriques (SMOTE dégradait la precision des modèles à base d'arbres)
- → 3 modèles comparés par niveau : Régression Logistique, Random Forest, Gradient Boosting
- → Optimisation du seuil de décision par label (courbe Precision-Recall, maximisation du F1)
- → Interprétabilité SHAP pour les deux niveaux, validant la cohérence physique des mécanismes appris
- → Dashboard Streamlit en ligne : [URL Streamlit Cloud]

## Résultats — Niveau 1 (Prédiction de panne)

| Modèle | Precision | Recall | F1 | AUC-ROC |
|---|---|---|---|---|
| Régression Logistique | 0,18 | 0,85 | 0,30 | 0,93 |
| Random Forest | 0,94 | 0,66 | 0,78 | 0,97 |
| **Gradient Boosting ★** | **0,93** | **0,82** | **0,88** | **0,98** |

## Résultats — Niveau 2 (Identification du mode de panne)

| Mode | Cause | F1-score | Seuil |
|---|---|---|---|
| HDF | Surchauffe / dissipation thermique | 0,98 | 0,785 |
| PWF | Puissance anormale | 1,00 | 0,9998 |
| OSF | Surcontrainte mécanique | 0,94 | 0,206 |
| TWF | Usure de l'outil | règle heuristique | basé usure |
| RNF | Panne aléatoire | non prédictible | — |

## Utilisation

```
git clone https://github.com/Medcos/Energy-Data-Scientist/tree/main/predictive-maintenance-electrical-grid
pip install -r requirements.txt
streamlit run app.py
```

## Pourquoi mon expérience fait la différence

La feature `power_kw` n'existait pas dans le dataset original. Elle a été dérivée d'une connaissance d'ingénierie électromécanique : la puissance mécanique calculée à partir du couple et de la vitesse de rotation (P = T × ω), une relation fondamentale en diagnostic de machines tournantes. L'analyse SHAP a confirmé que cette seule feature capture 100% du signal de panne de puissance — ce type de feature engineering guidé par le métier surpasse généralement les approches purement data-driven sur des jeux de données industriels.

De même, `temp_diff` (différentiel de température process/ambiant) s'est révélé être le 3ème prédicteur global le plus important, reflétant directement l'efficacité de dissipation thermique — un concept familier issu de l'exploitation de réseaux électriques HTA/BTA.

---

Auteur : Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Disponible pour missions à distance