"""
test_route_depart.py — Régression Jour 5 : le nouveau routage conditionnel
au démarrage du graphe (route_depart) ne doit casser ni le chemin email
(Jour 2, inchangé) ni introduire de comportement incorrect sur le nouveau
chemin "localité déjà connue" (Jour 5, /analyser-localite et le fan-out de
/traiter-rapport-hebdomadaire).

Utilise MemorySaver (pas le checkpoints.sqlite versionné) pour ne pas
polluer la base livrée avec des threads de test.
"""

from datetime import date

from langgraph.checkpoint.memory import MemorySaver

from agent import nodes
from agent.graph import compile_graph
from agent.state import AgentState

REFERENCE_DATE = date(2026, 8, 31)


def test_route_depart_id_localite_connu():
    assert nodes.route_depart(AgentState(id_localite="Site_09")) == "localite_connue"


def test_route_depart_email_sans_id_localite():
    assert nodes.route_depart(AgentState(email_brut="...")) == "a_extraire"


def test_graphe_chemin_localite_connue_saute_extraction_et_resolution():
    # id_localite pré-rempli, email_brut vide -> doit produire un rapport
    # sans jamais passer par extraction_localites/resoudre_localite (donc
    # sans dépendre du contenu d'un email).
    graph = compile_graph(checkpointer=MemorySaver())
    etat_initial = AgentState(
        thread_id="test_route_localite_connue",
        id_localite="Site_09",
        date_du_jour=REFERENCE_DATE,
    )
    config = {"configurable": {"thread_id": etat_initial.thread_id}}
    resultat = graph.invoke(etat_initial, config=config)

    assert resultat["id_localite"] == "Site_09"
    # nom_localite_brut n'a jamais été renseigné : preuve qu'extraction_localites
    # n'a pas tourné (sinon il serait resté "" par défaut de toute façon côté
    # état initial — la preuve réelle est plutôt l'absence d'erreur liée à
    # une extraction ratée sur un email vide).
    assert resultat["statut_alerte"] in {"normal", "retard", "critique"}
    assert resultat["section_rapport"] is not None
    assert "Aucune localité extraite" not in " ".join(resultat["erreurs"])


def test_graphe_chemin_email_inchange():
    # Non-régression : le chemin historique (email -> extraction ->
    # résolution) continue de fonctionner tel quel quand id_localite n'est
    # pas pré-rempli.
    graph = compile_graph(checkpointer=MemorySaver())
    etat_initial = AgentState(
        thread_id="test_route_chemin_email",
        email_brut="  - Site_09 (Commune_A, ALIBORI)\n",
        date_du_jour=REFERENCE_DATE,
    )
    config = {"configurable": {"thread_id": etat_initial.thread_id}}
    resultat = graph.invoke(etat_initial, config=config)

    assert resultat["id_localite"] == "Site_09"
    assert resultat["nom_localite_brut"] == "Site_09"
    assert resultat["section_rapport"] is not None
