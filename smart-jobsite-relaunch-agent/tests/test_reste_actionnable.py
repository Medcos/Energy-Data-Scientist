"""
test_reste_actionnable.py — Régression Jour 5 (post-déploiement) : la page
Streamlit "Historique de cadence" affichait un total de reste à faire
absurde (ex. Site_09 : ~-4753 au lieu de ~+340) parce qu'elle sommait TOUTES
les valeurs de reste_a_faire, y compris les tâches en fort sur-réalisé
(reste très négatif — 131 des 573 couples tâche/localité du jeu de données
Jour 1 sont dans ce cas, concentrés sur TASK_Cable_BT).

`reste_actionnable` (agent/nodes.py) est maintenant le seul endroit qui
définit "reste actionnable" (reste > 0) — utilisé à la fois par
generer_section_rapport (déjà le cas depuis le Jour 2) et par la page
Historique de cadence (nouveau, ce correctif).
"""

from agent.nodes import reste_actionnable


def test_filtre_les_taches_terminees_ou_sur_realisees():
    reste = {"A": 10.0, "B": 0.0, "C": -4879.0, "D": 3.0}
    assert reste_actionnable(reste) == {"A": 10.0, "D": 3.0}


def test_ne_modifie_pas_les_valeurs_positives():
    reste = {"A": 274.0, "B": 2.0}
    assert reste_actionnable(reste) == reste


def test_dict_vide():
    assert reste_actionnable({}) == {}


def test_reproduit_le_cas_site_09_du_bug_deploiement():
    from agent import data_access

    reste = data_access.lire_reste_a_faire("Site_09")
    total_non_filtre = sum(reste.values())
    total_actionnable = sum(reste_actionnable(reste).values())

    # Avant correctif : le total non filtré est fortement négatif à cause de
    # TASK_Cable_BT (-4879) — c'est ce que la page Historique affichait.
    assert total_non_filtre < -1000
    # Après correctif : le total actionnable (ce que la page affiche
    # maintenant) reste dans une plage plausible, cohérente avec le rapport
    # texte déjà généré pour Site_09 (~339, cf. docs/exemple_rapport_hebdomadaire.md).
    assert 0 < total_actionnable < 1000
