"""
test_app_streamlit.py — Non-régression Jour 5 sur l'app Streamlit : chaque
page se rend sans exception au chargement initial (pas de clic simulé ici,
pour ne pas invoquer le graphe contre le checkpoints.sqlite versionné —
cf. tests/test_orchestration.py et tests/test_api.py pour la logique
d'invocation, déjà testée en isolation avec MemorySaver).
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).parent.parent / "app"

PAGES = [
    "Accueil.py",
    "pages/1_Simulateur_de_relance.py",
    "pages/2_Historique_de_cadence.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_se_rend_sans_exception(page):
    at = AppTest.from_file(str(APP_DIR / page))
    at.run(timeout=30)
    assert not at.exception
