"""
test_orchestration.py — Couche d'invocation du graphe pour l'API (Jour 5) :
analyser_localite (chemin direct) et traiter_rapport_hebdomadaire (fan-out
multi-localités, corrige le Jour 2 qui ne gardait que la première localité
extraite d'un email).

Utilise MemorySaver (pas checkpoints.sqlite) pour ne pas polluer la base
versionnée avec des threads de test.
"""

from datetime import date
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from agent import data_access, orchestration
from agent.graph import compile_graph

DATA_DIR = Path(__file__).parent.parent / "data"
REFERENCE_DATE = date(2026, 8, 31)


def _graphe():
    return compile_graph(checkpointer=MemorySaver())


def test_analyser_localite_bootstrap():
    graph = _graphe()
    resultat = orchestration.analyser_localite(graph, "Site_09", REFERENCE_DATE)
    assert resultat["id_localite"] == "Site_09"
    assert resultat["section_rapport"] is not None
    assert len(resultat["historique_cadence"]) == 1


def test_analyser_localite_continue_le_meme_thread_sans_ecraser_historique():
    # Deux appels successifs sur la même localité, à deux dates différentes
    # -> l'historique doit s'accumuler (2 entrées), pas repartir de zéro.
    # C'est la règle bootstrap-vs-partiel établie au Jour 3/4 : un
    # AgentState() complet sur un thread existant écraserait le checkpoint.
    graph = _graphe()
    orchestration.analyser_localite(graph, "Site_09", date(2026, 8, 24))
    resultat = orchestration.analyser_localite(graph, "Site_09", date(2026, 8, 31))
    assert len(resultat["historique_cadence"]) == 2


def test_analyser_localite_ne_reporte_pas_un_jours_inactivite_declares_perime():
    # Un précédent appel via traiter_rapport_hebdomadaire (avec un email)
    # aurait pu laisser jours_inactivite_declares dans l'état persisté ;
    # analyser_localite doit le remettre à None (pas d'email ici, rien à
    # déclarer) pour ne pas fausser la vérification croisée de la semaine.
    graph = _graphe()
    orchestration._invoquer(
        graph,
        thread_id="Site_09",
        champs={
            "id_localite": "Site_09",
            "date_du_jour": date(2026, 8, 24),
            "jours_inactivite_declares": 9999,  # volontairement absurde
        },
    )
    resultat = orchestration.analyser_localite(graph, "Site_09", date(2026, 8, 31))
    assert not any("Écart d'inactivité" in e for e in resultat["erreurs"])


def test_traiter_rapport_hebdomadaire_traite_toutes_les_localites_de_l_email():
    # sample_report_email.txt liste 5 localités (les 5 gelées) — avant le
    # correctif Jour 5, seule la première (Site_09) aurait été traitée.
    graph = _graphe()
    email = (DATA_DIR / "sample_report_email.txt").read_text(encoding="utf-8")
    resultats = orchestration.traiter_rapport_hebdomadaire(graph, email, REFERENCE_DATE)

    ids_traites = {r["id_localite"] for r in resultats}
    assert ids_traites == {"Site_09", "Site_23", "Site_35", "Site_39", "Site_45"}
    assert all(r["section_rapport"] is not None for r in resultats)


def test_traiter_rapport_hebdomadaire_localite_non_resolue_signalee_sans_planter():
    graph = _graphe()
    email = "  - Localite_Totalement_Inconnue_Xyz (Commune_A, ALIBORI)\n"
    resultats = orchestration.traiter_rapport_hebdomadaire(graph, email, REFERENCE_DATE)

    assert len(resultats) == 1
    assert resultats[0]["id_localite"] is None
    assert resultats[0]["statut_alerte"] == "a_verifier"
    assert resultats[0]["section_rapport"] is None


def test_traiter_rapport_hebdomadaire_localite_ambigue_via_monkeypatch(monkeypatch):
    import pandas as pd

    loc = pd.DataFrame(
        [
            {"ID_Localite": "Site_A1", "Nom_Geo_1": "ALIBORI", "Localite": "Kandi_Centre"},
            {"ID_Localite": "Site_A2", "Nom_Geo_1": "ALIBORI", "Localite": "Kandi_Nord"},
        ]
    )
    monkeypatch.setattr(data_access, "_load_all", lambda: {"localites": loc})

    graph = _graphe()
    email = "  - Kandi (Commune_A, ALIBORI)\n"
    resultats = orchestration.traiter_rapport_hebdomadaire(graph, email, REFERENCE_DATE)

    assert len(resultats) == 1
    assert resultats[0]["id_localite"] is None
    assert set(resultats[0]["candidats_resolution"]) >= {"Kandi_Centre", "Kandi_Nord"}


def test_traiter_rapport_hebdomadaire_email_vide():
    graph = _graphe()
    resultats = orchestration.traiter_rapport_hebdomadaire(graph, "texte sans localité", REFERENCE_DATE)
    assert len(resultats) == 1
    assert resultats[0]["statut_alerte"] == "a_verifier"
