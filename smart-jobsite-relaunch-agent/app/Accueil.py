"""
app/Accueil.py — Page d'accueil de l'app Streamlit (Jour 5).

Point d'entrée du déploiement Streamlit Community Cloud : "Main file path"
= app/Accueil.py. Les deux autres pages (app/pages/) sont détectées
automatiquement par Streamlit (convention de dossier "pages/").
"""

import sys
from pathlib import Path

# L'app est lancée depuis app/, mais importe le package agent/ à la racine
# du repo — on ajoute la racine au sys.path avant tout import local. Répété
# à l'identique dans chaque page (app/pages/*.py), car Streamlit exécute
# chaque page comme un script indépendant.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Agent de relance de chantier",
    page_icon="🏗️",
    layout="wide",
)

st.title("Agent IA de relance de chantier")
st.caption(
    "Démo portfolio — architecture hybride n8n + LangGraph, dérivée d'un projet réel "
    "d'électrification (données et identifiants fictifs)."
)

st.markdown(
    """
### Le cas d'usage

Un chef de chantier envoie chaque semaine un rapport listant les localités sans
activité depuis plus de 3 mois. Pour chacune, l'agent :

1. extrait et identifie la localité (résolution de nom tolérante aux fautes de frappe) ;
2. compare l'inactivité déclarée à l'inactivité mesurée dans le système de suivi terrain, et signale tout écart suspect ;
3. calcule la cadence d'exécution nécessaire pour tenir les échéances de planning restantes ;
4. classe la localité (normal / retard / critique) en tenant compte de sa tendance sur les semaines précédentes ;
5. génère la section de rapport correspondante.

L'objectif : transformer un rapport texte hebdomadaire en alertes priorisées et actionnables,
sans réintervention manuelle sur les cas déjà normaux.
"""
)

st.markdown("### Le pipeline")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**n8n**")
    st.markdown(
        "Déclenchement hebdomadaire (Schedule Trigger), lecture du rapport, "
        "écriture du résultat final. Voir `n8n/workflow.json` et le GIF de démo."
    )
with col2:
    st.markdown("**API FastAPI**")
    st.markdown(
        "Expose l'agent en HTTP (`/traiter-rapport-hebdomadaire`, `/analyser-localite`, "
        "`/historique/{id}`). Appelée par n8n ; voir `api/main.py`."
    )
with col3:
    st.markdown("**Agent LangGraph**")
    st.markdown(
        "9 nœuds, état persisté par localité (`checkpoints.sqlite`), historique de "
        "cadence alimenté semaine après semaine. Voir `agent/graph.py`."
    )

st.info(
    "Cette page Streamlit appelle l'agent **directement en Python**, pas via l'API "
    "FastAPI ci-dessus — Streamlit Community Cloud héberge l'app dans son propre "
    "processus et ne peut pas atteindre une API tournant séparément sur une autre "
    "machine. L'API reste un composant réel et testé indépendamment : elle est "
    "démontrée via le workflow n8n (Jour 4) et via `docker-compose.yml`, qui la fait "
    "tourner comme un vrai service HTTP aux côtés de n8n. Les deux chemins "
    "(app et API) appellent exactement la même logique, `agent/orchestration.py`.",
    icon="ℹ️",
)

st.markdown(
    """
### Dans cette démo

- **Simulateur de relance** — choisissez une localité et une semaine, voyez le rapport généré et le détail du calcul.
- **Historique de cadence** — visualisez l'évolution du reste à faire semaine après semaine, pour une localité déjà simulée sur plusieurs semaines.

*Les identifiants de localité, communes et échéances de planning sont fictifs — seuls le pays, les
départements et les quantités de travaux agrégées sont réels (voir le README du dépôt pour le détail
de l'arbitrage de confidentialité).*
"""
)
