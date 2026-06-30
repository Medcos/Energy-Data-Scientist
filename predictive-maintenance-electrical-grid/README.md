⚡ Predictive Maintenance for Industrial Machines

[🇫🇷 Version française](README.fr.md)

`Python 3.11+` `scikit-learn 1.6` `XGBoost 2.0` `Streamlit App`

## Overview

Two-level machine learning system to predict equipment failures on industrial machines (temperature, rotational speed, torque, tool wear) and identify the root cause among 5 failure modes. Level 1 (binary classification) achieves **AUC-ROC of 0.98** and **F1 = 0.88** on failure detection. Level 2 (multi-label classification) identifies the specific failure mode (Heat Dissipation, Power, Overstrain, Tool Wear, Random) with **F1 up to 1.00** depending on the mode.

Built by Medico Diomande — Electromechanical Engineer (10 years field experience on World Bank / AFD / AfDB electrification projects) + Data Scientist. The domain expertise directly informs the feature engineering (power, thermal stress derived from physical laws).

## Business Impact

- → Two-stage decision system: "Will it fail?" then "Why will it fail?" for targeted maintenance action
- → Physics-grounded feature engineering validated by SHAP analysis (power_kw alone explains 100% of Power Failure signal)
- → Decision thresholds optimized per failure mode instead of generic 0.5 cutoff, improving F1 by up to +15%
- → Interactive Streamlit dashboard for non-technical stakeholders — live demo, no notebook required

## Key Features

- → Domain-specific feature engineering (`temp_diff`, `power_kw = T × ω`, `thermal_stress`)
- → SMOTE vs class-weighting comparison — class-weighting retained after empirical testing (SMOTE degraded precision on tree-based models)
- → 3 models compared per level: Logistic Regression, Random Forest, Gradient Boosting
- → Per-label decision threshold optimization (Precision-Recall curve, F1 maximization)
- → SHAP interpretability for both levels, validating physical coherence of learned mechanisms
- → Live Streamlit dashboard: [Streamlit Cloud URL]

## Results — Level 1 (Failure Prediction)

| Model | Precision | Recall | F1 | AUC-ROC |
|---|---|---|---|---|
| Logistic Regression | 0.18 | 0.85 | 0.30 | 0.93 |
| Random Forest | 0.94 | 0.66 | 0.78 | 0.97 |
| **Gradient Boosting ★** | **0.93** | **0.82** | **0.88** | **0.98** |

## Results — Level 2 (Failure Mode Identification)

| Mode | Cause | F1-score | Threshold |
|---|---|---|---|
| HDF | Heat Dissipation Failure | 0.98 | 0.785 |
| PWF | Power Failure | 1.00 | 0.9998 |
| OSF | Overstrain Failure | 0.94 | 0.206 |
| TWF | Tool Wear Failure | heuristic rule | usage-based |
| RNF | Random Failure | not predictable | — |

## Usage

```
git clone https://github.com/Medcos/Energy-Data-Scientist/tree/main/predictive-maintenance-electrical-grid
pip install -r requirements.txt
streamlit run app.py
```

## Why my background matters

The `power_kw` feature was not in the original dataset. It was derived from electromechanical engineering knowledge: mechanical power computed from torque and rotational speed (P = T × ω), a fundamental relationship in rotating machinery diagnostics. SHAP analysis confirmed this single feature captures 100% of the Power Failure signal — domain-driven feature engineering of this kind typically outperforms purely data-driven approaches on industrial datasets.

Similarly, `temp_diff` (process-to-ambient temperature differential) was identified as the third most important global predictor, directly reflecting heat dissipation efficiency — a concept familiar from HTA/BTA electrical network operations.

---

Author: Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Available for remote missions