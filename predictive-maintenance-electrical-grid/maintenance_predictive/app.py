import streamlit as st

st.set_page_config(
    page_title = "Maintenance Prédictive",
    page_icon  = "🔧",
    layout     = "wide"
)

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .stat-box {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 0.5rem;
    }
    .stat-num   { font-size: 2rem; font-weight: 800; }
    .stat-label { font-size: 0.82rem; color: #666; margin-top: 0.2rem; }
    .card {
        border-radius: 14px;
        padding: 1.8rem 2rem;
        margin-bottom: 1rem;
        height: 100%;
    }
    .card-vert   { background: #F1F8F1; border: 2px solid #00C853; }
    .card-orange { background: #FFF8F0; border: 2px solid #FF6F00; }
    .step-box {
        background: white;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        border-left: 4px solid #2E75B6;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .num-circle {
        background: #1F4E79;
        color: white;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.9rem;
        margin-right: 0.6rem;
        flex-shrink: 0;
    }
    .info-panel {
        background: white;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        height: 100%;
    }
    .mode-ligne {
        padding: 0.5rem 0.8rem;
        border-radius: 8px;
        margin: 0.4rem 0;
        font-size: 0.9rem;
    }
    .footer {
        background: linear-gradient(135deg, #1F4E79, #2E75B6);
        padding: 1.5rem 2rem;
        border-radius: 14px;
        text-align: center;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(135deg,#1F4E79 0%,#2E75B6 100%);
            padding:2.5rem 2rem; border-radius:16px; text-align:center;
            margin-bottom:2rem'>
    <div style='font-size:3rem; margin-bottom:0.5rem'>🔧</div>
    <h1 style='color:white; font-size:2.5rem; margin:0; font-weight:800;
               letter-spacing:-0.5px'>
        Maintenance Prédictive</h1>
    <p style='color:#BDD7EE; font-size:1.05rem; margin:0.8rem 0 1.2rem'>
        Détection et identification de pannes machine industrielle par IA</p>
    <div style='display:flex; justify-content:center; gap:0.5rem;
                flex-wrap:wrap'>
        <span style='background:rgba(255,255,255,0.15); color:white;
                     padding:0.3rem 0.9rem; border-radius:20px;
                     font-size:0.82rem'>✓ GradientBoosting</span>
        <span style='background:rgba(255,255,255,0.15); color:white;
                     padding:0.3rem 0.9rem; border-radius:20px;
                     font-size:0.82rem'>✓ MultiOutput ML</span>
        <span style='background:rgba(255,255,255,0.15); color:white;
                     padding:0.3rem 0.9rem; border-radius:20px;
                     font-size:0.82rem'>✓ SHAP Interpretability</span>
        <span style='background:rgba(255,255,255,0.15); color:white;
                     padding:0.3rem 0.9rem; border-radius:20px;
                     font-size:0.82rem'>✓ Temps réel</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI ──────────────────────────────────────────────────────────────────
st.markdown("### 📊 Performance du modèle")
k1, k2, k3, k4, k5 = st.columns(5)

kpis = [
    ("0.88",   "F1-Score — Niveau 1", "#00C853"),
    ("0.9798", "AUC-ROC — Niveau 1",  "#2E75B6"),
    ("0.98",   "F1 — HDF Surchauffe", "#FF6F00"),
    ("1.00",   "F1 — PWF Puissance",  "#1565C0"),
    ("0.94",   "F1 — OSF Surcharge",  "#6A1B9A"),
]
for col, (val, label, color) in zip([k1,k2,k3,k4,k5], kpis):
    with col:
        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-num' style='color:{color}'>{val}</div>
            <div class='stat-label'>{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CARTES NIVEAU 1 / NIVEAU 2 ───────────────────────────────────────────
st.markdown("### 🚀 Deux niveaux de prédiction")
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div class='card card-vert'>
        <h2 style='color:#1B5E20; margin:0 0 0.3rem'>🎯 Niveau 1</h2>
        <h3 style='color:#2E7D32; margin:0 0 0.5rem; font-size:1.2rem'>
            Prédiction de panne</h3>
        <p style='color:#333; font-size:0.95rem; font-style:italic;
                  margin:0 0 1rem; padding:0.6rem 1rem;
                  background:#E8F5E9; border-radius:8px'>
            ❓ La machine va-t-elle tomber en panne ?</p>
        <p style='color:#444; margin:0.4rem 0'>
            ✅ Probabilité de panne en temps réel</p>
        <p style='color:#444; margin:0.4rem 0'>
            ✅ Jauge visuelle interactive</p>
        <p style='color:#444; margin:0.4rem 0'>
            ✅ Radar des 5 capteurs</p>
        <p style='color:#444; margin:0.4rem 0'>
            ✅ Features engineerées (power_kw, temp_diff)</p>
        <p style='color:#444; margin:0.4rem 0'>
            ✅ Seuil de décision optimisé : <b>0.4236</b></p>
        <div style='background:#E8F5E9; border-radius:8px;
                    padding:0.6rem 1rem; margin-top:1rem'>
            <span style='color:#1B5E20; font-size:0.88rem'>
                <b>Modèle :</b> GradientBoosting &nbsp;|&nbsp;
                <b>F1 = 0.88</b> &nbsp;|&nbsp;
                <b>AUC-ROC = 0.9798</b>
            </span>
        </div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class='card card-orange'>
        <h2 style='color:#E65100; margin:0 0 0.3rem'>🔍 Niveau 2</h2>
        <h3 style='color:#EF6C00; margin:0 0 0.5rem; font-size:1.2rem'>
            Identification du mode</h3>
        <p style='color:#333; font-size:0.95rem; font-style:italic;
                  margin:0 0 1rem; padding:0.6rem 1rem;
                  background:#FFF3E0; border-radius:8px'>
            ❓ Pourquoi la machine va-t-elle tomber en panne ?</p>
        <p style='color:#444; margin:0.4rem 0'>
            🌡️ <b>HDF</b> — Surchauffe &nbsp;
            <span style='color:#FF6F00'>(seuil 0.7846 | F1=0.98)</span></p>
        <p style='color:#444; margin:0.4rem 0'>
            ⚡ <b>PWF</b> — Puissance anormale &nbsp;
            <span style='color:#1565C0'>(seuil 0.9998 | F1=1.00)</span></p>
        <p style='color:#444; margin:0.4rem 0'>
            ⚙️ <b>OSF</b> — Surcontrainte &nbsp;
            <span style='color:#6A1B9A'>(seuil 0.2058 | F1=0.94)</span></p>
        <p style='color:#444; margin:0.4rem 0'>
            🔩 <b>TWF</b> — Usure outil &nbsp;
            <span style='color:#B71C1C'>(règle heuristique)</span></p>
        <p style='color:#444; margin:0.4rem 0'>
            🛠️ Action de maintenance recommandée</p>
        <div style='background:#FFF3E0; border-radius:8px;
                    padding:0.6rem 1rem; margin-top:1rem'>
            <span style='color:#E65100; font-size:0.88rem'>
                <b>Modèle :</b> MultiOutput GradientBoosting &nbsp;|&nbsp;
                <b>5 estimateurs indépendants</b>
            </span>
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── COMMENT ÇA MARCHE ────────────────────────────────────────────────────
st.markdown("### ⚙️ Comment ça marche ?")
col_steps, col_modes = st.columns([3, 2], gap="large")

with col_steps:
    steps = [
        ("1", "📡", "Saisie des capteurs",
         "Température ambiante et process, vitesse de rotation, couple, usure outil, type de produit (L/M/H)."),
        ("2", "🔬", "Feature engineering automatique",
         "Calcul de temp_diff (ΔT thermique), power_kw (P = T × ω) et thermal_stress (produit des deux)."),
        ("3", "🤖", "Niveau 1 — Prédiction binaire",
         "GradientBoosting évalue la probabilité de panne. Si proba ≥ 0.4236 → PANNE PRÉDITE."),
        ("4", "🔍", "Niveau 2 — Identification du mode",
         "Si panne détectée, 5 estimateurs identifient le mode : HDF, PWF, OSF, TWF ou RNF."),
        ("5", "🛠️", "Action de maintenance",
         "Le système affiche l'action corrective adaptée au mode détecté pour intervenir efficacement."),
    ]
    for num, icon, titre, desc in steps:
        st.markdown(f"""
        <div class='step-box'>
            <div style='display:flex; align-items:flex-start; gap:0.8rem'>
                <div style='background:#1F4E79; color:white; border-radius:50%;
                            min-width:30px; height:30px; display:flex;
                            align-items:center; justify-content:center;
                            font-weight:bold; font-size:0.9rem'>
                    {num}
                </div>
                <div>
                    <p style='color:#1F4E79; font-weight:700; margin:0 0 0.2rem;
                               font-size:0.95rem'>{icon} {titre}</p>
                    <p style='color:#555; font-size:0.88rem; margin:0;
                               line-height:1.5'>{desc}</p>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

with col_modes:
    st.markdown("""
    <div class='info-panel'>
        <h4 style='color:#1F4E79; margin:0 0 1rem; font-size:1rem'>
            🏆 Modes de panne détectés</h4>""", unsafe_allow_html=True)

    modes = [
        ("🌡️", "HDF", "Heat Dissipation Failure", "F1 = 0.98", "#FF6F00", "#FFF8F0"),
        ("⚡",  "PWF", "Power Failure",             "F1 = 1.00", "#1565C0", "#F0F4FF"),
        ("⚙️",  "OSF", "Overstrain Failure",        "F1 = 0.94", "#6A1B9A", "#F5F0FF"),
        ("🔩",  "TWF", "Tool Wear Failure",          "Heuristique", "#B71C1C", "#FFF0F0"),
        ("🎲",  "RNF", "Random Failure",             "Non prédit", "#546E7A", "#F5F5F5"),
    ]
    for icon, code, nom, perf, color, bg in modes:
        st.markdown(
            f"<div style='background:{bg};border-left:4px solid {color};"
            f"border-radius:0 10px 10px 0;padding:0.7rem 1rem;"
            f"margin:0.5rem 0'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center'>"
            f"<span style='font-size:0.9rem'>{icon} <b style='color:{color}'>"
            f"{code}</b> — {nom}</span>"
            f"<span style='background:{color};color:white;font-size:0.75rem;"
            f"padding:0.15rem 0.5rem;border-radius:10px'>{perf}</span>"
            f"</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ── NAVIGATION ────────────────────────────────────────────────────────────
st.markdown("### 🧭 Navigation")
st.info("👈 Utilisez le **menu latéral gauche** pour naviguer entre les deux niveaux.")

n1, n2 = st.columns(2, gap="large")
with n1:
    st.markdown("""
    <div style='background:#F1F8F1;border:2px solid #00C853;
                border-radius:12px;padding:1.2rem;text-align:center'>
        <div style='font-size:2rem'>🎯</div>
        <h4 style='color:#1B5E20;margin:0.3rem 0'>Niveau 1 — Prédiction</h4>
        <p style='color:#555;font-size:0.88rem;margin:0'>
            Menu latéral → <b>Niveau1 Prediction</b></p>
    </div>""", unsafe_allow_html=True)

with n2:
    st.markdown("""
    <div style='background:#FFF8F0;border:2px solid #FF6F00;
                border-radius:12px;padding:1.2rem;text-align:center'>
        <div style='font-size:2rem'>🔍</div>
        <h4 style='color:#E65100;margin:0.3rem 0'>Niveau 2 — Identification</h4>
        <p style='color:#555;font-size:0.88rem;margin:0'>
            Menu latéral → <b>Niveau2 Mode Panne</b></p>
    </div>""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("""
<div class='footer'>
    <p style='color:#BDD7EE;margin:0 0 0.3rem;font-size:0.95rem;font-weight:600'>
        🔧 Système de Maintenance Prédictive par IA</p>
    <p style='color:#7FBBDD;margin:0;font-size:0.85rem'>
        Dataset : 10 000 observations &nbsp;|&nbsp;
        Précision : 93% &nbsp;|&nbsp;
        Rappel : 82% &nbsp;|&nbsp;
        F1 : 0.88 &nbsp;|&nbsp;
        AUC-ROC : 0.9798
    </p>
</div>
""", unsafe_allow_html=True)