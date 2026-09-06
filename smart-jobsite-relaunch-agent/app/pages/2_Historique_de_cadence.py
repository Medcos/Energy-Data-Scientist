"""
app/pages/2_Historique_de_cadence.py — Page "Historique de cadence" (Jour 5).

Visualise l'évolution du reste à faire semaine après semaine pour une
localité donnée — l'apport concret du Checkpointer (SqliteSaver, Jour 3) :
sans lui, chaque appel à l'agent serait sans mémoire des semaines
précédentes.
"""

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP_DIR.parent))
sys.path.insert(0, str(_APP_DIR))

import pandas as pd
import plotly.express as px
import streamlit as st

from agent_client import LOCALITES_GELEES_AVEC_HISTORIQUE, get_historique, lister_localites

st.set_page_config(page_title="Historique de cadence", page_icon="📈", layout="wide")

st.title("Historique de cadence")
st.caption(
    "Reste à faire (toutes tâches confondues) au fil des semaines déjà simulées ou "
    "analysées pour une localité — persistant grâce au Checkpointer, pas recalculé "
    "depuis zéro à chaque appel."
)

localites = lister_localites()
libelles = {f"{l['ID_Localite']} ({l['departement']})": l["ID_Localite"] for l in localites}
ids = list(libelles.values())
index_defaut = ids.index("Site_09") if "Site_09" in ids else 0

libelle_choisi = st.selectbox("Localité", options=list(libelles.keys()), index=index_defaut)
id_localite = libelles[libelle_choisi]

if id_localite not in LOCALITES_GELEES_AVEC_HISTORIQUE:
    st.caption(
        "Cette localité ne fait pas partie des 8 pré-chargées avec 4 semaines "
        "d'historique — analysez-la plusieurs fois sur la page Simulateur de relance "
        "(à des dates différentes) pour lui construire un historique."
    )

historique = get_historique(id_localite)

if not historique:
    st.info(f"Aucun historique pour {id_localite} pour l'instant.", icon="ℹ️")
else:
    lignes = [
        {"semaine": h.semaine, "reste_total": sum(h.reste_a_faire.values())}
        for h in historique
    ]
    df = pd.DataFrame(lignes)
    fig = px.line(
        df,
        x="semaine",
        y="reste_total",
        markers=True,
        title=f"{id_localite} — reste à faire total par semaine",
        labels={"semaine": "Semaine", "reste_total": "Reste à faire (toutes tâches)"},
    )
    st.plotly_chart(fig, width='stretch')

    with st.expander("Détail par tâche"):
        detail = pd.DataFrame({h.semaine: h.reste_a_faire for h in historique}).T
        detail.index.name = "semaine"
        st.dataframe(detail, width='stretch')
