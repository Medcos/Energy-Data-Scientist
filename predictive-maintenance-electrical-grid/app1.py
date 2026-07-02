import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ── Configuration de la page ─────────────────────────────────────────────
st.set_page_config(
    page_title  = "Maintenance Prédictive — Niveau 1",
    page_icon   = "🔧",
    layout      = "wide",
    initial_sidebar_state = "expanded"
)

# ── Chargement des artefacts ─────────────────────────────────────────────
@st.cache_resource
def charger_modele():
    base = os.path.join(os.path.dirname(__file__), 'models')
    model  = joblib.load(os.path.join(base, 'gradient_boosting_niveau1.pkl'))
    scaler = joblib.load(os.path.join(base, 'robust_scaler_niveau1.pkl'))
    with open(os.path.join(base, 'config_niveau1.json'), encoding='utf-8') as f:
        config = json.load(f)
    return model, scaler, config

model, scaler, config = charger_modele()

# ── Feature engineering ──────────────────────────────────────────────────
def feature_engineering(df):
    df = df.copy()
    df['temp_diff']      = df['Process temperature [K]'] - df['Air temperature [K]']
    df['power_kw']       = (df['Torque [Nm]'] * df['Rotational speed [rpm]'] * 2 * np.pi / 60) / 1000
    df['thermal_stress'] = df['temp_diff'] * df['power_kw']
    df['Type_encoded']   = df['Type'].map({'L': 0, 'M': 1, 'H': 2})
    return df

# ── Prédiction ───────────────────────────────────────────────────────────
def predire(df_brut):
    df = feature_engineering(df_brut)

    numeric_cols = ['Air temperature [K]', 'Process temperature [K]',
                    'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
                    'temp_diff', 'power_kw', 'thermal_stress']

    df[numeric_cols] = scaler.transform(df[numeric_cols])
    X     = df[config['features_utilisees']]
    proba = float(model.predict_proba(X)[0, 1])
    pred  = int(proba >= config['seuil_decision'])
    return pred, proba

# ── En-tête ──────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(135deg,#1F4E79,#2E75B6);
            padding:2rem;border-radius:12px;margin-bottom:2rem;text-align:center'>
    <h1 style='color:white;margin:0;font-size:2.2rem'>🔧 Maintenance Prédictive</h1>
    <p style='color:#BDD7EE;margin:0.5rem 0 0;font-size:1.1rem'>
        Prédiction de panne machine industrielle — Niveau 1</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar — Saisie des capteurs ────────────────────────────────────────
st.sidebar.header("📡 Paramètres capteurs")
st.sidebar.markdown("---")

type_produit = st.sidebar.selectbox(
    "Type de produit", options=['L', 'M', 'H'],
    help="L = Low quality, M = Medium, H = High"
)
air_temp = st.sidebar.slider(
    "Température ambiante [K]", 295.0, 305.0, 300.0, 0.1
)
proc_temp = st.sidebar.slider(
    "Température process [K]", 305.0, 315.0, 310.0, 0.1
)
rot_speed = st.sidebar.slider(
    "Vitesse de rotation [rpm]", 1168, 2886, 1500, 1
)
torque = st.sidebar.slider(
    "Couple [Nm]", 3.8, 76.6, 40.0, 0.1
)
tool_wear = st.sidebar.slider(
    "Usure outil [min]", 0, 253, 100, 1
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Seuil de décision :** `{config['seuil_decision']}`")

# ── Prédiction en temps réel ─────────────────────────────────────────────
df_input = pd.DataFrame([{
    'Type'                     : type_produit,
    'Air temperature [K]'      : air_temp,
    'Process temperature [K]'  : proc_temp,
    'Rotational speed [rpm]'   : rot_speed,
    'Torque [Nm]'              : torque,
    'Tool wear [min]'          : tool_wear,
}])

prediction, probabilite = predire(df_input)

# ── Layout principal ─────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 1])

# Carte résultat principal
with col1:
    if prediction == 1:
        st.markdown(f"""
        <div style='background:#FF4B4B;padding:1.5rem;border-radius:12px;text-align:center'>
            <h2 style='color:white;margin:0'>⚠️ PANNE PRÉDITE</h2>
            <p style='color:white;font-size:1.8rem;font-weight:bold;margin:0.5rem 0'>
                {probabilite:.1%}</p>
            <p style='color:#FFD0D0;margin:0'>de probabilité de panne</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background:#00C853;padding:1.5rem;border-radius:12px;text-align:center'>
            <h2 style='color:white;margin:0'>✅ MACHINE OK</h2>
            <p style='color:white;font-size:1.8rem;font-weight:bold;margin:0.5rem 0'>
                {1-probabilite:.1%}</p>
            <p style='color:#D0FFE8;margin:0'>de probabilité de fonctionnement normal</p>
        </div>""", unsafe_allow_html=True)

# Jauge de probabilité
with col2:
    fig_gauge = go.Figure(go.Indicator(
        mode  = "gauge+number+delta",
        value = probabilite * 100,
        title = {"text": "Probabilité de panne (%)", "font": {"size": 14}},
        delta = {"reference": config['seuil_decision'] * 100, "valueformat": ".1f"},
        gauge = {
            "axis"  : {"range": [0, 100], "tickwidth": 1},
            "bar"   : {"color": "#FF4B4B" if prediction == 1 else "#00C853"},
            "steps" : [
                {"range": [0,  config['seuil_decision']*100], "color": "#E8F5E9"},
                {"range": [config['seuil_decision']*100, 100], "color": "#FFEBEE"},
            ],
            "threshold": {
                "line" : {"color": "#1F4E79", "width": 4},
                "thickness": 0.85,
                "value": config['seuil_decision'] * 100
            }
        }
    ))
    fig_gauge.update_layout(height=250, margin=dict(t=40,b=0,l=20,r=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

# Features engineerées calculées
with col3:
    df_fe     = feature_engineering(df_input)
    temp_diff = float(df_fe['temp_diff'].iloc[0])
    power_kw  = float(df_fe['power_kw'].iloc[0])
    therm_str = float(df_fe['thermal_stress'].iloc[0])

    st.markdown("**🔬 Features calculées**")
    st.metric("Différentiel thermique", f"{temp_diff:.1f} K")
    st.metric("Puissance mécanique",    f"{power_kw:.2f} kW")
    st.metric("Stress thermique",       f"{therm_str:.1f}")

st.markdown("---")

# ── Radar des capteurs ───────────────────────────────────────────────────
st.subheader("📊 Profil des capteurs")

col_radar, col_table = st.columns([1, 1])

with col_radar:
    # Normalisation min-max pour le radar
    ranges = {
        'Air temp [K]'   : (295, 305),
        'Process temp [K]': (305, 315),
        'Vitesse [rpm]'  : (1168, 2886),
        'Couple [Nm]'    : (3.8, 76.6),
        'Usure [min]'    : (0, 253),
    }
    vals_raw = [air_temp, proc_temp, rot_speed, torque, tool_wear]
    vals_norm = [(v - r[0]) / (r[1] - r[0]) * 100
                 for v, r in zip(vals_raw, ranges.values())]

    fig_radar = go.Figure(go.Scatterpolar(
        r      = vals_norm + [vals_norm[0]],
        theta  = list(ranges.keys()) + [list(ranges.keys())[0]],
        fill   = 'toself',
        line_color = "#FF4B4B" if prediction == 1 else "#1F4E79",
        fillcolor  = "rgba(255,75,75,0.2)" if prediction == 1 else "rgba(31,78,121,0.2)"
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        showlegend=False, height=350,
        margin=dict(t=40,b=40,l=40,r=40)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_table:
    st.markdown("**Valeurs saisies**")
    df_display = pd.DataFrame({
        'Capteur': ['Type produit', 'Air temp [K]', 'Process temp [K]',
                    'Vitesse [rpm]', 'Couple [Nm]', 'Usure [min]'],
        'Valeur' : [type_produit, air_temp, proc_temp,
                    rot_speed, torque, tool_wear]
    })
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("**Métriques du modèle**")
    metriques = config.get('metriques_test', {})
    df_metrics = pd.DataFrame({
        'Métrique' : ['Precision', 'Recall', 'F1-score', 'AUC-ROC'],
        'Valeur'   : [
            metriques.get('precision_panne', 0.93),
            metriques.get('recall_panne',    0.82),
            metriques.get('f1_panne',        0.88),
            metriques.get('auc_roc',         0.9798),
        ]
    })
    st.dataframe(df_metrics, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#888;font-size:0.85rem'>"
    "Modèle : GradientBoostingClassifier | "
    f"Seuil : {config['seuil_decision']} | "
    f"AUC-ROC : 0.9798 | "
    f"Généré le {datetime.now().strftime('%d/%m/%Y')}</p>",
    unsafe_allow_html=True
)