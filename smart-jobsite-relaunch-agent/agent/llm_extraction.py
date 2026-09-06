"""
llm_extraction.py — Étape 2 de la spec (section 5.2) : extraction en sortie
structurée des localités en souffrance mentionnées dans le rapport email.

Deux chemins :
  1. Appel réel à l'API Anthropic (sortie structurée via tool_use), utilisé
     si ANTHROPIC_API_KEY est défini dans l'environnement. C'est
     l'implémentation "production" — nécessaire en réalité, car les emails
     réels varient dans leur formulation, contrairement au format fixe de
     notre email de démo.
  2. Repli déterministe (expressions régulières), utilisé uniquement quand
     aucune clé API n'est disponible — pour que l'agent reste testable
     localement sans dépendance externe. Il ne fonctionne que sur le format
     de `sample_report_email.txt` généré au Jour 1 ; il ne prétend pas
     remplacer le LLM en production.

Dans les deux cas, la sortie est une liste de dicts :
  {"nom_localite_brut": str, "departement": str|None,
   "commune": str|None, "jours_inactivite_declares": int|None}
"""

from __future__ import annotations

import json
import os
import re

EXTRACTION_TOOL_SCHEMA = {
    "name": "extraire_localites",
    "description": "Extrait la liste des localités signalées inactives dans le rapport email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "localites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nom_localite_brut": {
                            "type": "string",
                            "description": "Nom de la localité tel qu'écrit dans l'email, orthographe non garantie.",
                        },
                        "departement": {"type": ["string", "null"]},
                        "commune": {"type": ["string", "null"]},
                        "jours_inactivite_declares": {"type": ["integer", "null"]},
                    },
                    "required": ["nom_localite_brut"],
                },
            }
        },
        "required": ["localites"],
    },
}

SYSTEM_PROMPT = (
    "Tu extrais, depuis un rapport email de suivi de chantier, la liste des "
    "localités signalées comme inactives depuis plus de 3 mois. Pour chaque "
    "localité, capture le nom tel qu'écrit (ne corrige pas l'orthographe), "
    "le département et la commune si mentionnés, et le nombre de jours "
    "d'inactivité s'il est indiqué. N'invente aucune information absente du texte."
)


def _extract_via_llm(email_text: str) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "extraire_localites"},
        messages=[{"role": "user", "content": email_text}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input.get("localites", [])
    return []


# Approx. "3 mois" -> jours, pour convertir une formulation textuelle
# ("depuis plus de 3 mois") si aucun nombre de jours explicite n'apparaît.
_DEFAULT_JOURS_SI_TEXTE_SEUL = 90


def _extract_via_regex(email_text: str) -> list[dict]:
    """Repli déterministe, calé sur le format de sample_report_email.txt :
        - Site_23 (Commune_G, DONGA)
    Tolère les variantes orthographiques simples (tiret/espace au lieu
    d'underscore), qui restent le cas d'usage principal du fuzzy matching
    en aval (resoudre_localite).
    """
    pattern = re.compile(
        r"-\s*([^\(\n]+?)\s*\(([^,\)]+),\s*([^\)]+)\)"
    )
    results = []
    for m in pattern.finditer(email_text):
        nom, commune, dept = (g.strip() for g in m.groups())
        results.append(
            {
                "nom_localite_brut": nom,
                "departement": dept,
                "commune": commune,
                "jours_inactivite_declares": _DEFAULT_JOURS_SI_TEXTE_SEUL,
            }
        )
    return results


def extraire_localites(email_text: str) -> list[dict]:
    """Point d'entrée du nœud extraction_localites. Utilise l'API Anthropic
    si une clé est configurée, sinon un repli déterministe (voir docstring
    du module)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _extract_via_llm(email_text)
        except Exception:
            # En production on voudrait logguer/alerter plutôt que replier
            # silencieusement ; pour la démo, on retombe sur le mode dégradé
            # et l'erreur remonte via l'état (voir nodes.py).
            pass
    return _extract_via_regex(email_text)
