# ⚡ Predictive Rollout & Supply Forecast

[🇫🇷 Version française](README.fr.md)

`Python` `pandas` `scikit-learn` `SHAP` `Streamlit`

📂 **Data Science & Predictive Analytics** — Project 2/3 · [Portfolio home](../README.md) · [← Predictive Maintenance](../predictive-maintenance-electrical-grid) · Next: [Jobsite Relaunch Agent →](../smart-jobsite-relaunch-agent)

## Overview

Predictive modeling of construction progress and material supply on a rural electrification project (SBEE Benin, West Africa, internationally financed) — 55 localities, 4 departments, December 2026 deadline.

Second installment of the Data Science & Predictive Analytics track, following [Predictive Maintenance for Industrial Machines](../predictive-maintenance-electrical-grid). This project turns a real construction-tracking system into a predictive steering tool, with three lightweight models sharing a single data pipeline plus a bonus segmentation:

- **A. Resources** — remaining material to deliver, by locality × task (regression)
- **B. Progress** — advancement projection at +2 / +4 weeks, by department (time series)
- **C. Delay risk** — localities lagging behind their peers (classification)
- **D. Segmentation** — 4 locality profiles, with no pre-existing label (clustering, bonus)

Built by Medico Diomande — Electromechanical Engineer (10 years field experience on World Bank / AFD / AfDB electrification projects) + Data Scientist. Ten years scoping and tracking electrification rollouts directly informed which targets were worth modeling and which raw-data anomalies were data-entry errors rather than signal.

## Business Impact

- → 7 units / 1,376 meters average error on material forecasting (Model A), vs. 20 units / 2,637 m with no model — cuts over-ordering and last-minute shortages
- → 4.3 percentage points of error at 4 weeks on progress projection (Model B), vs. 7.3 points if nothing is projected forward — gives planners a reliable early-warning horizon
- → 93% of at-risk localities correctly flagged (Model C, 15/55 localities) — turns a reactive follow-up process into a proactive one
- → An unsupervised clustering (Model D) isolated a locality group that matches **exactly** a group identified through a completely independent method — a cross-validation signal that owed nothing to chance

Full detail in [`reports/synthese_resultats_publique.md`](reports/synthese_resultats_publique.md) (French; key figures summarized above).

## 🔒 Confidentiality note

This repository contains **pseudonymized** data from a real project financed by an international donor. Locality and commune names are replaced with generic identifiers (`Localite_001`…`Localite_055`, `Commune_A`…`Commune_I`); only departments (a public administrative division of Benin) are left in clear. The models provided (`models/public/`) were **retrained on this pseudonymized data** — no categorical encoder in this repository contains a real name. Full detail on this confidentiality policy (decision D5) is documented in [`reports/cadrage_jour1.md`](reports/cadrage_jour1.md) (French).

*(The detailed analysis notebooks, which use real data, remain for internal use only and are not published — see repository structure below.)*

## Demo

**🔗 Live app: https://energy-data-scientist-mdz2vr9ozqxhey3t5nprkh.streamlit.app**

```bash
pip install -r requirements.txt
PUBLIC_MODE=1 streamlit run app/streamlit_app.py
```

3-page dashboard: Resources, Progress, Risks.

## Repository structure

```
predictive-avancement-projet/
├── README.md                     # English version (default)
├── README.fr.md                  # French version
├── requirements.txt
├── app/
│   └── streamlit_app.py          # 3-page dashboard (public mode via PUBLIC_MODE=1)
├── src/
│   ├── anonymize.py              # PII anonymization + locality/commune pseudonymization
│   └── features.py               # pivot table construction
├── data/
│   └── public/                   # pseudonymized data only
├── models/
│   └── public/                   # models retrained on pseudonymized data
└── reports/
    ├── synthese_resultats_publique.md
    └── figures/
```

## Methodology

A 6-step approach, detailed in `reports/synthese_resultats_publique.md`: data scoping and audit, EDA with detection and correction of two real data-entry anomalies, simple baselines before complex models (Ridge, linear trend, logistic regression), a measured comparison against Gradient Boosting tested on every model (kept in only 1 case out of 4 — simplicity won elsewhere, on evidence rather than by default), systematic SHAP interpretability, and finally a dashboard plus a bonus clustering segmentation.

**Acknowledged limitation:** small sample size (55 localities, 20 weeks of tracking). The goal is to demonstrate a rigorous methodology — baselines, temporal validation, business-unit metrics, interpretability — applied to a real case, not to reach production-grade accuracy.

## Tech stack

Python · pandas · scikit-learn (Ridge, Gradient Boosting, logistic regression, K-Means) · SHAP · Streamlit · matplotlib.

## Why My Background Matters

The 6-step methodology is standard data science practice. What isn't standard is knowing, from ten years running electrification rollouts, which numbers in a construction-tracking export are real signal and which are data-entry artifacts — the two anomalies caught and corrected during EDA came from that field experience, not from a generic outlier-detection rule. The same background shaped Model C's target: the original label was degenerate (100% positive), and it was replaced with relative underperformance vs. department quartile — a metric that matches how a mission supervisor actually judges "which localities need attention."

---

Author: Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Available for remote missions
