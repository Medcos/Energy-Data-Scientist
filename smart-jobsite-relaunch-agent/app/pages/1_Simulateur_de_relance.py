"""
app/pages/1_Simulateur_de_relance.py — Page "Simulateur de relance" (Jour 5).

L'utilisateur choisit une localité existante + une semaine, sans coller de
texte d'email : chemin direct de l'agent (route_depart -> "localite_connue"
-> agent/orchestration.analyser_localite), le même que l'endpoint
POST /analyser-localite de l'API.
"""

import sys
from datetime import date
from pathlib import Path

# Deux ajouts nécessaires : la racine du repo (pour `import agent`) et
# app/ (pour `import agent_client`, qui n'est pas garanti d'être déjà sur
# sys.path pour une page exécutée depuis app/pages/ — cf. commentaire de
# app/Accueil.py).
_APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP_DIR.parent))
sys.path.insert(0, str(_APP_DIR))

import pandas as pd
import streamlit as st

from agent_client import LOCALITES_GELEES_AVEC_HISTORIQUE, analyser, lister_localites

st.set_page_config(page_title="Simulateur de relance", page_icon="🔁", layout="wide")

st.title("Simulateur de relance")
st.caption(
    "Choisissez une localité et une semaine : l'agent lit son état à cette date-là et "
    "génère la section de rapport correspondante — sans passer par l'extraction d'un email."
)

localites = lister_localites()
libelles = {f"{l['ID_Localite']} ({l['departement']})": l["ID_Localite"] for l in localites}

col_choix, col_date = st.columns([2, 1])
with col_choix:
    libelle_choisi = st.selectbox(
        "Localité",
        options=list(libelles.keys()),
        index=list(libelles.values()).index("Site_09") if "Site_09" in libelles.values() else 0,
        help=(
            "Les 8 localités marquées avec un historique pré-chargé (voir le bandeau "
            "ci-dessous) montrent tout de suite une vraie tendance sur 4 semaines. "
            "Les autres démarrent sans historique, qui se construit au fil de vos clics."
        ),
    )
with col_date:
    date_du_jour = st.date_input(
        "Semaine (date du lundi)",
        value=date(2026, 8, 31),
        help="Les 4 lundis 10/17/24/31 août 2026 correspondent aux semaines déjà simulées (voir Historique de cadence).",
    )

id_localite = libelles[libelle_choisi]
if id_localite in LOCALITES_GELEES_AVEC_HISTORIQUE:
    st.caption(f"📈 {id_localite} a déjà un historique de cadence pré-chargé (4 semaines, voir l'onglet Historique).")

if st.button("Analyser", type="primary"):
    with st.spinner("L'agent traite la localité..."):
        resultat = analyser(id_localite, date_du_jour)
    st.session_state["dernier_resultat"] = resultat
    st.session_state["derniere_localite"] = id_localite

resultat = st.session_state.get("dernier_resultat")
if resultat and st.session_state.get("derniere_localite") == id_localite:
    statut = resultat.get("statut_alerte", "a_verifier")
    libelle_statut = {
        "normal": ("Normal", "success"),
        "retard": ("Retard", "warning"),
        "critique": ("Critique", "error"),
        "a_verifier": ("À vérifier", "warning"),
    }[statut]
    getattr(st, libelle_statut[1])(f"Statut : **{libelle_statut[0]}**")

    for e in resultat.get("erreurs", []):
        st.warning(e)

    st.markdown("#### Rapport généré")
    st.markdown(resultat.get("section_rapport") or "*(aucune section générée — voir les anomalies ci-dessus)*")

    with st.expander("Trace de raisonnement de l'agent"):
        st.markdown("**Reste à faire, par tâche :**")
        reste = resultat.get("reste_a_faire", {})
        if reste:
            deadlines = resultat.get("deadlines_planning", {})
            semaines = resultat.get("semaines_restantes", {})
            cadence = resultat.get("cadence_recommandee", {})
            df = pd.DataFrame(
                {
                    "Reste à faire": reste,
                    "Échéance": {k: v for k, v in deadlines.items()},
                    "Semaines restantes": semaines,
                    "Cadence recommandée / semaine": cadence,
                }
            )
            st.dataframe(df, width='stretch')
        else:
            st.markdown("*(aucune donnée — localité inconnue du référentiel ?)*")

        st.markdown(
            f"**Dernière activité mesurée (Electrack Pro) :** "
            f"{resultat.get('derniere_activite_mesuree') or '*(aucune)*'}"
        )
        st.markdown(f"**Nombre d'entrées d'historique de cadence pour cette localité :** {len(resultat.get('historique_cadence', []))}")
