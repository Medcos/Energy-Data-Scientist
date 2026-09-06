"""
test_data_access.py — lister_localites (ajouté Jour 5 pour peupler le
sélecteur de la page Streamlit "Simulateur de relance").
"""

from agent import data_access


def test_lister_localites_contient_les_localites_gelees():
    localites = data_access.lister_localites()
    ids = {l["ID_Localite"] for l in localites}
    assert {"Site_09", "Site_23", "Site_35", "Site_39", "Site_45"} <= ids
    assert len(localites) == 55


def test_lister_localites_a_un_departement_par_entree():
    localites = data_access.lister_localites()
    assert all(l["departement"] for l in localites)
