"""
Dashboard P2AE Rollout Forecast — ElecTrack Pro
3 pages : Ressources (Modèle A), Avancement (Modèle B), Risques (Modèle C).

Lancement local (données de travail réelles) :
    streamlit run app/streamlit_app.py

Lancement en mode public (données/modèles pseudonymisés, pour déploiement
Streamlit Cloud — voir décision D5, reports/cadrage_jour1.md) :
    P2AE_PUBLIC_MODE=1 streamlit run app/streamlit_app.py
Sur Streamlit Cloud : définir la variable d'environnement P2AE_PUBLIC_MODE=1
dans les paramètres avancés de l'app (Settings > Secrets ou Environment).
"""
import os
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# Configuration générale
# ----------------------------------------------------------------------------
st.set_page_config(page_title="P2AE Rollout Forecast", page_icon="⚡", layout="wide")

PUBLIC_MODE = os.environ.get("P2AE_PUBLIC_MODE", "0") == "1"

BASE_DIR = Path(__file__).resolve().parent.parent
if PUBLIC_MODE:
    DATA_DIR = BASE_DIR / "data" / "public"
    MODELS_DIR = BASE_DIR / "models" / "public"
    FICHIER_RESSOURCES = "table_pivot_publique.csv"
    FICHIER_AVANCEMENT = "table_avancement_publique.csv"
else:
    DATA_DIR = BASE_DIR / "data" / "processed"
    MODELS_DIR = BASE_DIR / "models"
    FICHIER_RESSOURCES = "table_pivot_anonymisee.csv"
    FICHIER_AVANCEMENT = "table_avancement_departement_semaine_anonymisee.csv"

# Métriques de référence des modèles retenus (Jours 2-3), affichées telles
# quelles dans le dashboard pour contextualiser chaque prédiction — jamais un
# chiffre sans son incertitude associée.
METRIQUES = {
    "A_U": {"label": "Matériel compté (unités)", "mae": 6.97, "r2": 0.80},
    "A_m": {"label": "Câble (mètres)", "mae": 1375.71, "r2": 0.71},
    "B_S2": {"mae": 4.09},
    "B_S4": {"mae": 4.25},
    "C": {"recall": 0.93, "precision": 0.44, "seuil": 0.35},
}

plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


# ----------------------------------------------------------------------------
# Chargement des données et modèles (mis en cache)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    df_ressources = pd.read_csv(DATA_DIR / FICHIER_RESSOURCES)
    df_avancement = pd.read_csv(DATA_DIR / FICHIER_AVANCEMENT, parse_dates=["Semaine"])
    df_avancement = df_avancement[df_avancement["Departement"] != "TOUTES"]
    return df_ressources, df_avancement


@st.cache_resource
def load_models():
    with open(MODELS_DIR / "model_A_ressources_U.pkl", "rb") as f:
        model_a_u = pickle.load(f)
    with open(MODELS_DIR / "model_A_ressources_m.pkl", "rb") as f:
        model_a_m = pickle.load(f)
    with open(MODELS_DIR / "model_B_avancement_tendance.pkl", "rb") as f:
        model_b = pickle.load(f)
    with open(MODELS_DIR / "model_C_risque_logreg.pkl", "rb") as f:
        model_c_obj = pickle.load(f)
    return model_a_u, model_a_m, model_b, model_c_obj["pipeline"], model_c_obj["seuil_optimise"]


df_ressources, df_avancement = load_data()
model_a_u, model_a_m, model_b, model_c, seuil_c = load_models()

CAT_FEATURES_A = ["Departement", "Commune", "Categorie", "ID_Tache", "Statut"]
NUM_FEATURES_A = ["Poids", "Qte_Prevue", "Nb_Anomalies_Signalees"]
FEATURES_C = ["Nb_Anomalies", "Nb_Lignes_Materiel", "Prop_Non_Commencees"]


# ----------------------------------------------------------------------------
# Table par localité (grain unique), réutilisée par les pages Ressources/Risques
# ----------------------------------------------------------------------------
@st.cache_data
def build_table_localites():
    loc = df_ressources.groupby(
        ["ID_Localite", "Localite", "Departement", "Commune", "Statut"]
    ).agg(
        Avancement_pct=("Avancement_Global_Localite_pct", "first"),
        Nb_Anomalies=("Nb_Anomalies_Signalees", "first"),
        Nb_Lignes_Materiel=("ID_Helper", "count"),
        Prop_Non_Commencees=("Taux_Realisation", lambda x: (x == 0).mean()),
    ).reset_index()
    loc["Seuil_Dept_Q1"] = loc.groupby("Departement")["Avancement_pct"].transform(
        lambda x: x.quantile(0.25)
    )
    loc["En_Retard_Relatif"] = (loc["Avancement_pct"] <= loc["Seuil_Dept_Q1"]).astype(int)
    loc["Proba_Risque"] = model_c.predict_proba(loc[FEATURES_C])[:, 1]
    loc["Signale_Risque"] = (loc["Proba_Risque"] >= seuil_c).astype(int)
    return loc


table_localites = build_table_localites()

# ----------------------------------------------------------------------------
# Barre latérale — navigation
# ----------------------------------------------------------------------------
st.sidebar.title("⚡ P2AE Rollout Forecast")
st.sidebar.caption("SBEE Bénin · Phase 1, Lot 1 · ElecTrack Pro")
page = st.sidebar.radio("Page", ["🧱 Ressources", "📈 Avancement", "⚠️ Risques"])
st.sidebar.markdown("---")
st.sidebar.metric("Localités suivies", "55")
st.sidebar.metric("Départements", "4")
st.sidebar.markdown("---")
if PUBLIC_MODE:
    st.sidebar.caption(
        "🌐 Mode public — localités et communes pseudonymisées (Localite_A, "
        "Commune_A…), départements réels (information publique). Modèles "
        "ré-entraînés sur ces données pseudonymisées. Voir décision D5."
    )
else:
    st.sidebar.caption(
        "⚠️ Mode interne — données de travail réelles (noms de localités/communes). "
        "Ne pas partager publiquement sans activer P2AE_PUBLIC_MODE=1 (décision D5)."
    )


# ----------------------------------------------------------------------------
# Page 1 — Ressources (Modèle A)
# ----------------------------------------------------------------------------
def page_ressources():
    st.title("🧱 Ressources — Matériel restant à livrer")
    st.caption(
        f"Modèle retenu : Gradient Boosting (unités, MAE≈{METRIQUES['A_U']['mae']:.0f}, "
        f"R²={METRIQUES['A_U']['r2']:.2f}) · Ridge (câble, MAE≈{METRIQUES['A_m']['mae']:.0f} m, "
        f"R²={METRIQUES['A_m']['r2']:.2f})"
    )

    localites = sorted(df_ressources["Localite"].unique())
    choix = st.selectbox("Choisir une localité", localites)

    sub = df_ressources[df_ressources["Localite"] == choix].copy()
    dep = sub["Departement"].iloc[0]
    commune = sub["Commune"].iloc[0]
    st.markdown(f"**Département :** {dep} · **Commune :** {commune}")

    # Prédiction du modèle retenu, par ligne, selon l'unité
    def predire(row):
        X = pd.DataFrame([row[CAT_FEATURES_A + NUM_FEATURES_A]])
        modele = model_a_u if row["Unite"] == "U" else model_a_m
        return max(0.0, float(modele.predict(X)[0]))

    sub["Prediction_Modele"] = sub.apply(predire, axis=1)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Lignes matériel", len(sub))
    with col2:
        restant_u = sub.loc[sub["Unite"] == "U", "Quantite_Restante"].sum()
        st.metric("Restant (unités comptées)", f"{restant_u:.0f}")
    with col3:
        restant_m = sub.loc[sub["Unite"] == "m", "Quantite_Restante"].sum()
        st.metric("Restant (câble)", f"{restant_m:,.0f} m")

    st.markdown("#### Détail par tâche et matériel")
    affichage = sub[
        ["ID_Tache", "Designation", "Unite", "Qte_Prevue", "Qte_Realisee",
         "Quantite_Restante", "Prediction_Modele", "Taux_Realisation"]
    ].rename(columns={
        "Quantite_Restante": "Restant (observé)",
        "Prediction_Modele": "Restant (modèle)",
        "Taux_Realisation": "Taux réalisation",
    }).sort_values("Restant (observé)", ascending=False)
    affichage["Taux réalisation"] = (affichage["Taux réalisation"] * 100).round(0).astype(int).astype(str) + " %"
    st.dataframe(affichage, width="stretch", hide_index=True)

    st.markdown("#### Quantité restante par tâche (observé vs modèle)")
    graf = sub.groupby("ID_Tache")[["Quantite_Restante", "Prediction_Modele"]].sum().sort_values(
        "Quantite_Restante", ascending=True
    )
    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.4 * len(graf))))
    y_pos = np.arange(len(graf))
    ax.barh(y_pos - 0.2, graf["Quantite_Restante"], height=0.4, label="Observé", color="#2E5A8C")
    ax.barh(y_pos + 0.2, graf["Prediction_Modele"], height=0.4, label="Modèle", color="#C0622D")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(graf.index)
    ax.legend()
    st.pyplot(fig)


# ----------------------------------------------------------------------------
# Page 2 — Avancement (Modèle B)
# ----------------------------------------------------------------------------
def page_avancement():
    st.title("📈 Avancement — Observé et projection")
    st.caption(
        f"Modèle retenu : tendance linéaire par département "
        f"(MAE≈{METRIQUES['B_S2']['mae']:.1f} pts à S+2, {METRIQUES['B_S4']['mae']:.1f} pts à S+4)"
    )

    departements = sorted(df_avancement["Departement"].unique())
    choix = st.selectbox("Choisir un département", departements)

    sub = df_avancement[df_avancement["Departement"] == choix].sort_values("Semaine").reset_index(drop=True)
    derniere_semaine = sub["Semaine"].max()
    dernier_avancement = sub.loc[sub["Semaine"] == derniere_semaine, "Avancement"].iloc[0]
    derniers_jours = sub.loc[sub["Semaine"] == derniere_semaine, "Jours_Ecoules_Depuis_Debut_Chantier"].iloc[0]

    modele_dep = model_b[choix]
    horizons = {"Aujourd'hui": 0, "S+2": 2, "S+4": 4}
    mae_par_horizon = {0: 0.0, 2: METRIQUES["B_S2"]["mae"], 4: METRIQUES["B_S4"]["mae"]}

    projections = []
    for label, h in horizons.items():
        jours_proj = derniers_jours + 7 * h
        X_pred = pd.DataFrame([[jours_proj]], columns=["Jours_Ecoules_Depuis_Debut_Chantier"])
        pred = float(modele_dep.predict(X_pred)[0])
        pred = min(100.0, max(0.0, pred))
        projections.append({"Horizon": label, "Avancement_pct": pred, "MAE": mae_par_horizon[h]})
    proj_df = pd.DataFrame(projections)

    col1, col2, col3 = st.columns(3)
    for col, row in zip([col1, col2, col3], proj_df.itertuples()):
        with col:
            marge = f" ± {row.MAE:.1f}" if row.MAE > 0 else ""
            st.metric(row.Horizon, f"{row.Avancement_pct:.0f} %{marge}")

    st.markdown("#### Trajectoire observée et projection")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(sub["Semaine"], sub["Avancement"], "o-", color="#2E5A8C", label="Observé", markersize=4)

    dates_proj = [derniere_semaine + pd.Timedelta(weeks=h) for h in [0, 2, 4]]
    valeurs_proj = proj_df["Avancement_pct"].values
    marges_proj = proj_df["MAE"].values
    ax.plot(dates_proj, valeurs_proj, "--o", color="#C0622D", label="Projection")
    ax.fill_between(
        dates_proj,
        np.array(valeurs_proj) - np.array(marges_proj),
        np.array(valeurs_proj) + np.array(marges_proj),
        color="#C0622D", alpha=0.15, label="Marge d'erreur (± MAE)"
    )
    ax.set_ylabel("Avancement (%)")
    ax.set_ylim(0, 100)
    ax.legend()
    plt.xticks(rotation=30)
    st.pyplot(fig)

    st.caption(
        "La marge d'erreur affichée correspond à l'erreur moyenne mesurée du modèle sur les 4 dernières "
        "semaines de test (Jour 2) — pas une incertitude statistique formelle."
    )


# ----------------------------------------------------------------------------
# Page 3 — Risques (Modèle C)
# ----------------------------------------------------------------------------
def page_risques():
    st.title("⚠️ Risques — Localités à surveiller en priorité")
    st.caption(
        f"Cible : sous-avancement relatif par rapport aux autres localités du même département · "
        f"Modèle : régression logistique, seuil optimisé à {seuil_c} · "
        f"Performance **estimée par validation croisée** (Jour 3, hors échantillon) : "
        f"Recall={METRIQUES['C']['recall']:.2f}, Precision={METRIQUES['C']['precision']:.2f}"
    )

    n_risque = table_localites["Signale_Risque"].sum()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Localités signalées à risque (modèle actuel)", f"{n_risque} / 55")
    with col2:
        st.metric("Seuil de décision", f"{seuil_c}")
    st.caption(
        "Le nombre de localités signalées ci-dessus est calculé en ré-appliquant le modèle final "
        "(entraîné sur les 55 localités) à ces mêmes localités — c'est le calcul pertinent pour un "
        "usage en production. Il peut différer légèrement des 32 localités qu'aurait signalées "
        "l'évaluation par validation croisée du Jour 3 (Precision/Recall ci-dessus) : cet écart est "
        "normal, pas une erreur — la validation croisée reste la référence pour juger de la fiabilité "
        "du modèle sur de nouvelles localités."
    )

    st.markdown("#### Localités signalées, par ordre de probabilité de risque")
    table_risque = table_localites[table_localites["Signale_Risque"] == 1].sort_values(
        "Proba_Risque", ascending=False
    )
    affichage = table_risque[
        ["Localite", "Departement", "Commune", "Avancement_pct", "Proba_Risque", "Prop_Non_Commencees", "Nb_Anomalies"]
    ].rename(columns={
        "Avancement_pct": "Avancement (%)", "Proba_Risque": "Probabilité de risque",
        "Prop_Non_Commencees": "Part non démarrée", "Nb_Anomalies": "Anomalies signalées",
    })
    affichage["Avancement (%)"] = affichage["Avancement (%)"].round(1)
    affichage["Probabilité de risque"] = (affichage["Probabilité de risque"] * 100).round(0).astype(int).astype(str) + " %"
    affichage["Part non démarrée"] = (affichage["Part non démarrée"] * 100).round(0).astype(int).astype(str) + " %"
    st.dataframe(affichage, width="stretch", hide_index=True)

    st.markdown("#### Comprendre une alerte — facteurs dominants")
    choix = st.selectbox("Choisir une localité à risque", table_risque["Localite"].tolist())
    ligne = table_localites[table_localites["Localite"] == choix].iloc[0]

    # Contribution des variables (coefficient x valeur standardisée), équivalent
    # analytique de SHAP pour un modèle linéaire (voir notebooks/05, section 4c).
    scaler = model_c.named_steps["scale"]
    logreg = model_c.named_steps["model"]
    X_ligne = pd.DataFrame([ligne[FEATURES_C]])
    X_scaled = scaler.transform(X_ligne)[0]
    contributions = pd.Series(logreg.coef_[0] * X_scaled, index=FEATURES_C).sort_values()

    col1, col2 = st.columns([1, 1.3])
    with col1:
        st.metric("Probabilité de risque", f"{ligne['Proba_Risque']*100:.0f} %")
        st.metric("Avancement observé", f"{ligne['Avancement_pct']:.0f} %")
        st.metric("Part des tâches non démarrées", f"{ligne['Prop_Non_Commencees']*100:.0f} %")
        st.metric("Anomalies terrain signalées", int(ligne["Nb_Anomalies"]))
    with col2:
        fig, ax = plt.subplots(figsize=(6, 3))
        couleurs = ["#C0622D" if v < 0 else "#2E5A8C" for v in contributions.values]
        ax.barh(contributions.index, contributions.values, color=couleurs)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title("Contribution au score de risque")
        st.pyplot(fig)

    st.caption(
        "Une contribution positive (bleu) augmente le risque prédit ; une contribution négative (orange) le réduit. "
        "Rappel du constat déjà établi en EDA : un signalement d'anomalie réduit le risque prédit, car il traduit "
        "une localité déjà inspectée en détail, pas une localité mal gérée."
    )


# ----------------------------------------------------------------------------
# Routage
# ----------------------------------------------------------------------------
if page == "🧱 Ressources":
    page_ressources()
elif page == "📈 Avancement":
    page_avancement()
else:
    page_risques()
