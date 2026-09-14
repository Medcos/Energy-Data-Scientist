# ⚡ Energy Data Scientist — Portfolio

[🇬🇧 English version](README.md)

**Medico Diomande** — Ingénieur électromécanicien (10+ ans sur des projets d'électrification financés par la Banque Mondiale / l'AFD / la BAD) devenu Data Scientist & Architecte Technique. Positionné comme **Energy Data Scientist & Infrastructure Intelligence Specialist** : machine learning appliqué et automatisation, ancrés dans une véritable expérience terrain en ingénierie de réseaux électriques.

## Pourquoi ce portfolio

Dix ans à piloter des chantiers d'électrification ont montré ce qui casse réellement sur le terrain : connectivité peu fiable, rapports d'avancement qui ne collent pas à la réalité, réconciliation de matériaux qui doit survivre au renommage de données de référence. Chaque projet ci-dessous transforme l'un de ces problèmes opérationnels réels en système fonctionnel, documenté et — quand c'est possible — déployé publiquement.

Tous les projets s'inspirent de programmes réels d'électrification financés par des bailleurs internationaux en Afrique de l'Ouest (SBEE Bénin, 55 localités réparties sur 4 départements). La géographie et les quantités agrégées réelles sont conservées pour la crédibilité ; les noms de localités, coordonnées GPS et tout élément identifiant un client sont pseudonymisés ou synthétiques. La section **Confidentialité** de chaque projet précise exactement ce qui est réel et ce qui est anonymisé, et chaque livraison publique est vérifiée par un grep anti-fuite au préalable.

## Parcours 1 — Data Science & Predictive Analytics

Une progression de trois projets de complexité croissante, avec un même fil conducteur : des baselines avant toute complexité, une interprétabilité SHAP systématique, et des métriques métier plutôt que de simples scores ML.

| # | Projet | Ce qu'il fait | Résultat clé | Démo en ligne |
|---|---|---|---|---|
| 1 | [Maintenance Prédictive pour Machines Industrielles](./predictive-maintenance-electrical-grid) | Classification à deux niveaux : la machine va-t-elle tomber en panne, et lequel des 5 modes en est la cause racine | AUC-ROC 0,98 · F1 jusqu'à 1,00 sur la cause racine | [Ouvrir →](https://maintenance-predictive-medico.streamlit.app/) |
| 2 | [Prévision d'Avancement et d'Approvisionnement](./predictive-avancement-projet) | Suite de 3 modèles prévoyant les besoins en matériel, l'avancement et le risque de retard sur un chantier d'électrification rurale | 93 % de détection du risque de retard · erreur ~2-3× plus faible que sans modèle | [Ouvrir →](https://energy-data-scientist-mdz2vr9ozqxhey3t5nprkh.streamlit.app) |
| 3 | [Agent de Relance de Chantier](./smart-jobsite-relaunch-agent) | Agent LangGraph + n8n qui lit les rapports terrain hebdomadaires, résout les noms de localités et classe automatiquement les chantiers à l'arrêt | Agent à état avec graphe à 9 nœuds · historique persisté semaine après semaine | [Ouvrir →](https://energy-data-scientist-kbqch4dr9lgc3aypv3kmgx.streamlit.app/) |

## Parcours 2 — Ingénierie Plateforme

| Projet | Ce qu'il fait |
|---|---|
| [ElecTrack Pro](./electrack-pro) | SaaS multi-tenant (AppSheet + Google Sheets + Apps Script) de gestion d'interventions terrain pour infrastructures électriques — en production sur 55 localités / 4 départements |

## Compétences démontrées dans ce portfolio

- → **Feature engineering guidé par le métier** — lois physiques (ex. `power_kw = T × ω`) et connaissance du terrain transformées en features et en corrections de données qu'un profil purement data science ne saurait dériver
- → **Rigueur méthodologique ML** — les baselines sont conservées sauf preuve chiffrée qu'un modèle plus complexe apporte un gain (Gradient Boosting retenu dans seulement 1 cas sur 4 comparables dans le projet de prévision) ; interprétabilité SHAP sur chaque modèle
- → **Logique de production, pas de notebook isolé** — chaque projet Data Science livre un dashboard Streamlit déployé ou un agent orchestré fonctionnel, pas seulement un `.ipynb`
- → **Confidentialité des données dès la conception** — un protocole de pseudonymisation documenté (géographie agrégée réelle, identifiants synthétiques, modèles ré-entraînés sans encodeur qui fuit) appliqué systématiquement et vérifié par grep avant chaque commit public
- → **Livraison full-stack** — des plateformes SaaS no-code (AppSheet/Apps Script) aux pipelines ML Python, jusqu'aux agents LangGraph orchestrés avec n8n et FastAPI

## À propos de moi

Ingénieur électromécanicien avec plus de 10 ans d'expérience terrain sur des programmes d'électrification financés par des bailleurs internationaux (Banque Mondiale, AFD, Banque Africaine de Développement), titulaire d'une certification Data Science RNCP niveau 7 (CentraleSupélec / OpenClassrooms). Chaque projet de ce portfolio associe cette expérience terrain à un travail appliqué de ML/data science et d'automatisation — voir la section « Pourquoi mon expérience fait la différence » de chaque projet pour le détail.

Disponible pour des missions de conseil à distance en data science, ML et automatisation des infrastructures.

Medico Diomande · dmedcos@yahoo.fr · [linkedin.com/in/medico-diomande-data](https://linkedin.com/in/medico-diomande-data)
