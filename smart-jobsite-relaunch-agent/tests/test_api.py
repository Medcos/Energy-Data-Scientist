"""
test_api.py — Régression Jour 5 sur les 3 endpoints FastAPI (api/main.py).

Remplace le _graph du module par un graphe MemorySaver (monkeypatch) avant
chaque test : le module importe compile_graph() au chargement, qui ouvre
par défaut une connexion vers le checkpoints.sqlite VERSIONNÉ du repo — on
ne veut surtout pas que faire tourner la suite de tests pollue ce fichier
livré (leçon du Jour 4 : c'est exactement ce qui s'était passé en testant
l'API manuellement, d'où la régénération de checkpoints.sqlite avant chaque
livraison).
"""

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from agent.graph import compile_graph
from api import main

DATA_DIR = Path(__file__).parent.parent / "data"
REFERENCE_DATE = "2026-08-31"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "_graph", compile_graph(checkpointer=MemorySaver()))
    return TestClient(main.app)


def test_sante(client):
    assert client.get("/sante").json() == {"ok": True}


def test_analyser_localite(client):
    resp = client.post(
        "/analyser-localite",
        json={"id_localite": "Site_09", "date_du_jour": REFERENCE_DATE},
    )
    assert resp.status_code == 200
    corps = resp.json()
    assert corps["id_localite"] == "Site_09"
    assert corps["section_rapport"] is not None


def test_traiter_rapport_hebdomadaire_toutes_les_localites(client):
    email = (DATA_DIR / "sample_report_email.txt").read_text(encoding="utf-8")
    resp = client.post(
        "/traiter-rapport-hebdomadaire",
        json={"email_brut": email, "date_du_jour": REFERENCE_DATE},
    )
    assert resp.status_code == 200
    resultats = resp.json()["resultats"]
    ids = {r["id_localite"] for r in resultats}
    assert ids == {"Site_09", "Site_23", "Site_35", "Site_39", "Site_45"}


def test_historique_404_avant_tout_appel(client):
    resp = client.get("/historique/Site_09")
    assert resp.status_code == 404


def test_historique_apres_deux_appels(client):
    client.post("/analyser-localite", json={"id_localite": "Site_09", "date_du_jour": "2026-08-24"})
    client.post("/analyser-localite", json={"id_localite": "Site_09", "date_du_jour": "2026-08-31"})
    resp = client.get("/historique/Site_09")
    assert resp.status_code == 200
    historique = resp.json()["historique"]
    assert [h["semaine"] for h in historique] == ["2026-08-24", "2026-08-31"]
