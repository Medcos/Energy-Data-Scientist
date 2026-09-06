"""
graph.py — Construction du StateGraph (spec technique section 6.1).

Enchaînement :
    START -> route_depart
        -> [a_extraire]      -> extraction_localites -> resoudre_localite
                                  -> [résolu]     -> lire_reste_a_faire -> ...
                                  -> [non résolu] -> END (statut a_verifier)
        -> [localite_connue] -> lire_reste_a_faire -> lire_derniere_activite
                                  -> lire_deadline_planning -> calculer_cadence
                                  -> classer_statut -> mettre_a_jour_historique
                                  -> generer_section_rapport -> END

route_depart (ajouté Jour 5) : si state.id_localite est déjà renseigné à
l'entrée du graphe, on saute extraction_localites et resoudre_localite —
c'est le chemin emprunté par l'endpoint direct /analyser-localite (Jour 5,
l'utilisateur choisit une localité existante, pas de texte à parser) ET par
le fan-out multi-localités de /traiter-rapport-hebdomadaire, qui résout
chaque localité extraite d'un email AVANT d'invoquer le graphe une fois par
localité (voir agent/orchestration.py) — nécessaire pour que chaque
invocation utilise le bon thread_id (= id_localite) dès le départ.
Sans id_localite pré-rempli, le chemin historique du Jour 2 (email_brut ->
extraction_localites -> resoudre_localite) reste inchangé.

mettre_a_jour_historique est intercalé après classer_statut (qui lit
l'historique existant) et avant generer_section_rapport, pour que la
nouvelle entrée d'historique soit écrite dans l'état avant la fin du run
(section 6.2 du résumé de reprise, Jour 3).

Checkpointer : SqliteSaver à partir du Jour 3 (persistance inter-semaines,
thread_id = code localité), fichier versionné dans le repo
(agent/checkpoints.sqlite — chemin relatif au module, même convention que
DATA_DIR dans data_access.py). compile_graph() ouvre une connexion dédiée à
chaque appel ; les scripts appelants (run_single_test.py, simulate_weeks.py)
appellent compile_graph() UNE FOIS par exécution puis invoquent le graphe
compilé en boucle — ne pas rappeler compile_graph() à chaque invoke().
MemorySaver (Jour 2, non persistant) reste utilisable en passant
checkpointer=MemorySaver() explicitement, utile pour des tests isolés qui ne
doivent pas écrire dans la base versionnée.
"""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import AgentState

# Fichier SQLite versionné dans le repo (cf. section 6.2.3 du résumé de
# reprise) — contient l'historique de cadence inter-semaines de chaque
# localité (thread_id). Pas dans data/ : ce n'est pas une donnée source,
# c'est l'état persisté de l'agent lui-même.
CHECKPOINT_DB_PATH = Path(__file__).parent / "checkpoints.sqlite"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("extraction_localites", nodes.extraction_localites)
    g.add_node("resoudre_localite", nodes.resoudre_localite)
    g.add_node("lire_reste_a_faire", nodes.lire_reste_a_faire)
    g.add_node("lire_derniere_activite", nodes.lire_derniere_activite)
    g.add_node("lire_deadline_planning", nodes.lire_deadline_planning)
    g.add_node("calculer_cadence", nodes.calculer_cadence)
    g.add_node("classer_statut", nodes.classer_statut)
    g.add_node("mettre_a_jour_historique", nodes.mettre_a_jour_historique)
    g.add_node("generer_section_rapport", nodes.generer_section_rapport)

    g.add_conditional_edges(
        START,
        nodes.route_depart,
        {"a_extraire": "extraction_localites", "localite_connue": "lire_reste_a_faire"},
    )
    g.add_edge("extraction_localites", "resoudre_localite")

    g.add_conditional_edges(
        "resoudre_localite",
        nodes.route_apres_resolution,
        {"resolu": "lire_reste_a_faire", "non_resolu": END},
    )

    g.add_edge("lire_reste_a_faire", "lire_derniere_activite")
    g.add_edge("lire_derniere_activite", "lire_deadline_planning")
    g.add_edge("lire_deadline_planning", "calculer_cadence")
    g.add_edge("calculer_cadence", "classer_statut")
    g.add_edge("classer_statut", "mettre_a_jour_historique")
    g.add_edge("mettre_a_jour_historique", "generer_section_rapport")
    g.add_edge("generer_section_rapport", END)

    return g


def _default_checkpointer() -> SqliteSaver:
    """Connexion SQLite dédiée vers le fichier versionné du repo.
    check_same_thread=False : nécessaire pour l'API FastAPI (Jour 5), qui
    pourra servir des requêtes sur des threads différents de celui où la
    connexion a été ouverte."""
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
    # historique_cadence contient des HistoriqueCadenceEntry (type Pydantic
    # custom). Le sérialiseur msgpack par défaut de LangGraph accepte ce
    # type mais avertit qu'il sera bloqué dans une future version
    # (LANGGRAPH_STRICT_MSGPACK) sauf enregistrement explicite — on
    # l'enregistre ici pour ne pas perdre l'historique au prochain upgrade
    # de langgraph (leçon RobustScaler du projet précédent, section 7 du
    # résumé de reprise : toujours anticiper l'incompatibilité de version).
    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[("agent.state", "HistoriqueCadenceEntry")]
    )
    saver = SqliteSaver(conn, serde=serde)
    saver.setup()
    return saver


def compile_graph(checkpointer=None):
    g = build_graph()
    return g.compile(checkpointer=checkpointer or _default_checkpointer())
