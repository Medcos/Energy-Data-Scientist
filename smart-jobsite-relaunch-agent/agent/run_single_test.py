"""
run_single_test.py — Validation du Jour 2 : fait tourner l'agent en local
sur UNE localité extraite de sample_report_email.txt et affiche la section
de rapport produite, ainsi que l'état final pour inspection.

Usage :
    python -m agent.run_single_test
"""

from datetime import date
from pathlib import Path

from .graph import compile_graph
from .state import AgentState

DATA_DIR = Path(__file__).parent.parent / "data"

# Doit correspondre à REFERENCE_DATE de data/generate_demo_data.py pour que
# les échéances de planning et les reste à faire soient cohérents.
REFERENCE_DATE = date(2026, 8, 31)


def main():
    email_text = (DATA_DIR / "sample_report_email.txt").read_text(encoding="utf-8")

    graph = compile_graph()
    initial_state = AgentState(
        thread_id="test_jour2_localite_unique",
        email_brut=email_text,
        date_du_jour=REFERENCE_DATE,
    )

    config = {"configurable": {"thread_id": initial_state.thread_id}}
    result = graph.invoke(initial_state, config=config)

    print("=" * 70)
    print("ÉTAT FINAL (champs clés)")
    print("=" * 70)
    print(f"nom_localite_brut       : {result.get('nom_localite_brut')}")
    print(f"id_localite (résolu)    : {result.get('id_localite')}")
    print(f"candidats_resolution    : {result.get('candidats_resolution')}")
    print(f"jours_inactivite_decl.  : {result.get('jours_inactivite_declares')}")
    print(f"derniere_activite_mes.  : {result.get('derniere_activite_mesuree')}")
    print(f"statut_alerte           : {result.get('statut_alerte')}")
    print(f"erreurs                 : {result.get('erreurs')}")
    print()
    print("reste_a_faire           :")
    for k, v in result.get("reste_a_faire", {}).items():
        print(f"    {k:20s} {v:>10.1f}")
    print()
    print("=" * 70)
    print("SECTION DE RAPPORT GÉNÉRÉE")
    print("=" * 70)
    print(result.get("section_rapport", "(aucune — voir erreurs ci-dessus)"))


if __name__ == "__main__":
    main()
