"""
simulate_weeks.py — Rejoue 4 lundis fictifs successifs pour peupler
historique_cadence de façon réaliste, avant le premier lancement public
(Plan_de_mise_en_place Jour 3, section 6.2.4 du résumé de reprise).

Localités simulées :
  - Les 5 localités "gelées" choisies arbitrairement au Jour 1 (Site_09,
    Site_23, Site_35, Site_39, Site_45) : leur dernière intervention RÉELLE
    est bien antérieure aux 4 semaines simulées (mars-mi mai 2026, vérifié
    sur details_intervention.csv) -> reste_a_faire y reste identique semaine
    après semaine (stagnation réelle, pas fabriquée), mais semaines_restantes
    diminue et cadence_recommandee grimpe à mesure que les échéances de
    planning se rapprochent, jusqu'à un possible passage en critique.
  - 3 localités actives (Site_46, Site_49, Site_04), choisies parce que
    leurs interventions réelles sont réparties sur plusieurs des 4 lundis
    simulés -> reste_a_faire y baisse réellement, semaine après semaine.

Pour chaque localité, thread_id = id_localite (convention établie au Jour 2).
Le premier run de chaque localité amorce le thread avec un AgentState
complet (email de démo mono-localité, même format que sample_report_email.txt
du Jour 1, extrait via le vrai pipeline extraction_localites/resoudre_localite
— pas d'id_localite injecté à la main). Les runs suivants passent un dict
PARTIEL ({"date_du_jour": ...}) pour laisser le Checkpointer fusionner sur
l'état déjà persisté : repasser un AgentState complet écraserait
historique_cadence à chaque semaine (découverte technique du Jour 3,
section 6.1 du résumé de reprise).

Usage :
    python -m agent.simulate_weeks
"""

from datetime import date, timedelta
from pathlib import Path

from .graph import compile_graph
from .state import AgentState

DATA_DIR = Path(__file__).parent.parent / "data"

# Doit rester cohérent avec REFERENCE_DATE de data/generate_demo_data.py et
# de run_single_test.py (Jour 2) — c'est la date la plus tardive du jeu de
# données ; les 3 semaines précédentes sont simulées en remontant par pas de
# 7 jours, comme proposé section 6.2.4 du résumé de reprise.
REFERENCE_DATE = date(2026, 8, 31)
SEMAINES_SIMULEES = sorted(REFERENCE_DATE - timedelta(days=7 * i) for i in range(4))
# -> [2026-08-10, 2026-08-17, 2026-08-24, 2026-08-31]

# (id_localite, commune, departement) — le nom envoyé dans l'email de
# simulation est toujours id_localite lui-même (les noms de localités sont
# déjà pseudonymisés en Site_XX, cf. section 3 du résumé de reprise).
#
# Gelées : mêmes commune/département que dans sample_report_email.txt
# (Jour 1). Actives : commune/département lus dans data/localites.csv.
LOCALITES_SIMULEES = [
    ("Site_09", "Commune_A", "ALIBORI"),   # gelée
    ("Site_23", "Commune_G", "DONGA"),     # gelée
    ("Site_35", "Commune_D", "ALIBORI"),   # gelée
    ("Site_39", "Commune_F", "DONGA"),     # gelée
    ("Site_45", "Commune_B", "DONGA"),     # gelée
    ("Site_46", "Commune_H", "ATACORA"),   # active
    ("Site_49", "Commune_D", "ALIBORI"),   # active
    ("Site_04", "Commune_H", "ATACORA"),   # active
]


def _email_mono_localite(id_localite: str, commune: str, departement: str) -> str:
    """Email synthétique au format de sample_report_email.txt (une seule
    localité par email), pour que extraction_localites/resoudre_localite
    passent par le vrai pipeline d'extraction plutôt qu'un id_localite
    injecté directement dans l'état."""
    return (
        "Objet : [Rapport hebdomadaire] Chantiers sans activité depuis plus de 3 mois\n\n"
        "Bonjour,\n\n"
        "Voici la liste des localités n'ayant connu aucune activité de chantier "
        "depuis plus de 3 mois :\n\n"
        f"  - {id_localite} ({commune}, {departement})\n\n"
        "Merci de relancer les équipes concernées.\n\n"
        "-- Rapport automatique Electrack Pro (démo)"
    )


def simuler_localite(graph, id_localite: str, commune: str, departement: str) -> None:
    config = {"configurable": {"thread_id": id_localite}}
    email = _email_mono_localite(id_localite, commune, departement)

    premiere_semaine, *semaines_suivantes = SEMAINES_SIMULEES

    # Premier run de ce thread_id : amorce avec un AgentState complet.
    resultat = graph.invoke(
        AgentState(thread_id=id_localite, email_brut=email, date_du_jour=premiere_semaine),
        config=config,
    )
    _afficher_semaine(premiere_semaine, resultat)

    # Runs suivants : dict PARTIEL uniquement.
    for semaine in semaines_suivantes:
        resultat = graph.invoke({"date_du_jour": semaine}, config=config)
        _afficher_semaine(semaine, resultat)


def _afficher_semaine(semaine: date, resultat: dict) -> None:
    reste_total = sum(v for v in resultat.get("reste_a_faire", {}).values() if v > 0)
    print(
        f"  {semaine.isoformat()} -> statut={resultat.get('statut_alerte', '?'):9s} "
        f"reste_total={reste_total:>8.0f}  "
        f"historique={len(resultat.get('historique_cadence', []))} entrée(s)"
    )


def main():
    graph = compile_graph()
    for id_localite, commune, departement in LOCALITES_SIMULEES:
        print(f"=== {id_localite} ===")
        simuler_localite(graph, id_localite, commune, departement)
        print()


if __name__ == "__main__":
    main()
