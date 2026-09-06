"""
orchestration.py — Couche d'invocation du graphe pour l'API (Jour 5).

Isole la logique d'appel du graphe (bootstrap vs continuation de thread,
fan-out multi-localités) hors de api/main.py, pour qu'elle reste testable
sans dépendance à FastAPI.

Règle critique établie au Jour 3/4 et rappelée ici : passer un AgentState()
complet à graph.invoke() sur un thread_id déjà existant ÉCRASE le
checkpoint (réinitialise historique_cadence, etc.). Il ne faut passer qu'un
dict PARTIEL pour continuer un thread existant ; seul le tout premier appel
sur un thread_id doit fournir un AgentState complet pour l'amorcer.
"""

from __future__ import annotations

from datetime import date

from . import data_access
from .llm_extraction import extraire_localites
from .state import AgentState


def _invoquer(graph, thread_id: str, champs: dict) -> dict:
    """Invoque le graphe sur thread_id, en respectant la règle bootstrap
    (AgentState complet) vs continuation (dict partiel) ci-dessus."""
    config = {"configurable": {"thread_id": thread_id}}
    etat_existant = graph.get_state(config).values
    entree = champs if etat_existant else AgentState(thread_id=thread_id, **champs)
    return graph.invoke(entree, config=config)


def analyser_localite(graph, id_localite: str, date_du_jour: date) -> dict:
    """Chemin direct (endpoint /analyser-localite, Jour 5) : la localité est
    déjà connue (choisie dans l'UI Streamlit), pas de texte à parser.
    jours_inactivite_declares est explicitement remis à None à chaque appel
    — sans ça, une valeur déclarée par un email traité une semaine
    précédente sur ce même thread_id resterait dans l'état persisté et
    fausserait la vérification croisée de lire_derniere_activite pour cette
    requête-ci, qui n'a pas d'email et donc rien à déclarer."""
    return _invoquer(
        graph,
        thread_id=id_localite,
        champs={
            "id_localite": id_localite,
            "date_du_jour": date_du_jour,
            "jours_inactivite_declares": None,
        },
    )


def traiter_rapport_hebdomadaire(graph, email_brut: str, date_du_jour: date) -> list[dict]:
    """Chemin multi-localités (endpoint /traiter-rapport-hebdomadaire, Jour
    5) : parse l'email UNE fois, résout chaque localité mentionnée, puis
    invoque le graphe une fois par localité résolue (thread_id =
    id_localite, convention établie depuis le Jour 3 — chaque localité a
    son propre historique persisté, on ne peut pas les mélanger dans un seul
    thread). Une localité non résolvable est signalée directement ici
    (statut a_verifier), sans invoquer le graphe : sans id_localite, il n'y
    a pas de thread_id stable sous lequel checkpointer un résultat.

    Avant le Jour 5, extraction_localites (le nœud du graphe) ne gardait que
    la première localité extraite d'un email — même quand
    sample_report_email.txt en liste 5. Cette fonction corrige ce point en
    traitant réellement toutes les localités extraites."""
    localites = extraire_localites(email_brut)
    if not localites:
        return [
            {
                "id_localite": None,
                "nom_localite_brut": None,
                "statut_alerte": "a_verifier",
                "section_rapport": None,
                "candidats_resolution": [],
                "erreurs": ["Aucune localité extraite du texte fourni."],
            }
        ]

    resultats = []
    for loc in localites:
        nom_brut = loc.get("nom_localite_brut", "")
        id_localite, candidats = data_access.resoudre_localite(nom_brut, loc.get("departement"))

        if id_localite is None:
            resultats.append(
                {
                    "id_localite": None,
                    "nom_localite_brut": nom_brut,
                    "statut_alerte": "a_verifier",
                    "section_rapport": None,
                    "candidats_resolution": candidats,
                    "erreurs": [
                        f"Résolution ambiguë ou impossible pour '{nom_brut}' — "
                        f"candidats : {candidats}"
                    ],
                }
            )
            continue

        resultat = _invoquer(
            graph,
            thread_id=id_localite,
            champs={
                "id_localite": id_localite,
                "date_du_jour": date_du_jour,
                "jours_inactivite_declares": loc.get("jours_inactivite_declares"),
            },
        )
        resultat.setdefault("nom_localite_brut", nom_brut)
        resultats.append(resultat)

    return resultats
