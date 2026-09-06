"""
api/main.py — API FastAPI exposant l'agent LangGraph (Jour 5, spec section
9 / plan Jour 4-5).

Trois endpoints :
  - POST /analyser-localite            : chemin direct (localité déjà
    connue), utilisé par la page "Simulateur de relance" de l'app
    Streamlit — l'utilisateur choisit une localité + une semaine, pas de
    texte à parser.
  - POST /traiter-rapport-hebdomadaire : chemin email, fan-out sur TOUTES
    les localités mentionnées (corrige le Jour 2/4, qui ne traitaient que
    la première extraite d'un email même quand sample_report_email.txt en
    liste 5) ; utilisé par le workflow n8n (Jour 4, mis à jour au Jour 5
    pour ce nouveau nom et cette nouvelle forme de réponse — remplace
    l'ancien /relancer, qui ne gérait qu'une seule localité par appel).
  - GET  /historique/{id_localite}     : lecture seule de l'historique de
    cadence persisté par le Checkpointer, pour la page "Historique de
    cadence" de l'app Streamlit. Pas dans le texte du plan Jour 5, mais
    nécessaire techniquement — cette page ne peut pas invoquer le graphe
    juste pour lire un historique déjà calculé les semaines précédentes.

La logique d'invocation (bootstrap vs continuation de thread — cf. la règle
critique documentée dans agent/orchestration.py — et le fan-out
multi-localités) vit dans agent/orchestration.py, testée indépendamment de
FastAPI (tests/test_orchestration.py).

Lancement local (hors Docker), depuis la racine du repo :
    uvicorn api.main:app --reload --port 8000
"""

from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import orchestration
from agent.graph import compile_graph

app = FastAPI(title="Agent de relance de chantier — API (démo)")

# Une seule connexion/checkpointer réutilisée entre les requêtes — ne pas
# rappeler compile_graph() à chaque appel (cf. docstring de graph.py).
_graph = compile_graph()


class LocaliteResultat(BaseModel):
    id_localite: str | None = None
    nom_localite_brut: str | None = None
    statut_alerte: str = "a_verifier"
    section_rapport: str | None = None
    candidats_resolution: list[str] = []
    erreurs: list[str] = []


class AnalyserLocaliteRequest(BaseModel):
    id_localite: str
    date_du_jour: date


class RapportHebdomadaireRequest(BaseModel):
    email_brut: str
    date_du_jour: date


class RapportHebdomadaireResponse(BaseModel):
    resultats: list[LocaliteResultat]


class HistoriqueEntree(BaseModel):
    semaine: str
    reste_a_faire: dict[str, float]


class HistoriqueResponse(BaseModel):
    id_localite: str
    historique: list[HistoriqueEntree]


def _vers_resultat(brut: dict) -> LocaliteResultat:
    return LocaliteResultat(
        id_localite=brut.get("id_localite"),
        nom_localite_brut=brut.get("nom_localite_brut"),
        statut_alerte=brut.get("statut_alerte", "a_verifier"),
        section_rapport=brut.get("section_rapport"),
        candidats_resolution=brut.get("candidats_resolution", []),
        erreurs=brut.get("erreurs", []),
    )


@app.post("/analyser-localite", response_model=LocaliteResultat)
def analyser_localite(payload: AnalyserLocaliteRequest) -> LocaliteResultat:
    resultat = orchestration.analyser_localite(_graph, payload.id_localite, payload.date_du_jour)
    return _vers_resultat(resultat)


@app.post("/traiter-rapport-hebdomadaire", response_model=RapportHebdomadaireResponse)
def traiter_rapport_hebdomadaire(payload: RapportHebdomadaireRequest) -> RapportHebdomadaireResponse:
    resultats = orchestration.traiter_rapport_hebdomadaire(
        _graph, payload.email_brut, payload.date_du_jour
    )
    return RapportHebdomadaireResponse(resultats=[_vers_resultat(r) for r in resultats])


@app.get("/historique/{id_localite}", response_model=HistoriqueResponse)
def historique(id_localite: str) -> HistoriqueResponse:
    config = {"configurable": {"thread_id": id_localite}}
    etat = _graph.get_state(config).values
    if not etat:
        raise HTTPException(status_code=404, detail=f"Aucun historique pour '{id_localite}'.")
    return HistoriqueResponse(
        id_localite=id_localite,
        historique=[
            HistoriqueEntree(semaine=h.semaine, reste_a_faire=h.reste_a_faire)
            for h in etat.get("historique_cadence", [])
        ],
    )


@app.get("/sante")
def sante():
    return {"ok": True}
