import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import os
import re
import plotly.graph_objects as go

# ── Chargement artefacts ──────────────────────────────────────────────────
@st.cache_resource
def charger_modele_n2():
    base   = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    model  = joblib.load(os.path.join(base, 'gb_multilabel_niveau2.pkl'))
    scaler = joblib.load(os.path.join(base, 'robust_scaler_niveau2.pkl'))
    with open(os.path.join(base, 'config_niveau2.json'), encoding='utf-8') as f:
        config = json.load(f)
    return model, scaler, config

model_n2, scaler_n2, config_n2 = charger_modele_n2()

# ── Feature engineering ───────────────────────────────────────────────────
def feature_engineering(df):
    df = df.copy()
    df['temp_diff']      = df['Process temperature [K]'] - df['Air temperature [K]']
    df['power_kw']       = (df['Torque [Nm]'] * df['Rotational speed [rpm]'] * 2 * np.pi / 60) / 1000
    df['thermal_stress'] = df['temp_diff'] * df['power_kw']
    df['Type_encoded']   = df['Type'].map({'L': 0, 'M': 1, 'H': 2})
    return df

# ── Prédiction Niveau 2 ───────────────────────────────────────────────────
def predire_n2(df_brut):
    df = feature_engineering(df_brut)
    numeric_cols = ['Air temperature [K]', 'Process temperature [K]',
                    'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
                    'temp_diff', 'power_kw', 'thermal_stress']
    df[numeric_cols] = scaler_n2.transform(df[numeric_cols])
    df.columns = [re.sub(r'[\[\]<>]', '', c).strip().replace(' ', '_')
                  for c in df.columns]
    X      = df[config_n2['features_utilisees']]
    seuils = config_n2['seuils_production']
    labels = config_n2['labels']
    probas = np.array([est.predict_proba(X)[0, 1] for est in model_n2.estimators_])

    predictions  = {}
    probabilites = {}
    for i, label in enumerate(labels):
        prob = round(float(probas[i]), 4)
        probabilites[label] = prob
        if label in ['HDF', 'PWF', 'OSF'] and seuils.get(label):
            predictions[label] = int(prob >= seuils[label])
        else:
            predictions[label] = None

    # Règle heuristique TWF
    predictions['TWF'] = int(df_brut['Tool wear [min]'].iloc[0] >= 200)
    return predictions, probabilites

# ── Configuration actions ─────────────────────────────────────────────────
ACTIONS = {
    'HDF': {
        'label' : 'Heat Dissipation Failure',
        'icon'  : '🌡️',
        'color' : '#FF6F00',
        'action': 'Vérifier le circuit de refroidissement. Vitesse de rotation trop basse ou température ambiante trop élevée.',
        'seuil' : 0.7846
    },
    'PWF': {
        'label' : 'Power Failure',
        'icon'  : '⚡',
        'color' : '#1565C0',
        'action': "Contrôler l'alimentation électrique et la transmission mécanique. Puissance mécanique anormale détectée.",
        'seuil' : 0.9998
    },
    'OSF': {
        'label' : 'Overstrain Failure',
        'icon'  : '⚙️',
        'color' : '#6A1B9A',
        'action': "Remplacer l'outil et réduire le couple. Surcontrainte mécanique : outil usé sous fort couple.",
        'seuil' : 0.2058
    },
    'TWF': {
        'label' : 'Tool Wear Failure',
        'icon'  : '🔩',
        'color' : '#B71C1C',
        'action': "Remplacer l'outil immédiatement. Usure au-delà du seuil physique critique (200 min).",
        'seuil' : None
    },
    'RNF': {
        'label' : 'Random Failure',
        'icon'  : '🎲',
        'color' : '#546E7A',
        'action': 'Inspection manuelle aléatoire. Panne non prédictible par les capteurs.',
        'seuil' : None
    },
}

# ── En-tête ───────────────────────────────────────────────────────────────
st.title("🔍 Niveau 2 — Identification du mode de panne")
st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────────────────
st.sidebar.header("📡 Paramètres capteurs")
st.sidebar.markdown("---")

type_produit = st.sidebar.selectbox("Type de produit", ['L', 'M', 'H'])
air_temp  = st.sidebar.slider("Température ambiante [K]",  295.0, 305.0, 300.0, 0.1)
proc_temp = st.sidebar.slider("Température process [K]",   305.0, 315.0, 310.0, 0.1)
rot_speed = st.sidebar.slider("Vitesse de rotation [rpm]", 1168,  2886,  1500,  1)
torque    = st.sidebar.slider("Couple [Nm]",               3.8,   76.6,  40.0,  0.1)
tool_wear = st.sidebar.slider("Usure outil [min]",         0,     253,   100,   1)

st.sidebar.markdown("---")
st.sidebar.markdown("**Seuils de décision par mode :**")
for label, info in ACTIONS.items():
    if info['seuil']:
        st.sidebar.markdown(
            f"<span style='color:{info['color']}'>{info['icon']} {label}</span> : `{info['seuil']}`",
            unsafe_allow_html=True
        )

# ── Prédiction ────────────────────────────────────────────────────────────
df_input = pd.DataFrame([{
    'Type'                    : type_produit,
    'Air temperature [K]'     : air_temp,
    'Process temperature [K]' : proc_temp,
    'Rotational speed [rpm]'  : rot_speed,
    'Torque [Nm]'             : torque,
    'Tool wear [min]'         : tool_wear,
}])

predictions, probabilites = predire_n2(df_input)
modes_detectes = [l for l, v in predictions.items() if v == 1]

# ── Résultat principal ────────────────────────────────────────────────────
if modes_detectes:
    modes_str = " + ".join([f"{ACTIONS[m]['icon']} {m}" for m in modes_detectes])
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#B71C1C,#E53935);
                padding:1.5rem;border-radius:12px;text-align:center;margin-bottom:1.5rem'>
        <h2 style='color:white;margin:0'>⚠️ MODE(S) DE PANNE DÉTECTÉ(S)</h2>
        <h3 style='color:#FFCCBC;margin:0.5rem 0'>{modes_str}</h3>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1B5E20,#2E7D32);
                padding:1.5rem;border-radius:12px;text-align:center;margin-bottom:1.5rem'>
        <h2 style='color:white;margin:0'>✅ Aucun mode de panne détecté</h2>
        <p style='color:#C8E6C9;margin:0'>Machine en fonctionnement normal</p>
    </div>""", unsafe_allow_html=True)

# ── Jauges par mode ───────────────────────────────────────────────────────
st.subheader("📊 Probabilités par mode de panne")

cols = st.columns(5)
labels_order = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']

for i, label in enumerate(labels_order):
    info   = ACTIONS[label]
    prob   = probabilites.get(label, 0.0)
    pred   = predictions.get(label)
    seuil  = info['seuil']
    actif  = pred == 1

    with cols[i]:
        couleur = info['color'] if actif else "#BDBDBD"

        fig = go.Figure(go.Indicator(
            mode  = "gauge+number",
            value = prob * 100,
            title = {"text": f"{info['icon']} {label}", "font": {"size": 13}},
            number= {"suffix": "%", "font": {"size": 20,
                     "color": info['color'] if actif else "#555"}},
            gauge = {
                "axis" : {"range": [0, 100], "tickwidth": 1, "tickfont": {"size": 9}},
                "bar"  : {"color": couleur},
                "steps": [
                    {"range": [0, (seuil or 0.5)*100], "color": "#F5F5F5"},
                    {"range": [(seuil or 0.5)*100, 100], "color": "#FFEBEE" if actif else "#F5F5F5"},
                ],
                "threshold": {
                    "line" : {"color": info['color'], "width": 3},
                    "thickness": 0.85,
                    "value": (seuil or 0.5) * 100
                } if seuil else {}
            }
        ))
        fig.update_layout(height=200, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

        # Badge statut
        if pred is None:
            st.markdown(f"<div style='text-align:center;background:#ECEFF1;"
                        f"border-radius:8px;padding:4px;font-size:0.75rem;color:#546E7A'>"
                        f"⚠️ Heuristique</div>", unsafe_allow_html=True)
        elif actif:
            st.markdown(f"<div style='text-align:center;background:{info['color']};"
                        f"border-radius:8px;padding:4px;font-size:0.75rem;color:white'>"
                        f"🔴 DÉTECTÉ</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center;background:#E8F5E9;"
                        f"border-radius:8px;padding:4px;font-size:0.75rem;color:#2E7D32'>"
                        f"✅ Normal</div>", unsafe_allow_html=True)

# ── Actions de maintenance ────────────────────────────────────────────────
st.markdown("---")
st.subheader("🛠️ Actions de maintenance recommandées")

if modes_detectes:
    for mode in modes_detectes:
        info = ACTIONS[mode]
        st.markdown(f"""
        <div style='background:{info['color']}15;border-left:5px solid {info['color']};
                    padding:1rem 1.5rem;border-radius:0 8px 8px 0;margin-bottom:1rem'>
            <h4 style='color:{info['color']};margin:0'>
                {info['icon']} {mode} — {info['label']}</h4>
            <p style='color:#333;margin:0.5rem 0 0'>{info['action']}</p>
        </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style='background:#E8F5E9;border-left:5px solid #00C853;
                padding:1rem 1.5rem;border-radius:0 8px 8px 0'>
        <h4 style='color:#1B5E20;margin:0'>✅ Aucune action requise</h4>
        <p style='color:#333;margin:0.5rem 0 0'>
            La machine fonctionne dans les paramètres normaux.
            Poursuivre la surveillance régulière des capteurs.</p>
    </div>""", unsafe_allow_html=True)

# ── Tableau récapitulatif ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Récapitulatif")

col_recap, col_fe = st.columns([1, 1])

with col_recap:
    df_recap = pd.DataFrame([{
        'Mode'      : f"{ACTIONS[l]['icon']} {l}",
        'Nom complet': ACTIONS[l]['label'],
        'Probabilité': f"{probabilites.get(l, 0)*100:.2f}%",
        'Statut'    : '🔴 DÉTECTÉ' if predictions.get(l)==1
                      else ('⚠️ Heuristique' if predictions.get(l) is None
                      else '✅ Normal')
    } for l in labels_order])
    st.dataframe(df_recap, use_container_width=True, hide_index=True)

with col_fe:
    df_fe     = feature_engineering(df_input)
    st.markdown("**Features calculées**")
    st.metric("Différentiel thermique",
              f"{float(df_fe['temp_diff'].iloc[0]):.1f} K")
    st.metric("Puissance mécanique",
              f"{float(df_fe['power_kw'].iloc[0]):.2f} kW")
    st.metric("Stress thermique",
              f"{float(df_fe['thermal_stress'].iloc[0]):.1f}")
    st.metric("Usure outil",
              f"{tool_wear} min",
              delta="⚠️ Critique" if tool_wear >= 200 else "✅ Normal",
              delta_color="inverse" if tool_wear >= 200 else "normal")

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#888;font-size:0.85rem'>"
    "Modèle : MultiOutput GradientBoosting | "
    "HDF F1=0.98 | PWF F1=1.00 | OSF F1=0.94 | "
    "TWF : règle heuristique (usure > 200 min) | "
    "RNF : non prédictible</p>",
    unsafe_allow_html=True
)