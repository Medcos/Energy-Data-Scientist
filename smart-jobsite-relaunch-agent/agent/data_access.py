"""
data_access.py — Implémentation des outils de la section 7 de la spec
technique, adossés aux fichiers CSV générés au Jour 1 (data/).

En production (Jour 5, phase 3 de la roadmap), ces fonctions seraient
remplacées par des appels à un serveur MCP exposant Electrack Pro. Pour la
démo, elles lisent directement les CSV — le contrat (signatures, valeurs de
retour) est conçu pour rester identique le jour où l'implémentation change.
"""

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Chargement (mis en cache — les CSV sont figés pour la semaine, cf. Jour 1)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_all() -> dict[str, pd.DataFrame]:
    return {
        "localites": pd.read_csv(DATA_DIR / "localites.csv"),
        "objectifs": pd.read_csv(DATA_DIR / "objectifs.csv"),
        "interventions": pd.read_csv(DATA_DIR / "interventions.csv", parse_dates=["Date_Saisie"]),
        "details": pd.read_csv(DATA_DIR / "details_intervention.csv", parse_dates=["Date"]),
        "taches": pd.read_csv(DATA_DIR / "taches_reference.csv"),
        "planning": pd.read_csv(DATA_DIR / "planning_departements.csv", parse_dates=["Date_Debut", "Date_Fin"]),
    }


def reset_cache():
    """Utile pour les tests qui régénèrent les CSV entre deux runs."""
    _load_all.cache_clear()


# ---------------------------------------------------------------------------
# resoudre_localite — fuzzy matching (section 5.2)
# ---------------------------------------------------------------------------


MARGE_AMBIGUITE = 5.0  # points d'écart WRatio requis entre le 1er et le 2e
# candidat pour considérer la correspondance comme fiable (ajouté Jour 3,
# cf. section 6.2.5 du résumé de reprise, cas de test "correspondance de nom
# ambiguë"). Sans cette marge, deux localités différentes mais proches du
# nom recherché (score identique ou quasi identique, ex. "Kandi_Centre" vs
# "Kandi_Nord" pour la requête "Kandi") étaient résolues silencieusement
# vers le premier candidat de la liste — un vrai risque de mauvaise
# localité relancée. 5 points laisse une marge confortable au-dessus du
# bruit normal du matching sur des noms générés Site_01..Site_55 (où le
# meilleur candidat réel obtient typiquement 100 contre ~86 pour les
# suivants, cf. vérification sur les 8 localités simulées au Jour 3).


def resoudre_localite(
    nom_localite_brut: str,
    departement: Optional[str] = None,
    seuil: int = 80,
    marge_ambiguite: float = MARGE_AMBIGUITE,
) -> tuple[Optional[str], list[str]]:
    """Résout un nom de localité brut (potentiellement mal orthographié) vers
    un ID_Localite.

    Retourne (id_localite, candidats) :
      - correspondance fiable  -> (id_localite, [])
      - aucune correspondance fiable, OU correspondance ambiguë (meilleur
        score non décisif par rapport au second) -> (None, [liste de noms
        candidats])
    """
    data = _load_all()
    loc = data["localites"]
    if departement:
        loc = loc[loc["Nom_Geo_1"].str.upper() == departement.upper()]
    if loc.empty:
        return None, []

    choices = loc["Localite"].tolist()
    # normalise les séparateurs pour absorber les variantes orthographiques
    # illustrées dans sample_report_email.txt (ex. "Site-09" vs "Site_09")
    query = nom_localite_brut.replace("-", "_").replace(" ", "_")

    matches = process.extract(query, choices, scorer=fuzz.WRatio, limit=3)
    if not matches:
        return None, []

    best_name, best_score, _ = matches[0]
    deuxieme_score = matches[1][1] if len(matches) > 1 else -1
    if best_score >= seuil and (best_score - deuxieme_score) >= marge_ambiguite:
        row = loc[loc["Localite"] == best_name].iloc[0]
        return row["ID_Localite"], []

    return None, [m[0] for m in matches]


# ---------------------------------------------------------------------------
# lire_reste_a_faire (section 5.3)
# ---------------------------------------------------------------------------


def lire_reste_a_faire(id_localite: str, as_of: Optional[date] = None) -> dict[str, float]:
    """Reste à faire par tâche = Quantite_Prevue - somme(Quantite_Nette_Calculee).

    as_of (ajouté Jour 3, cf. section 6.2 du résumé de reprise) : ne compte
    que les interventions dont la date est <= as_of, pour que le "reste à
    faire" reflète l'état réellement connu à cette date-là plutôt que le
    total cumulé de tout le jeu de données. None (par défaut) = comportement
    Jour 1/2 inchangé, tout compter — utilisé quand aucune date de
    simulation n'est pertinente (ex. appel hors contexte AgentState).
    """
    data = _load_all()
    obj = data["objectifs"]
    obj_loc = obj[obj["ID_Localite"] == id_localite]

    det = data["details"].merge(
        data["interventions"][["ID_Intervention", "ID_Localite"]], on="ID_Intervention"
    )
    det_loc = det[det["ID_Localite"] == id_localite]
    if as_of is not None:
        det_loc = det_loc[det_loc["Date"] <= pd.Timestamp(as_of)]
    realise = det_loc.groupby("Tache")["Quantite_Nette_Calculee"].sum()

    reste = {}
    for _, row in obj_loc.iterrows():
        r = float(realise.get(row["ID_Tache"], 0.0))
        reste[row["ID_Tache"]] = float(row["Quantite_Prevue"]) - r
    return reste


# ---------------------------------------------------------------------------
# lire_derniere_activite (section 5.3)
# ---------------------------------------------------------------------------


def lire_derniere_activite(id_localite: str, as_of: Optional[date] = None) -> Optional[date]:
    """as_of (ajouté Jour 3, même logique que lire_reste_a_faire) : ignore
    les interventions postérieures à as_of, pour qu'une localité active ne
    semble pas avoir eu de la "future" activité lors d'une semaine simulée
    antérieure (simulate_weeks.py)."""
    data = _load_all()
    interv = data["interventions"]
    d = interv[interv["ID_Localite"] == id_localite]
    if as_of is not None:
        d = d[d["Date_Saisie"] <= pd.Timestamp(as_of)]
    if d.empty:
        return None
    return d["Date_Saisie"].max().date()


# ---------------------------------------------------------------------------
# lire_deadline_planning (section 5.4)
# ---------------------------------------------------------------------------


def lire_deadline_planning(departement: str, phase: str) -> Optional[date]:
    data = _load_all()
    plan = data["planning"]
    row = plan[(plan["Departement"] == departement) & (plan["Phase"] == phase)]
    if row.empty:
        return None
    return row.iloc[0]["Date_Fin"].date()


# ---------------------------------------------------------------------------
# Référentiel des tâches (poids + phase associée) — utilisé par
# calculer_cadence et pour prioriser les "tâches majeures" (section 5.3)
# ---------------------------------------------------------------------------


def get_taches_reference() -> pd.DataFrame:
    return _load_all()["taches"]


def lister_localites() -> list[dict]:
    """Liste (ID_Localite, département) de toutes les localités connues —
    utilisé par la page Streamlit "Simulateur de relance" (Jour 5) pour
    peupler le sélecteur, l'utilisateur choisissant une localité existante
    plutôt que de taper un nom (pas de fuzzy matching nécessaire sur ce
    chemin, cf. route_depart/agent/orchestration.analyser_localite)."""
    data = _load_all()
    loc = data["localites"][["ID_Localite", "Nom_Geo_1"]].rename(columns={"Nom_Geo_1": "departement"})
    return loc.sort_values("ID_Localite").to_dict("records")


def get_departement_localite(id_localite: str) -> Optional[str]:
    data = _load_all()
    row = data["localites"][data["localites"]["ID_Localite"] == id_localite]
    if row.empty:
        return None
    return row.iloc[0]["Nom_Geo_1"]


# ---------------------------------------------------------------------------
# lire_historique_cadence (section 7) — stub au Jour 2 : sans SqliteSaver,
# aucun historique multi-semaines n'existe encore. Remplacé au Jour 3.
# ---------------------------------------------------------------------------


def lire_historique_cadence(id_localite: str) -> list[dict]:
    return []
