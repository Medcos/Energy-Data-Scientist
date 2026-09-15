# ⚡ Energy Data Scientist — Portfolio

[🇫🇷 Version française](README.fr.md)

**Medico Diomande** — Electromechanical Engineer (10+ years on World Bank / AFD / AfDB-funded electrification projects) turned Data Scientist & Technical Architect. Positioned as an **Energy Data Scientist & Infrastructure Intelligence Specialist**: applied machine learning and automation, grounded in real power-grid field engineering.

## Why this portfolio

Ten years running electrification worksites showed what actually breaks in the field: unreliable connectivity, progress reports that don't match reality, materials reconciliation that has to survive renamed reference data. Every project below turns one of those real operational problems into a working, documented, and — where possible — publicly deployed system.

All projects are inspired by real donor-financed electrification programs in West Africa (SBEE Bénin, 55 localities across 4 departments). Real aggregate geography and quantities are kept for credibility; locality names, GPS coordinates, and any client-identifying detail are pseudonymized or synthetic. Each project's own **Confidentiality** section states exactly what is real vs. anonymized, and every public delivery is checked with a leak-detection grep beforehand.

## Track 1 — Data Science & Predictive Analytics

A progression of three projects of increasing complexity, sharing one throughline: baselines before complexity, SHAP interpretability throughout, and business-unit metrics instead of raw ML scores.

| # | Project | What it does | Key result | Live demo |
|---|---|---|---|---|
| 1 | [Predictive Maintenance for Industrial Machines](./predictive-maintenance-electrical-grid) | Two-level classification: will a machine fail, and which of 5 modes is the root cause | AUC-ROC 0.98 · F1 up to 1.00 on root-cause | [Open →](https://maintenance-predictive-medico.streamlit.app/) |
| 2 | [Predictive Rollout & Supply Forecast](./predictive-avancement-projet) | 3-model suite forecasting material needs, progress, and delay risk on a rural electrification rollout | 93% delay-risk detection · ~2-3× lower forecast error than no model | [Open →](https://energy-data-scientist-mdz2vr9ozqxhey3t5nprkh.streamlit.app) |
| 3 | [Jobsite Relaunch Agent](./smart-jobsite-relaunch-agent) | LangGraph + n8n agent that reads weekly field reports, resolves locality names, and classifies stalled worksites automatically | 9-node stateful agent · persisted week-over-week history | [Open →](https://energy-data-scientist-kbqch4dr9lgc3aypv3kmgx.streamlit.app/) |

## Track 2 — Platform Engineering

| Project | What it does |
|---|---|
| [ElecTrack Pro](./electrack-pro) | Multi-tenant SaaS (AppSheet + Google Sheets + Apps Script) for field-intervention management on utility infrastructure — in production across 55 localities / 4 departments |

## Skills demonstrated across this portfolio

- → **Domain-driven feature engineering** — physical laws (e.g. `power_kw = T × ω`) and field operating knowledge turned into model features and data corrections a pure data-science profile wouldn't derive
- → **ML methodology discipline** — baselines kept unless a more complex model proves its worth on evidence (Gradient Boosting retained in only 1 of 4 comparable cases in the forecast project); SHAP interpretability on every model
- → **Production concerns, not notebooks** — every Data Science project ships a deployed Streamlit dashboard or a working orchestrated agent, not just a `.ipynb`
- → **Data confidentiality by design** — a documented pseudonymization protocol (real aggregate geography, synthetic identifiers, retrained models with no leaking encoders) applied consistently and grep-verified before every public commit
- → **Full-stack delivery** — from no-code SaaS platforms (AppSheet/Apps Script) to Python ML pipelines to LangGraph agents orchestrated with n8n and FastAPI

## About me

Electromechanical engineer with 10+ years of field experience on international donor-financed electrification programs (World Bank, AFD, African Development Bank). Each project in this portfolio pairs that field experience with applied ML/data-science and automation work — see each project's own "Why My Background Matters" section for specifics.

**Certifications**

- → RNCP Level 7 Data Science (CentraleSupélec / OpenClassrooms)
- → *Building AI Agents and Agentic Workflows* — IBM / Coursera specialization (LangGraph, CrewAI, AutoGen, BeeAI), Aug 2026 — [verify](https://coursera.org/verify/specialization/ENTIGWJF6KCS). Direct grounding for the [Jobsite Relaunch Agent](./smart-jobsite-relaunch-agent) project above.

Available for remote data science, ML, and infrastructure-automation consulting missions.

Medico Diomande · dmedcos@yahoo.fr · [linkedin.com/in/medico-diomande-data](https://linkedin.com/in/medico-diomande-data)
