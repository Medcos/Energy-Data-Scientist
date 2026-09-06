# Agent IA de relance de chantier — démo n8n + LangGraph

Démonstration portfolio d'un agent d'automatisation dérivé d'un projet réel de suivi de
chantiers d'électrification (données, noms de localités et échéances fictifs — voir
[Confidentialité](#confidentialité) ci-dessous).

> Note d'avancement : ce README couvre l'essentiel (architecture, exécution, déploiement).
> Un diagramme et une relecture finale sont prévus avant la publication (v1.0).

## Le cas d'usage

Un chef de chantier envoie chaque semaine un rapport listant les localités sans activité
depuis plus de 3 mois. L'agent, pour chacune :

1. extrait et identifie la localité (résolution de nom tolérante aux fautes de frappe, y compris en cas d'ambiguïté entre deux noms proches) ;
2. compare l'inactivité déclarée à l'inactivité mesurée dans le système de suivi terrain, et signale tout écart suspect ;
3. calcule la cadence d'exécution nécessaire pour tenir les échéances de planning restantes ;
4. classe la localité (normal / retard / critique) en tenant compte de sa tendance sur les semaines précédentes, grâce à un historique persisté d'une semaine à l'autre ;
5. génère la section de rapport correspondante.

## Architecture

```
n8n (déclenchement + I/O)  →  API FastAPI  →  Agent LangGraph (9 nœuds, état persisté)
        │                          │                      │
 Schedule Trigger            /traiter-rapport-       StateGraph, checkpointer
 lecture email simulé        hebdomadaire (fan-out    SQLite (thread_id =
 écriture du rapport         multi-localités),         identifiant de localité)
                              /analyser-localite,
                              /historique/{id}
```

- **`agent/`** — le graphe LangGraph : extraction, résolution de nom (fuzzy matching avec
  marge d'ambiguïté), lecture des données terrain, calcul de cadence, classification,
  historique persisté (`agent/checkpoints.sqlite`, versionné).
- **`api/`** — API FastAPI exposant l'agent en HTTP (voir `api/main.py` pour le détail des
  3 endpoints).
- **`app/`** — app Streamlit à 3 pages (Accueil, Simulateur de relance, Historique de
  cadence). Appelle l'agent directement en Python plutôt que via l'API — voir
  `app/agent_client.py` pour le pourquoi.
- **`n8n/`** — workflow n8n (`workflow.json`) qui orchestre le déclenchement hebdomadaire ;
  voir `n8n/README.md` pour les points d'attention (accès fichier, validation).
- **`data/`** — jeu de données synthétique (55 localités, 4 départements du Bénin, 11
  tâches de travaux HTA/BT).
- **`tests/`** — suite pytest (agent, API, app Streamlit).
- **`docker-compose.yml`** — lance l'API et n8n ensemble en local.

## Exécuter en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -q          # 36 tests

# API
uvicorn api.main:app --reload --port 8000

# App Streamlit (dans un autre terminal)
streamlit run app/Accueil.py

# Stack complète API + n8n (nécessite Docker — voir n8n/README.md pour le détail)
docker compose up --build
```

## Déploiement (Streamlit Community Cloud)

1. Pousser ce repo sur GitHub.
2. Sur [share.streamlit.io](https://share.streamlit.io), créer une nouvelle app pointant
   vers ce repo, avec **Main file path : `app/Accueil.py`**.
3. `requirements.txt` (racine) est détecté automatiquement.

L'app déployée fonctionne de façon autonome (elle appelle l'agent directement en Python,
pas via l'API — voir `app/agent_client.py`) : aucun autre service à déployer pour la démo
publique. L'API FastAPI et le workflow n8n restent démontrés indépendamment, en local
(`docker compose up`) ou via le GIF de démo (`n8n_demo.gif`).

## Confidentialité

**Réel** : le pays (Bénin), les 4 départements, et les quantités de travaux agrégées par
tâche.

**Fictif** : noms de communes et de localités, coordonnées GPS, calendrier exact des
interventions, échéances précises de planning, nom du projet/client d'origine.

Toute donnée générée est vérifiée par un grep anti-fuite avant chaque livraison.

## Statut

Jours 1 à 5 du plan de mise en place terminés (données, agent, checkpointer + tests,
intégration n8n, API + app Streamlit + déploiement). Restent : README complet +
diagramme (Jour 6), publication et carte portfolio (Jour 7).
