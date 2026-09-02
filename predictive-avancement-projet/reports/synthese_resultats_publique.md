# Synthèse des résultats — Portfolio public

**Projet :** Modélisation prédictive de l'avancement et de l'approvisionnement sur un chantier d'électrification rurale (SBEE Bénin, financement international) · **Base :** 55 localités, 4 départements, 20 semaines de suivi.

> 🔒 **Note de confidentialité.** Ce document est la version publique du rapport de synthèse. Les noms de localités et de communes ont été pseudonymisés (`Localite_001`…`Localite_055`, `Commune_A`…`Commune_I`) — seuls les départements, information administrative publique, restent en clair. Voir `reports/cadrage_jour1.md` (décision D5) pour le détail de cette politique. La version interne (noms réels) reste un usage strictement privé, non publié.

---

## En une phrase

Sur 55 localités, **15 accusent un retard net par rapport aux autres localités de leur propre département** ; le modèle en détecte 14 sur 15 automatiquement. Le chantier avance normalement dans 3 départements sur 4, mais l'un des quatre a dépassé sa date de fin contractuelle en n'étant qu'à environ un quart d'avancement.

---

## 1. Où en est le chantier, département par département

| Département | Avancement moyen | Lecture |
|---|---:|---|
| Département le plus avancé | 68 % | Largement dans les temps |
| Département intermédiaire (1) | 54 % | Rythme correct |
| Département intermédiaire (2) | 40 % | En retrait, à surveiller |
| **Département le moins avancé** | 24 % | **Situation la plus préoccupante** |

Le département le moins avancé cumule deux signaux indépendants des modèles :
1. Sa date de fin contractuelle est déjà dépassée à la date d'observation, pour un avancement de seulement un quart.
2. Le chantier y est resté totalement à l'arrêt pendant **9 semaines consécutives**, avant de reprendre — un plateau de stagnation invisible sur une mesure ponctuelle, révélé uniquement par un suivi semaine par semaine.

## 2. Où en sont les travaux, tâche par tâche

Les tâches suivent un ordre d'avancement cohérent avec la logique de chantier — un bon signal de fiabilité des données :

- **Les plus avancées** : fouille basse tension (82 %), pose de poteaux basse tension (77 %) — les toutes premières étapes.
- **Les moins avancées** : éclairage public (11 %), mise à la terre (11 %), transformateurs (14 %) — les tâches de finition.

Au global, **44 % des lignes de travaux n'ont pas encore démarré et 27 % sont totalement terminées**.

## 3. Modèle de régression — combien de matériel reste-t-il à livrer ?

Deux modèles distincts ont été nécessaires (les quantités comptées et les mètres de câble ne se comparent pas sur la même échelle) :

| | Erreur moyenne du modèle | Erreur d'une estimation naïve |
|---|---:|---:|
| **Matériel compté** | **7 unités** | 20 unités |
| **Câble** | **1 376 mètres** | 2 637 mètres |

Ce qui explique le mieux la quantité restante : sans surprise, la quantité initialement prévue, mais à quantité égale, une tâche de finition pèse nettement plus qu'une tâche de début de chantier.

## 4. Modèle de série temporelle — où en sera-t-on dans 2 ou 4 semaines ?

| Horizon | Erreur moyenne de projection | Ne rien changer (référence) |
|---|---:|---:|
| Dans 2 semaines | 4,1 points de % | 4,5 points de % |
| Dans 4 semaines | **4,3 points de %** | 7,3 points de % |

À 4 semaines, projeter la tendance récente est presque deux fois plus précis que de supposer qu'aucun progrès ne sera fait.

## 5. Modèle de classification — quelles localités surveiller en priorité ?

**Définition retenue :** une localité est signalée si son avancement est nettement inférieur à celui des autres localités de son propre département (quartile inférieur) — la comparaison la plus juste entre départements ayant démarré à des dates et dans des conditions différentes.

**15 localités sur 55 (27 %)** répondent à ce critère. Le modèle en détecte **14 sur 15**, au prix d'environ 18 fausses alertes sur les 55 localités — un compromis assumé : pour un signal d'alerte terrain, mieux vaut sur-signaler que manquer un vrai cas.

**Cas le plus net :** `Localite_048` — la seule localité où aucun matériel n'a encore été posé (0 % d'avancement). Le modèle lui attribue une probabilité de risque de 90 %, entièrement justifiée par cette seule variable : aucune tâche démarrée.

**Résultat contre-intuitif, vérifié à deux reprises (EDA puis modèle) :** avoir eu un signalement d'anomalie terrain (matériel livré hors plan) est associé à un risque *plus faible*, pas plus élevé — ces anomalies ne sont détectées que sur des localités déjà suffisamment avancées pour être inspectées en détail.

## 6. Segmentation non supervisée (bonus)

Une segmentation par K-Means (K=4, choisi par méthode du coude et indice de silhouette) fait apparaître 4 profils de localités, sans aucune étiquette préexistante :

| Profil | Effectif | Caractéristique |
|---|---:|---|
| En difficulté généralisée | 29 | HTA et BT tous deux en retard — priorité d'intervention |
| Bien avancées sur les deux volets | 15 | Proches de la réception |
| BT quasi-terminé / peu de HTA | 5 | Périmètre HTA absent ou non démarré |
| Avancement médian, avec anomalie terrain | 6 | Déjà partiellement inspectées |

**Validation croisée notable :** le groupe « anomalie terrain » identifié par le clustering correspond exactement, sans un seul écart, aux localités où une anomalie avait été détectée par un comptage direct des données — deux méthodes indépendantes convergent vers le même résultat.

## 7. Fiabilité des données

Deux anomalies de saisie ont été détectées et corrigées avant modélisation : une jointure qui propageait un signalement d'anomalie à tort sur tout le matériel d'une tâche, et une saisie de correction terrain aberrante qui faisait passer un cumul de travaux réalisés en négatif — impossible physiquement. Aucune des deux ne remet en cause les tendances présentées ci-dessus.

## 8. Limites assumées

- Échantillon restreint (55 localités, 20 semaines) : méthodologie démontrée, pas précision de niveau production.
- « À risque » signifie retard relatif par rapport aux pairs du même département, pas retard contractuel absolu.
- Un modèle plus complexe (Gradient Boosting) n'a été retenu que dans 1 cas sur 4 testés — dans les 3 autres, un modèle plus simple a fait aussi bien ou mieux, et a été conservé par choix.

---

## Stack technique

Python · pandas · scikit-learn (Ridge, Gradient Boosting, régression logistique, K-Means) · SHAP · Streamlit · matplotlib.

## À propos

Ce projet est le second volet d'un portfolio de data science appliquée à l'énergie et aux infrastructures, après un projet de maintenance prédictive (classification, F1 = 0,88, SHAP, dashboard Streamlit). Il illustre la transformation d'un système de suivi de chantier réel en outil de pilotage prédictif, avec la rigueur méthodologique et les précautions de confidentialité qu'impose un contexte de développement international.
