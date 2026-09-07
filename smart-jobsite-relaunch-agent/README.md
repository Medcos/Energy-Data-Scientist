# ⚡ Jobsite Relaunch Agent — n8n + LangGraph Demo

[🇫🇷 Version française](README.fr.md)

Portfolio demonstration of an automation agent derived from a real electrification-jobsite
tracking project (data, locality names, and deadlines are fictional — see
[Confidentiality](#confidentiality) below).

**[▶ Live demo](https://energy-data-scientist-kbqch4dr9lgc3aypv3kmgx.streamlit.app/)** —
Streamlit app deployed on Streamlit Community Cloud.

## The use case

Every week, a site supervisor sends a report listing localities with no recorded activity
for more than 3 months. For each one, the agent:

1. extracts and identifies the locality (typo-tolerant name resolution, including
   detection of ambiguity between two similar names);
2. compares the declared inactivity against the inactivity measured in the field-tracking
   system, and flags any suspicious discrepancy;
3. computes the execution pace required to meet the remaining planning deadlines;
4. classifies the locality (normal / delayed / critical), taking its trend over previous
   weeks into account thanks to a history persisted from one week to the next;
5. generates the corresponding report section.

## Architecture

### Pipeline (n8n → API → agent)

```mermaid
flowchart LR
    subgraph n8n["n8n — trigger + I/O"]
        A[Schedule Trigger<br/>Monday 8am] --> B[Read simulated email]
        B --> C[Build the request]
    end

    subgraph api["FastAPI"]
        D["/traiter-rapport-hebdomadaire/<br/>(multi-locality fan-out)"]
        E["/analyser-localite/"]
        F["/historique/{id}/"]
    end

    subgraph agent["LangGraph agent"]
        G[StateGraph, 9 nodes]
        H[(checkpoints.sqlite<br/>thread_id = locality)]
        G <--> H
    end

    C --> D
    D -->|1 invocation<br/>per locality| G
    E --> G

    D --> I[Build the file]
    I --> J[Write the report]

    K["Streamlit app<br/>(calls the agent<br/>directly in Python)"] -.-> G
    K -.-> F
```

### LangGraph graph (agent/)

```mermaid
flowchart TD
    START((START)) --> ROUTE{route_depart}
    ROUTE -->|locality already<br/>known| LRF[lire_reste_a_faire]
    ROUTE -->|to extract<br/>from an email| EXTRACT[extraction_localites]
    EXTRACT --> RESOLVE{resoudre_localite}
    RESOLVE -->|resolved| LRF
    RESOLVE -->|unresolved| ENDA([END — a_verifier])
    LRF --> LDA[lire_derniere_activite]
    LDA --> LDP[lire_deadline_planning]
    LDP --> CC[calculer_cadence]
    CC --> CS[classer_statut]
    CS --> MAJ[mettre_a_jour_historique]
    MAJ --> GEN[generer_section_rapport]
    GEN --> ENDB([END])
```

`route_depart` (Day 5) lets the same graph serve two entry points: a locality that is
already known (the `/analyser-localite` endpoint, or each step of the
`/traiter-rapport-hebdomadaire` fan-out) jumps straight to `lire_reste_a_faire`; a raw
email still goes through the historical path (`extraction_localites` →
`resoudre_localite`).

### Folders

- **`agent/`** — the LangGraph graph: extraction, name resolution (fuzzy matching with an
  ambiguity margin), reading field data, pace calculation, classification, persisted
  history (`agent/checkpoints.sqlite`, versioned).
- **`api/`** — FastAPI exposing the agent over HTTP (see `api/main.py` for the 3
  endpoints).
- **`app/`** — 3-page Streamlit app (Home, Relaunch Simulator, Pace History). Calls the
  agent directly in Python rather than through the API — see `app/agent_client.py` for
  why.
- **`n8n/`** — n8n workflow (`workflow.json`) orchestrating the weekly trigger; see
  `n8n/README.md` for points of attention (file access, validation).
- **`data/`** — synthetic dataset (55 localities, 4 departments of Benin, 11 HV/LV work
  tasks).
- **`tests/`** — pytest suite (agent, API, Streamlit app).
- **`docker-compose.yml`** — runs the API and n8n together locally.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -q          # 41 tests

# API
uvicorn api.main:app --reload --port 8000

# Streamlit app (in another terminal)
streamlit run app/Accueil.py

# Full API + n8n stack (requires Docker — see n8n/README.md for details)
docker compose up --build
```

## Deployment (Streamlit Community Cloud)

The app is deployed and working: **https://energy-data-scientist-kbqch4dr9lgc3aypv3kmgx.streamlit.app/**

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing to this
   repo, with **Main file path: `app/Accueil.py`**.
3. Dependencies are detected automatically — see the point of attention below if this
   repo is itself a subfolder of a monorepo.

The deployed app works standalone (it calls the agent directly in Python, not through the
API — see `app/agent_client.py`): no other service needs to be deployed for the public
demo. The FastAPI API and the n8n workflow remain demonstrated independently, either
locally (`docker compose up`) or via the demo GIF (`n8n_demo.gif`).

### Point of attention — requirements.txt location in a monorepo

Community Cloud looks for a dependency file (1) in the **entrypoint's own directory**
(here `app/`, since Main file path = `app/Accueil.py`), then (2) at the **root of the
GitHub repo** — never in an intermediate folder. If this project is deployed as-is (its
own dedicated repo), the `requirements.txt` at its root IS the repo root: no problem. If
instead it is added as a subfolder of an existing monorepo (e.g.
`Medcos/Energy-Data-Scientist/smart-jobsite-relaunch-agent/`), neither the monorepo root
nor the `app/` folder naturally contains this file — Community Cloud then falls back to
the monorepo's own `requirements.txt` (meant for a *different* project), causing a
`ModuleNotFoundError` on `rapidfuzz`/`plotly` (absent from that file). Hence
**`app/requirements.txt`**, a scoped copy placed in the entrypoint's own folder — found
first, regardless of how deep the subfolder is. Keep it in sync with the root
`requirements.txt` if versions change.

### Point of attention — "actionable" remaining work

The synthetic dataset contains task/locality pairs where cumulative completed work
exceeds the planned quantity (over-delivery, e.g. `TASK_Cable_BT` in several localities),
producing a negative `reste_a_faire`. `agent/nodes.reste_actionnable()` filters these out
(reste > 0) before any display or historical-average computation — it is the single
definition of "actionable remaining work" used throughout the project (text report,
history page, status classification).

## Confidentiality

**Real**: the country (Benin), the 4 departments, and the aggregated work quantities per
task.

**Fictional**: commune and locality names, GPS coordinates, exact intervention schedule,
precise planning deadlines, original project/client name.

All generated data is checked with a leak-detection grep before every delivery.

## Status

Days 1 to 6 of the implementation plan are complete (data, agent, checkpointer + tests,
n8n integration, API + Streamlit app, Streamlit Community Cloud deployment validated in
real conditions, README + diagrams). Remaining: publication and portfolio card (Day 7).
