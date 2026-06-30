import streamlit as st

st.set_page_config(
    page_title = "Maintenance Prédictive",
    page_icon  = "🔧",
    layout     = "wide"
)

st.markdown("""
<div style='background:linear-gradient(135deg,#1F4E79,#2E75B6);
            padding:3rem;border-radius:16px;text-align:center;margin-bottom:2rem'>
    <h1 style='color:white;font-size:2.8rem;margin:0'>🔧 Maintenance Prédictive</h1>
    <p style='color:#BDD7EE;font-size:1.2rem;margin:1rem 0 0'>
        Système de détection et d'identification de pannes machine industrielle</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style='background:#E8F5E9;padding:2rem;border-radius:12px;
                border-left:6px solid #00C853;height:280px'>
        <h2 style='color:#1B5E20'>🎯 Niveau 1</h2>
        <h3 style='color:#2E7D32'>Prédiction de panne</h3>
        <p style='color:#333'>La machine va-t-elle tomber en panne ?</p>
        <hr style='border-color:#A5D6A7'>
        <ul style='color:#333'>
            <li>Probabilité de panne en temps réel</li>
            <li>Jauge visuelle interactive</li>
            <li>Radar des capteurs</li>
            <li>Seuil de décision : 0.4236</li>
        </ul>
        <p><b>Modèle :</b> GradientBoosting | <b>F1 = 0.88</b> | <b>AUC-ROC = 0.9798</b></p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='background:#FFF3E0;padding:2rem;border-radius:12px;
                border-left:6px solid #FF6F00;height:280px'>
        <h2 style='color:#E65100'>🔍 Niveau 2</h2>
        <h3 style='color:#EF6C00'>Identification du mode de panne</h3>
        <p style='color:#333'>Pourquoi la machine va-t-elle tomber en panne ?</p>
        <hr style='border-color:#FFCC80'>
        <ul style='color:#333'>
            <li>HDF — Surchauffe (seuil 0.7846)</li>
            <li>PWF — Puissance anormale (seuil 0.9998)</li>
            <li>OSF — Surcontrainte (seuil 0.2058)</li>
            <li>Action de maintenance recommandée</li>
        </ul>
        <p><b>Modèle :</b> MultiOutput GB | <b>HDF F1=0.98</b> | <b>PWF F1=1.00</b></p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style='text-align:center;padding:1rem'>
    <p style='color:#888;font-size:0.9rem'>
    👈 Utilisez le menu latéral pour naviguer entre les deux niveaux<br>
    Dataset : predictive_maintenance.csv — 10 000 observations — 3.4% de pannes
    </p>
</div>
""", unsafe_allow_html=True)