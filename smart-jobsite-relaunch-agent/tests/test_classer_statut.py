"""
test_classer_statut.py — Classification Normal/Retard/Critique
(nodes.classer_statut), section 6.2.5 du résumé de reprise (Jour 3).

Construit des AgentState synthétiques avec reste_a_faire/semaines_restantes
contrôlés pour chaque cas, plutôt que de passer par tout le graphe.
"""

from agent import nodes
from agent.state import AgentState, HistoriqueCadenceEntry

SEUIL_RETARD_SEMAINES = nodes.SEUIL_RETARD_SEMAINES  # 4, cf. nodes.py


def test_statut_normal():
    # Reste > 0, échéance confortable (> seuil retard), pas d'historique.
    state = AgentState(
        reste_a_faire={"T1": 10.0},
        semaines_restantes={"T1": SEUIL_RETARD_SEMAINES + 2},
        cadence_recommandee={"T1": 1.0},
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "normal"}


def test_statut_normal_quand_taches_terminees():
    # Toutes les tâches ont un reste <= 0 -> aucune alerte, normal.
    state = AgentState(
        reste_a_faire={"T1": 0.0, "T2": -3.0},
        semaines_restantes={"T1": -1.0, "T2": 2.0},
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "normal"}


def test_statut_retard_echeance_proche():
    # Reste > 0, échéance dans le seuil de retard (mais pas encore dépassée).
    state = AgentState(
        reste_a_faire={"T1": 10.0},
        semaines_restantes={"T1": SEUIL_RETARD_SEMAINES},  # <= seuil -> retard
        cadence_recommandee={"T1": 2.5},
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "retard"}


def test_statut_retard_via_cadence_historique_elevee():
    # Échéance confortable, mais cadence recommandée cette semaine trop
    # supérieure à la moyenne historique -> retard (branche historique de
    # classer_statut, câblée sur state.historique_cadence depuis l'étape 1
    # du Jour 3 — auparavant ce sous-critère était neutralisé par le stub
    # data_access.lire_historique_cadence qui renvoyait toujours []).
    state = AgentState(
        reste_a_faire={"T1": 15.0},
        semaines_restantes={"T1": SEUIL_RETARD_SEMAINES + 2},
        cadence_recommandee={"T1": 5.0},  # > 1.5 x la moyenne historique (2.0)
        historique_cadence=[
            HistoriqueCadenceEntry(semaine="2026-08-17", reste_a_faire={"T1": 2.0}),
            HistoriqueCadenceEntry(semaine="2026-08-24", reste_a_faire={"T1": 2.0}),
        ],
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "retard"}


def test_statut_critique_echeance_deja_depassee():
    # Cas limite explicitement demandé (section 6.2.5) : semaines_restantes
    # <= 0 avec reste_a_faire > 0 -> critique, INDÉPENDAMMENT de la cadence
    # (même avec une cadence historique qui suggérerait "normal").
    state = AgentState(
        reste_a_faire={"T1": 5.0},
        semaines_restantes={"T1": 0.0},
        cadence_recommandee={},  # pas de cadence lissée (délai dépassé)
        historique_cadence=[
            HistoriqueCadenceEntry(semaine="2026-08-17", reste_a_faire={"T1": 1.0}),
        ],
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "critique"}

    # Échéance dépassée depuis plus longtemps encore -> toujours critique.
    state.semaines_restantes["T1"] = -3.0
    assert nodes.classer_statut(state) == {"statut_alerte": "critique"}


def test_statut_critique_prioritaire_sur_retard():
    # Une tâche critique (échéance dépassée) et une autre en retard sur la
    # même localité -> le statut global est critique (a_du_critique prime).
    state = AgentState(
        reste_a_faire={"T1": 5.0, "T2": 8.0},
        semaines_restantes={"T1": -1.0, "T2": SEUIL_RETARD_SEMAINES},
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "critique"}


def test_statut_historique_avec_tache_sur_realisee_ne_force_pas_retard():
    # Régression Jour 5 (post-déploiement) : une tâche en fort sur-réalisé
    # dans l'historique (reste très négatif, ex. TASK_Cable_BT à Site_09 :
    # -4879 — un écart de données du Jour 1) ne doit pas, à elle seule,
    # déclencher "retard" pour une localité dont la cadence courante est par
    # ailleurs tout à fait normale. Avant le correctif (reste_actionnable
    # appliqué à cadence_moyenne_historique), cette tâche négative tirait la
    # moyenne historique fortement en dessous de zéro, rendant
    # `cadence > 1.5 * cadence_moyenne_historique` trivialement vrai.
    state = AgentState(
        reste_a_faire={"T1": 3.0},
        semaines_restantes={"T1": SEUIL_RETARD_SEMAINES + 2},  # échéance confortable
        cadence_recommandee={"T1": 1.0},  # cadence modeste, cohérente avec l'historique actionnable (1.0)
        historique_cadence=[
            HistoriqueCadenceEntry(
                semaine="2026-08-17",
                reste_a_faire={"T1": 1.0, "TASK_Cable_BT": -4879.0},
            ),
            HistoriqueCadenceEntry(
                semaine="2026-08-24",
                reste_a_faire={"T1": 1.0, "TASK_Cable_BT": -4879.0},
            ),
        ],
    )
    assert nodes.classer_statut(state) == {"statut_alerte": "normal"}
