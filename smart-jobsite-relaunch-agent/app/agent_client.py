"""
agent_client.py — Point d'accès partagé de l'app Streamlit à l'agent
LangGraph (Jour 5).

Choix d'architecture assumé (à signaler clairement, pas une évidence) :
l'app appelle le graphe LangGraph EN PROCESS (import direct de
agent/orchestration.py), PAS via l'API FastAPI en HTTP.

Raison : Streamlit Community Cloud héberge l'app dans son propre processus
Python isolé — il ne peut pas atteindre une API FastAPI qui tournerait
séparément sur localhost, ni nulle part ailleurs sans déployer et opérer un
second service public rien que pour cette démo (hors périmètre du plan
Jour 5, qui ne prévoit qu'un déploiement). L'API FastAPI (api/main.py)
reste un composant à part entière, démontrée indépendamment via le workflow
n8n (Jour 4) et via docker-compose (les deux services tournant ensemble en
local/Docker) — elle n'est pas dupliquée ici : cette page appelle la MÊME
logique (agent/orchestration.py, partagée par l'API et par l'app) via un
chemin d'appel différent.

Conséquence pratique : le graphe compilé ici (et son checkpoints.sqlite)
est un processus/état séparé de celui de l'API — un run fait depuis l'app
Streamlit et un run fait via l'API ne partagent PAS le même historique
persisté en mémoire de processus, même s'ils lisent/écrivent le même
fichier checkpoints.sqlite sur disque (chacun rouvre sa propre connexion
SQLite au démarrage de son propre processus).
"""

from datetime import date

import streamlit as st

from agent import data_access, orchestration
from agent.graph import compile_graph


@st.cache_resource(show_spinner=False)
def get_graph():
    return compile_graph()


def lister_localites() -> list[dict]:
    return data_access.lister_localites()


def analyser(id_localite: str, date_du_jour: date) -> dict:
    return orchestration.analyser_localite(get_graph(), id_localite, date_du_jour)


def get_historique(id_localite: str) -> list:
    config = {"configurable": {"thread_id": id_localite}}
    etat = get_graph().get_state(config).values
    return list(etat.get("historique_cadence", [])) if etat else []


LOCALITES_GELEES_AVEC_HISTORIQUE = [
    "Site_09", "Site_23", "Site_35", "Site_39", "Site_45",
    "Site_46", "Site_49", "Site_04",
]
