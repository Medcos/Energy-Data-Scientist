"""
test_resoudre_localite.py — Cas "correspondance de nom ambiguë"
(data_access.resoudre_localite), section 6.2.5 du résumé de reprise (Jour 3).

Utilise un jeu de localités synthétique (monkeypatch de data_access._load_all)
plutôt que les vraies données, pour contrôler précisément les scores de
fuzzy matching et déclencher une vraie ambiguïté à volonté.

Cette suite a fait ressortir un bug réel au Jour 3 : resoudre_localite
choisissait silencieusement le premier candidat en cas d'égalité de score
entre plusieurs localités différentes (ex. "Kandi" matchant "Kandi_Centre"
ET "Kandi_Nord" au même score) au lieu de signaler l'ambiguïté. Corrigé par
l'ajout d'une marge de décision (MARGE_AMBIGUITE) entre le 1er et le 2e
candidat.
"""

import pandas as pd
import pytest

from agent import data_access


@pytest.fixture
def localites_synthetiques(monkeypatch):
    """Remplace le chargement CSV par un petit jeu contrôlé :
    - deux localités au nom proche dans le même département (Kandi_Centre /
      Kandi_Nord) pour provoquer une ambiguïté ;
    - une localité nettement différente (Segbana) comme témoin.
    """
    loc = pd.DataFrame(
        [
            {"ID_Localite": "Site_A1", "Nom_Geo_1": "ALIBORI", "Localite": "Kandi_Centre"},
            {"ID_Localite": "Site_A2", "Nom_Geo_1": "ALIBORI", "Localite": "Kandi_Nord"},
            {"ID_Localite": "Site_A3", "Nom_Geo_1": "ALIBORI", "Localite": "Segbana"},
        ]
    )
    monkeypatch.setattr(data_access, "_load_all", lambda: {"localites": loc})
    return loc


def test_correspondance_ambigue_renvoie_none_et_candidats(localites_synthetiques):
    # "Kandi" matche Kandi_Centre ET Kandi_Nord au même score (90.0,
    # vérifié) -> ne doit PAS résoudre silencieusement vers l'un des deux.
    id_localite, candidats = data_access.resoudre_localite("Kandi", departement="ALIBORI")
    assert id_localite is None
    assert set(candidats) >= {"Kandi_Centre", "Kandi_Nord"}


def test_correspondance_non_ambigue_resout_normalement(localites_synthetiques):
    # Nom exact, sans concurrent proche -> résolution silencieuse normale
    # (pas de régression introduite par la marge d'ambiguïté).
    id_localite, candidats = data_access.resoudre_localite("Segbana", departement="ALIBORI")
    assert id_localite == "Site_A3"
    assert candidats == []


def test_correspondance_exacte_meme_avec_concurrents_proches(localites_synthetiques):
    # "Kandi_Centre" exact (score 100) a un écart suffisant avec le second
    # candidat le plus proche (Kandi_Nord, ~64) -> résolution normale, pas
    # d'ambiguïté malgré la présence d'un nom voisin.
    id_localite, candidats = data_access.resoudre_localite("Kandi_Centre", departement="ALIBORI")
    assert id_localite == "Site_A1"
    assert candidats == []


def test_aucune_correspondance_fiable(localites_synthetiques):
    # Nom trop éloigné de tout candidat (score sous le seuil) -> (None,
    # candidats), comportement déjà validé au Jour 2, non régressé ici.
    id_localite, candidats = data_access.resoudre_localite("Zzzzzz", departement="ALIBORI")
    assert id_localite is None
    assert isinstance(candidats, list)
