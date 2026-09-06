"""
test_extraction_localites.py — Régression Jour 4 : erreurs ne doit pas
s'accumuler indéfiniment d'une semaine à l'autre sur le même thread_id.

extraction_localites est le premier nœud du graphe ; c'est lui qui doit
réinitialiser erreurs à chaque run (les autres nœuds font
`state.erreurs + [...]`, donc tout en dépend).
"""

from agent import nodes
from agent.state import AgentState


def test_erreurs_repart_a_zero_meme_avec_extraction_reussie():
    # Un run précédent (semaine passée) a laissé des erreurs dans le
    # checkpoint -> le nouveau run ne doit PAS les reporter, même quand
    # l'extraction de cette semaine réussit.
    state = AgentState(
        email_brut="  - Site_09 (Commune_A, ALIBORI)\n",
        erreurs=["anomalie de la semaine précédente"],
    )
    out = nodes.extraction_localites(state)
    assert out["erreurs"] == []


def test_erreurs_repart_a_zero_quand_extraction_echoue():
    # Idem quand l'extraction ne trouve rien : l'erreur de CE run remplace
    # l'historique, elle ne s'y ajoute pas.
    state = AgentState(
        email_brut="texte sans aucune localité reconnaissable",
        erreurs=["anomalie de la semaine précédente"],
    )
    out = nodes.extraction_localites(state)
    assert out["erreurs"] == ["Aucune localité extraite du texte fourni."]
