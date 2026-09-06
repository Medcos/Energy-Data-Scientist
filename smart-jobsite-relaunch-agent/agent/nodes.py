"""
nodes.py — Implémentation des nœuds du graphe (spec technique section 6.1,
Plan_de_mise_en_place Jour 2, complété Jour 3 avec mettre_a_jour_historique).

Chaque nœud reçoit l'AgentState complet et retourne un dict des champs
modifiés (convention LangGraph : mise à jour partielle de l'état).
"""

from datetime import date

from . import data_access
from .llm_extraction import extraire_localites
from .state import AgentState, HistoriqueCadenceEntry

# Seuil d'écart (jours) entre inactivité déclarée par l'email et mesurée
# dans Electrack Pro au-delà duquel on signale plutôt que d'arbitrer
# silencieusement (spec section 5.3, point de vigilance).
SEUIL_ECART_INACTIVITE_JOURS = 7

# Seuils de classement du statut (spec section 5.5)
SEUIL_RETARD_SEMAINES = 4


# ---------------------------------------------------------------------------
# 1. extraction_localites
# ---------------------------------------------------------------------------


def extraction_localites(state: AgentState) -> dict:
    # erreurs repart de ZÉRO ici : nécessaire quand ce nœud s'exécute (chemin
    # email, route_depart -> "a_extraire"), pour que resoudre_localite puisse
    # ensuite faire erreurs + [...] sans reporter les anomalies d'un run
    # précédent sur le même thread_id. Bug trouvé au Jour 4 en testant l'API
    # sur plusieurs semaines successives (le même "écart d'inactivité"
    # apparaissait dupliqué une fois par semaine déjà écoulée).
    # Depuis le Jour 5, ce nœud n'est plus systématiquement le premier du
    # graphe (route_depart peut sauter directement à lire_reste_a_faire
    # quand id_localite est déjà connu) : ce dernier fait désormais le même
    # reset, pour rester le point d'entrée commun aux deux routes — voir son
    # commentaire pour le détail de ce second correctif.
    localites = extraire_localites(state.email_brut)
    if not localites:
        return {
            "erreurs": ["Aucune localité extraite du texte fourni."],
            "statut_alerte": "a_verifier",
        }
    # Cas de test à une seule localité (Jour 2) : on traite la première
    # entrée extraite. Le passage à plusieurs localités par run (fan-out)
    # est prévu au Jour 3/4 (simulate_weeks.py), pas modifié ici.
    premiere = localites[0]
    return {
        "nom_localite_brut": premiere.get("nom_localite_brut", ""),
        "departement_declare": premiere.get("departement"),
        "commune_declaree": premiere.get("commune"),
        "jours_inactivite_declares": premiere.get("jours_inactivite_declares"),
        "erreurs": [],
    }


# ---------------------------------------------------------------------------
# 2. resoudre_localite (routage conditionnel après ce nœud)
# ---------------------------------------------------------------------------


def resoudre_localite(state: AgentState) -> dict:
    id_localite, candidats = data_access.resoudre_localite(
        state.nom_localite_brut, state.departement_declare
    )
    if id_localite is None:
        return {
            "id_localite": None,
            "candidats_resolution": candidats,
            "statut_alerte": "a_verifier",
            "erreurs": state.erreurs
            + [
                f"Résolution ambiguë ou impossible pour "
                f"'{state.nom_localite_brut}' — candidats : {candidats}"
            ],
        }
    return {"id_localite": id_localite, "candidats_resolution": []}


def route_apres_resolution(state: AgentState) -> str:
    """Fonction de routage conditionnel (section 6.1) : résolu -> suite ;
    non résolu -> fin de graphe avec statut a_verifier."""
    return "resolu" if state.id_localite else "non_resolu"


# ---------------------------------------------------------------------------
# 0. route_depart (routage conditionnel AVANT extraction_localites, ajouté
# Jour 5)
#
# Deux façons légitimes de déclencher un run, désormais que l'API (Jour 5)
# expose un accès direct par localité en plus du chemin email :
#   - id_localite déjà connu (ex. /analyser-localite : l'utilisateur choisit
#     une localité existante dans l'UI Streamlit, pas de texte à parser) ->
#     on saute extraction_localites ET resoudre_localite, inutiles ici.
#   - email_brut fourni, id_localite pas encore connu (chemin historique du
#     Jour 2, toujours emprunté par /traiter-rapport-hebdomadaire pour
#     CHAQUE localité extraite d'un rapport, après résolution amont — voir
#     agent/orchestration.py) -> chemin inchangé depuis le Jour 2.
# ---------------------------------------------------------------------------


def route_depart(state: AgentState) -> str:
    return "localite_connue" if state.id_localite else "a_extraire"


# ---------------------------------------------------------------------------
# 3. lire_reste_a_faire
# ---------------------------------------------------------------------------


def lire_reste_a_faire(state: AgentState) -> dict:
    # as_of=state.date_du_jour (Jour 3) : ne compte que les interventions
    # connues à cette date-là, pour que le reste à faire varie réellement
    # d'une semaine simulée à l'autre (simulate_weeks.py) au lieu de
    # toujours refléter le total cumulé de tout le jeu de données.
    reste = data_access.lire_reste_a_faire(state.id_localite, as_of=state.date_du_jour)

    # erreurs repart de ZÉRO ici (Jour 5) : ce nœud est le point d'entrée
    # commun aux deux routes possibles depuis route_depart (email à extraire,
    # OU localité déjà connue qui saute directement ici). Le correctif du
    # Jour 4 réinitialisait erreurs dans extraction_localites, qui reste
    # correct pour le chemin email — mais route_depart peut désormais sauter
    # ce nœud entièrement (endpoint /analyser-localite, fan-out de
    # /traiter-rapport-hebdomadaire), auquel cas rien ne réinitialisait
    # erreurs et les anomalies d'un appel précédent sur le même thread_id
    # restaient dans le rapport indéfiniment — même bug que le Jour 4, sous
    # une autre forme, trouvé en écrivant les tests d'orchestration du Jour
    # 5. Reset sans risque ici : sur le chemin email, resoudre_localite (qui
    # s'exécute juste avant, dans la branche résolue) ne touche jamais à
    # erreurs, donc il vaut déjà [] à ce stade — ce reset est un no-op sur
    # ce chemin et l'unique correctif nécessaire sur l'autre.
    return {"reste_a_faire": reste, "erreurs": []}


# ---------------------------------------------------------------------------
# 4. lire_derniere_activite (avec vérification croisée, section 5.3)
# ---------------------------------------------------------------------------


def lire_derniere_activite(state: AgentState) -> dict:
    # as_of=state.date_du_jour (Jour 3), même logique que lire_reste_a_faire :
    # une localité active ne doit pas paraître avoir eu de l'activité "future"
    # lors d'une semaine simulée antérieure (simulate_weeks.py).
    derniere = data_access.lire_derniere_activite(state.id_localite, as_of=state.date_du_jour)
    erreurs = list(state.erreurs)

    if derniere is None:
        erreurs.append("Aucune intervention trouvée pour cette localité.")
    elif state.jours_inactivite_declares is not None:
        jours_mesures = (state.date_du_jour - derniere).days
        ecart = abs(jours_mesures - state.jours_inactivite_declares)
        if ecart > SEUIL_ECART_INACTIVITE_JOURS:
            erreurs.append(
                f"Écart d'inactivité : {state.jours_inactivite_declares} j déclarés "
                f"(email) vs {jours_mesures} j mesurés (Electrack Pro) — écart de "
                f"{ecart} j, au-delà du seuil de {SEUIL_ECART_INACTIVITE_JOURS} j."
            )

    return {"derniere_activite_mesuree": derniere, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# 5. lire_deadline_planning
# ---------------------------------------------------------------------------


def lire_deadline_planning(state: AgentState) -> dict:
    departement = data_access.get_departement_localite(state.id_localite)
    taches_ref = data_access.get_taches_reference().set_index("ID_Tache")

    deadlines = {}
    erreurs = list(state.erreurs)
    for id_tache in state.reste_a_faire:
        if id_tache not in taches_ref.index:
            erreurs.append(f"Tâche inconnue au référentiel : {id_tache}")
            continue
        phase = taches_ref.loc[id_tache, "Phase_Planning"]
        deadline = data_access.lire_deadline_planning(departement, phase)
        if deadline is None:
            erreurs.append(f"Aucune échéance de planning trouvée pour {id_tache} ({phase}).")
            continue
        deadlines[id_tache] = deadline

    return {"deadlines_planning": deadlines, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# 6. calculer_cadence (section 5.4-5.5)
# ---------------------------------------------------------------------------


def calculer_cadence(state: AgentState) -> dict:
    semaines_restantes = {}
    cadence_recommandee = {}

    for id_tache, deadline in state.deadlines_planning.items():
        semaines = (deadline - state.date_du_jour).days / 7
        semaines_restantes[id_tache] = round(semaines, 2)

        reste = state.reste_a_faire.get(id_tache, 0)
        if reste > 0 and semaines > 0:
            cadence_recommandee[id_tache] = round(reste / semaines, 2)
        # Si semaines <= 0 : échéance déjà dépassée -> pas de cadence
        # lissée pertinente, le statut Critique porte l'alerte à la place
        # (spec section 5.4).

    return {
        "semaines_restantes": semaines_restantes,
        "cadence_recommandee": cadence_recommandee,
    }


# ---------------------------------------------------------------------------
# 7. classer_statut (section 5.5)
# ---------------------------------------------------------------------------


def classer_statut(state: AgentState) -> dict:
    # Cadence historique moyenne de la localité (Jour 3 : lue directement
    # depuis l'état persisté par le Checkpointer — state.historique_cadence,
    # peuplé semaine après semaine via SqliteSaver. Remplace le stub
    # data_access.lire_historique_cadence utilisé au Jour 2, qui renvoyait
    # toujours [] faute de persistance inter-runs ; ce stub reste défini
    # dans data_access.py comme fallback inutilisé.)
    historique = state.historique_cadence
    cadence_moyenne_historique = None
    if historique:
        toutes_cadences = [
            v for h in historique for v in h.reste_a_faire.values()
        ]
        if toutes_cadences:
            cadence_moyenne_historique = sum(toutes_cadences) / len(toutes_cadences)

    a_du_critique = False
    a_du_retard = False

    for id_tache, reste in state.reste_a_faire.items():
        if reste <= 0:
            continue  # tâche terminée, pas d'alerte
        semaines = state.semaines_restantes.get(id_tache)
        if semaines is None:
            continue
        if semaines <= 0:
            a_du_critique = True
            continue
        if semaines <= SEUIL_RETARD_SEMAINES:
            a_du_retard = True
            continue
        if cadence_moyenne_historique:
            cadence = state.cadence_recommandee.get(id_tache, 0)
            if cadence > 1.5 * cadence_moyenne_historique:
                a_du_retard = True

    if a_du_critique:
        statut = "critique"
    elif a_du_retard:
        statut = "retard"
    else:
        statut = "normal"

    return {"statut_alerte": statut}


# ---------------------------------------------------------------------------
# 8. mettre_a_jour_historique (section 7, ajouté Jour 3)
#
# Nœud dédié plutôt que fondu dans generer_section_rapport : responsabilité
# unique (alimenter l'historique persisté), et place explicitement l'écriture
# APRÈS classer_statut, qui doit lire l'historique existant avant qu'il soit
# mis à jour (cf. section 6.2 du résumé de reprise). L'entrée ajoutée ici est
# ce que la semaine suivante trouvera dans state.historique_cadence via le
# Checkpointer (SqliteSaver à partir de cette même journée).
# ---------------------------------------------------------------------------


def mettre_a_jour_historique(state: AgentState) -> dict:
    nouvelle_entree = HistoriqueCadenceEntry(
        semaine=state.date_du_jour.isoformat(),
        reste_a_faire=state.reste_a_faire,
    )
    return {"historique_cadence": state.historique_cadence + [nouvelle_entree]}


# ---------------------------------------------------------------------------
# 9. generer_section_rapport (section 9)
# ---------------------------------------------------------------------------


def generer_section_rapport(state: AgentState) -> dict:
    taches_ref = data_access.get_taches_reference().set_index("ID_Tache")

    # Priorise les tâches au poids le plus élevé (section 5.3), ne montre
    # que celles avec un reste à faire réel.
    lignes_taches = [
        (id_tache, reste)
        for id_tache, reste in state.reste_a_faire.items()
        if reste > 0
    ]
    lignes_taches.sort(
        key=lambda t: taches_ref.loc[t[0], "Poids"] if t[0] in taches_ref.index else 0,
        reverse=True,
    )

    departement = data_access.get_departement_localite(state.id_localite) or "?"

    en_tete = (
        f"### {state.id_localite} ({departement}) — statut : "
        f"**{state.statut_alerte.upper()}**"
    )
    lignes = [en_tete, "", "| Tâche | Reste | Semaines rest. | Cadence/sem. |", "|---|---:|---:|---:|"]

    for id_tache, reste in lignes_taches:
        semaines = state.semaines_restantes.get(id_tache)
        cadence = state.cadence_recommandee.get(id_tache)
        semaines_str = f"{semaines:.1f}" if semaines is not None else "?"
        if semaines is not None and semaines <= 0:
            semaines_str = "délai dépassé"
            cadence_str = "à traiter en urgence"
        else:
            cadence_str = f"{cadence:.1f}/semaine" if cadence is not None else "?"
        nom_tache = taches_ref.loc[id_tache, "Nom_Tache"] if id_tache in taches_ref.index else id_tache
        lignes.append(f"| {nom_tache} | {reste:.0f} | {semaines_str} | {cadence_str} |")

    if not lignes_taches:
        lignes.append("| *(aucune tâche avec reste à faire)* | | | |")

    if state.erreurs:
        lignes.append("")
        lignes.append("**Anomalies signalées :**")
        for e in state.erreurs:
            lignes.append(f"- {e}")

    return {"section_rapport": "\n".join(lignes)}
