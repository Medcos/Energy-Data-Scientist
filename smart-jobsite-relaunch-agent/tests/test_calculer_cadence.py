"""
test_calculer_cadence.py — Formule de cadence (nodes.calculer_cadence),
section 6.2.5 du résumé de reprise (Jour 3).

Cas couverts :
  1. Normal : reste > 0 et semaines > 0 -> cadence = reste / semaines.
  2. Reste <= 0 (tâche terminée ou en avance) -> pas de cadence recommandée.
  3. Semaines <= 0 (échéance déjà dépassée) -> pas de cadence lissée
     (le statut Critique porte l'alerte à la place, cf. calculer_cadence
     et classer_statut).
"""

from datetime import date, timedelta

from agent import nodes
from agent.state import AgentState


def _etat(reste: float, jours_avant_deadline: int) -> AgentState:
    aujourdhui = date(2026, 8, 31)
    deadline = aujourdhui + timedelta(days=jours_avant_deadline)
    return AgentState(
        date_du_jour=aujourdhui,
        reste_a_faire={"T1": reste},
        deadlines_planning={"T1": deadline},
    )


def test_cadence_cas_normal():
    # 10 unités restantes, échéance dans 35 jours (5 semaines) -> 2/semaine.
    state = _etat(reste=10.0, jours_avant_deadline=35)
    out = nodes.calculer_cadence(state)
    assert out["semaines_restantes"]["T1"] == 5.0
    assert out["cadence_recommandee"]["T1"] == 2.0


def test_cadence_reste_nul_ou_negatif():
    # Tâche déjà terminée (reste <= 0) : pas de cadence recommandée, même
    # si l'échéance est encore loin.
    for reste in (0.0, -3.0):
        state = _etat(reste=reste, jours_avant_deadline=35)
        out = nodes.calculer_cadence(state)
        assert "T1" not in out["cadence_recommandee"], f"reste={reste}"
        # semaines_restantes reste calculé, lui, indépendamment du reste.
        assert out["semaines_restantes"]["T1"] == 5.0


def test_cadence_semaines_nulles_ou_negatives_echeance_depassee():
    # Échéance déjà dépassée (semaines <= 0) : pas de cadence lissée
    # pertinente, quel que soit le reste à faire.
    for jours_avant_deadline in (0, -14):
        state = _etat(reste=10.0, jours_avant_deadline=jours_avant_deadline)
        out = nodes.calculer_cadence(state)
        assert out["semaines_restantes"]["T1"] <= 0
        assert "T1" not in out["cadence_recommandee"], f"jours={jours_avant_deadline}"
