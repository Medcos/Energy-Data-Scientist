"""
Construction des tables pivot P2AE — Jour 1.

Décision de cadrage assumée (documentée dans le rapport d'audit) :
La spécification initiale (section 4 du plan) visait une seule table au grain
Localité x Tâche x Date. En pratique, deux grains distincts coexistent dans les
données sources et ne peuvent pas être fusionnés sans perte d'information :

  - Localité x Tâche x Matériel  : grain natif de Objectifs / Helper_Calcul
    (quantités prévues, réalisées, taux de réalisation) -> alimente le Modèle A
    (ressources).
  - Département x Semaine        : grain natif de Historique_Avnt_Geo
    (avancement HTA/BT observé dans le temps) -> alimente les Modèles B et C
    (avancement, retard).

Plutôt que de forcer un grain unique artificiel (ex. dupliquer l'avancement
hebdomadaire du département sur chaque tâche de chaque localité, ce qui
introduirait une fausse précision), ce module construit donc TROIS tables
complémentaires, explicitement documentées, conformément au principe déjà
énoncé dans le plan : "un point à énoncer clairement dans le README plutôt
qu'à masquer".
"""
from __future__ import annotations
import pandas as pd
import numpy as np

# Dates de chantier par département, lues sur le planning contractuel
# LRA_P2AE_Phase1/Lot1 (lignes de synthèse 6.1 à 6.4 du Gantt).
GANTT_DEPARTEMENTS = {
    "ATACORA": {"debut": "2024-11-18", "fin_contractuelle": "2026-08-15"},
    "ALIBORI": {"debut": "2024-11-18", "fin_contractuelle": "2026-09-19"},
    "DONGA":   {"debut": "2024-11-18", "fin_contractuelle": "2026-05-29"},
    "BORGOU":  {"debut": "2024-11-18", "fin_contractuelle": "2026-11-14"},
}


def build_table_ressources_detail(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Table pivot A — grain Localité x Tâche x Matériel.

    Base : Helper_Calcul (déjà la jointure Objectifs x Localités x Tâches,
    avec quantités prévues/réalisées et avancement pondéré). Enrichie avec :
    - Département / Commune / Statut / Avancement global de la localité (Top_Localites)
    - Unité de mesure du matériel (Catalogue_Materiel, jointure via ID_Materiel)
    - ID_Materiel (récupéré depuis Objectifs, absent de Helper_Calcul)

    C'est la table la plus directement exploitable pour le Modèle A
    (quantité restante à livrer par localité x tâche).
    """
    helper = sheets["Helper_Calcul"].copy()
    objectifs = sheets["Objectifs"].dropna(subset=["ID_Objectif"]).copy()
    top_loc = sheets["Top_Localites"].copy()
    catalogue = sheets["Catalogue_Materiel"][["ID_Materiel", "Unite"]].copy()

    # Recoller ID_Materiel (présent dans Objectifs, absent de Helper_Calcul)
    table = helper.merge(
        objectifs[["ID_Objectif", "ID_Materiel"]], on="ID_Objectif", how="left"
    )
    table = table.merge(catalogue, on="ID_Materiel", how="left")

    # Enrichissement localité (département/commune/statut/avancement global)
    top_loc_cols = top_loc[
        ["ID_Localite", "Departement", "Commune", "Statut",
         "Avancement_HTA_%", "Avancement_BT_%", "Avancement"]
    ].rename(columns={
        "Avancement_HTA_%": "Avancement_HTA_Localite_pct",
        "Avancement_BT_%": "Avancement_BT_Localite_pct",
        "Avancement": "Avancement_Global_Localite_pct",
    })
    # Top_Localites est en fraction (0-1) -> standardiser en pourcentage (0-100)
    # pour cohérence avec Historique_Avnt_Geo (voir audit, section "pièges").
    for c in ["Avancement_HTA_Localite_pct", "Avancement_BT_Localite_pct",
              "Avancement_Global_Localite_pct"]:
        top_loc_cols[c] = top_loc_cols[c] * 100

    table = table.merge(top_loc_cols, on="ID_Localite", how="left")

    # Reste à livrer (cible naturelle du Modèle A), jamais négatif par construction
    table["Quantite_Restante"] = (table["Qte_Prevue"] - table["Qte_Realisee"]).clip(lower=0)

    # Nombre d'anomalies signalées pour cette localité x tâche (signal de risque)
    anomalies = sheets["Anomalies_Taches"].groupby(["ID_Localite", "Tache"]).size()
    anomalies = anomalies.rename("Nb_Anomalies_Signalees").reset_index()
    table = table.merge(
        anomalies, left_on=["ID_Localite", "ID_Tache"],
        right_on=["ID_Localite", "Tache"], how="left"
    ).drop(columns=["Tache"])
    table["Nb_Anomalies_Signalees"] = table["Nb_Anomalies_Signalees"].fillna(0).astype(int)

    colonnes_finales = [
        "ID_Helper", "ID_Objectif", "ID_Localite", "Localite", "Departement", "Commune",
        "ID_Tache", "Categorie", "Designation", "ID_Materiel", "Unite",
        "Qte_Prevue", "Qte_Realisee", "Quantite_Restante", "Taux_Realisation",
        "Poids", "Qte_Prevue_Total", "Avancement_Pondere",
        "Statut", "Avancement_HTA_Localite_pct", "Avancement_BT_Localite_pct",
        "Avancement_Global_Localite_pct", "Nb_Anomalies_Signalees",
    ]
    return table[colonnes_finales].sort_values(["Departement", "Localite", "ID_Tache"]).reset_index(drop=True)


def build_table_ressources_temporelle(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Table pivot B — grain Localité x Tâche x Date.

    Reconstruit, à partir du journal `Details_Intervention`, la trajectoire
    cumulée de réalisation par (localité, tâche) au fil du temps, comparée à
    l'objectif prévu (agrégé au niveau tâche, tous matériels confondus).

    Note méthodologique : `Quantite_Nette_Calculee` est utilisée plutôt que
    `Quantite` brute, car elle absorbe correctement les deux modes de saisie
    terrain identifiés à l'audit (saisie incrémentale du jour vs. cumul total
    resaisi) en une seule quantité nette comparable d'une ligne à l'autre.
    """
    di = sheets["Details_Intervention"].dropna(subset=["ID_Detail"]).copy()
    objectifs = sheets["Objectifs"].dropna(subset=["ID_Objectif"]).copy()

    # Objectif agrégé au grain Localité x Tâche (somme sur les matériels)
    qte_prevue_tache = (
        objectifs.groupby(["ID_Localite", "ID_Tache"])["Quantite_Prevue"]
        .sum()
        .rename("Qte_Prevue_Tache")
        .reset_index()
    )

    # Réalisation nette quotidienne, agrégée au grain Localité x Tâche x Date
    quotidien = (
        di.groupby(["ID_Localite", "Localite", "Tache", "Date"])["Quantite_Nette_Calculee"]
        .sum()
        .rename("Quantite_Nette_Jour")
        .reset_index()
        .rename(columns={"Tache": "ID_Tache"})
        .sort_values(["ID_Localite", "ID_Tache", "Date"])
    )

    # Cumul réalisé dans le temps, par (localité, tâche)
    quotidien["Quantite_Cumulee_Realisee"] = (
        quotidien.groupby(["ID_Localite", "ID_Tache"])["Quantite_Nette_Jour"].cumsum()
    )

    table = quotidien.merge(qte_prevue_tache, on=["ID_Localite", "ID_Tache"], how="left")
    table["Taux_Realisation_Tache"] = (
        table["Quantite_Cumulee_Realisee"] / table["Qte_Prevue_Tache"]
    ).clip(upper=1.5)  # tolère un léger dépassement mais signale toute valeur aberrante
    table["Quantite_Restante_Tache"] = (
        table["Qte_Prevue_Tache"] - table["Quantite_Cumulee_Realisee"]
    ).clip(lower=0)

    # Département (via Localités) + jours écoulés depuis le début officiel du chantier
    loc = sheets["Localités"][["ID_Localite", "Nom_Geo_1"]].rename(columns={"Nom_Geo_1": "Departement"})
    table = table.merge(loc, on="ID_Localite", how="left")
    table["Jours_Ecoules_Depuis_Debut_Chantier"] = table.apply(
        lambda r: (r["Date"] - pd.Timestamp(GANTT_DEPARTEMENTS.get(r["Departement"], {}).get("debut", "2024-11-18"))).days,
        axis=1,
    )

    colonnes_finales = [
        "ID_Localite", "Localite", "Departement", "ID_Tache", "Date",
        "Jours_Ecoules_Depuis_Debut_Chantier",
        "Quantite_Nette_Jour", "Quantite_Cumulee_Realisee",
        "Qte_Prevue_Tache", "Quantite_Restante_Tache", "Taux_Realisation_Tache",
    ]
    return table[colonnes_finales].reset_index(drop=True)


def build_table_avancement_departement_semaine(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Table pivot C — grain Département x Semaine.

    Base : Historique_Avnt_Geo (avancement HTA/BT observé chaque semaine).
    Enrichie avec la trajectoire théorique linéaire (section 4.2 du plan) entre
    le début officiel du chantier et la date de fin contractuelle du Gantt, et
    l'écart observé/théorique qui alimentera la cible de retard (Modèle C, à
    construire en Jour 3).
    """
    hist = sheets["Historique_Avnt_Geo"].copy()
    hist = hist.rename(columns={"Localite": "Departement"})
    hist["Departement"] = hist["Departement"].str.upper()

    def trajectoire_theorique(row):
        cfg = GANTT_DEPARTEMENTS.get(row["Departement"])
        if cfg is None:
            return np.nan
        debut = pd.Timestamp(cfg["debut"])
        fin = pd.Timestamp(cfg["fin_contractuelle"])
        if row["Semaine"] <= debut:
            return 0.0
        if row["Semaine"] >= fin:
            return 100.0
        return 100.0 * (row["Semaine"] - debut).days / (fin - debut).days

    hist["Avancement_Theorique_Global_pct"] = hist.apply(trajectoire_theorique, axis=1)
    hist["Ecart_Avancement_Global_pct"] = hist["Avancement"] - hist["Avancement_Theorique_Global_pct"]

    hist["Jours_Ecoules_Depuis_Debut_Chantier"] = hist.apply(
        lambda r: (r["Semaine"] - pd.Timestamp(GANTT_DEPARTEMENTS[r["Departement"]]["debut"])).days
        if r["Departement"] in GANTT_DEPARTEMENTS else np.nan,
        axis=1,
    )
    hist["Jours_Avant_Fin_Contractuelle"] = hist.apply(
        lambda r: (pd.Timestamp(GANTT_DEPARTEMENTS[r["Departement"]]["fin_contractuelle"]) - r["Semaine"]).days
        if r["Departement"] in GANTT_DEPARTEMENTS else np.nan,
        axis=1,
    )

    colonnes_finales = [
        "Departement", "Semaine", "Num_Semaine",
        "Jours_Ecoules_Depuis_Debut_Chantier", "Jours_Avant_Fin_Contractuelle",
        "Avancement_HTA_%", "Avancement_BT_%", "Avancement",
        "Avancement_Theorique_Global_pct", "Ecart_Avancement_Global_pct",
    ]
    return hist[colonnes_finales].sort_values(["Departement", "Semaine"]).reset_index(drop=True)
