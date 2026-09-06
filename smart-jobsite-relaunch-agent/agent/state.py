"""
state.py — Modèle d'état de l'agent LangGraph (spec technique, section 6).

L'état est un objet partagé que chaque nœud du graphe lit et complète.
Un run est déclenché PAR LOCALITÉ, avec thread_id = code localité
(ex. Site_23), sauvegardé via un Checkpointer (MemorySaver au Jour 2,
SqliteSaver à partir du Jour 3).
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class HistoriqueCadenceEntry(BaseModel):
    """Une entrée de l'historique de cadence, alimentée semaine après semaine
    via le Checkpointer (peuplée à partir du Jour 3 — vide au Jour 2)."""

    semaine: str  # date ISO du lundi de run (ex. "2026-08-31")
    reste_a_faire: dict[str, float]


class AgentState(BaseModel):
    # --- Identité du run ---
    thread_id: str = ""

    # --- Entrée brute (ajout pratique hors tableau section 6 : porte le
    # texte source pour que extraction_localites ait quelque chose à lire) ---
    email_brut: str = ""
    # Date de référence simulée pour le calcul des échéances — en
    # production, date.today() ; pour les tests/démos, fixée explicitement
    # pour rejouer un "aujourd'hui" cohérent avec les données générées.
    date_du_jour: date = Field(default_factory=date.today)

    # --- Champs de la table section 6 de la spec ---
    nom_localite_brut: str = ""
    departement_declare: Optional[str] = None
    commune_declaree: Optional[str] = None
    jours_inactivite_declares: Optional[int] = None

    id_localite: Optional[str] = None

    derniere_activite_mesuree: Optional[date] = None

    reste_a_faire: dict[str, float] = Field(default_factory=dict)
    deadlines_planning: dict[str, date] = Field(default_factory=dict)
    semaines_restantes: dict[str, float] = Field(default_factory=dict)
    cadence_recommandee: dict[str, float] = Field(default_factory=dict)

    statut_alerte: Literal["normal", "retard", "critique", "a_verifier"] = "a_verifier"

    historique_cadence: list[HistoriqueCadenceEntry] = Field(default_factory=list)

    erreurs: list[str] = Field(default_factory=list)

    # --- Sortie (ajout pratique) ---
    section_rapport: Optional[str] = None
    candidats_resolution: list[str] = Field(default_factory=list)
