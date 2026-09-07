"""
Anonymisation des données ElecTrack Pro.

Périmètre couvert (identifié lors de l'audit des 29 feuilles, Jour 1) :
- Emails d'agents terrain (7 valeurs uniques, présentes dans 6 feuilles)
- Noms complets associés à ces emails
- Numéros de téléphone
- Coordonnées GPS précises (sites d'intervention, bases-vie)

Principe : un mapping unique email -> agent_id est construit une seule fois à partir
de la feuille `Utilisateurs` (qui liste les 7 comptes), puis appliqué de façon
cohérente à toutes les feuilles qui référencent ces emails. Cela garantit qu'un même
agent porte le même identifiant partout (traçabilité analytique préservée sans PII).
"""
from __future__ import annotations
import pandas as pd

# Colonnes contenant un email, par feuille
EMAIL_COLUMNS = {
    "Utilisateurs": "Email",
    "Roles": "Email",
    "Utilisateurs_Projets": "Email_User",
    "Filtre_Performance": "Email_Utilisateur",
    "Interventions": "Utilisateur",
    "Journal_Chantier": "Utilisateur",
}

# Colonnes à supprimer purement (PII sans valeur analytique suffisante pour la justifier)
COLUMNS_TO_DROP = {
    "Utilisateurs": ["Telephone", "Nom_Complet"],
    "Roles": ["Nom_Complet"],
    "Filtre_Performance": ["Nom_Complet"],
    "Localités": ["Coordonnees_GPS"],
    "Interventions": ["Coordonnees_GPS"],
    "Journal_Chantier": ["Localisation"],
}


def build_email_mapping(sheets: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Construit le mapping email -> agent_id à partir de la feuille Utilisateurs.

    L'ordre de la feuille Utilisateurs est préservé (l'Admin du projet devient
    logiquement agent_01), ce qui donne un mapping stable et lisible.
    """
    emails_ordonnes = list(sheets["Utilisateurs"]["Email"].dropna().unique())

    # Sécurité : inclure aussi tout email qui apparaîtrait ailleurs mais pas dans
    # Utilisateurs (ne devrait pas arriver, mais on ne veut jamais laisser un email
    # brut passer faute de mapping).
    autres_emails = set()
    for feuille, col in EMAIL_COLUMNS.items():
        if feuille in sheets and col in sheets[feuille].columns:
            autres_emails.update(sheets[feuille][col].dropna().unique())
    for e in sorted(autres_emails):
        if e not in emails_ordonnes:
            emails_ordonnes.append(e)

    return {email: f"agent_{i+1:02d}" for i, email in enumerate(emails_ordonnes)}


def anonymize_sheets(
    sheets: dict[str, pd.DataFrame], email_mapping: dict[str, str]
) -> dict[str, pd.DataFrame]:
    """Retourne une copie anonymisée des feuilles. Les feuilles sans PII sont
    passées telles quelles (aucune donnée personnelle à traiter)."""
    anon = {name: df.copy() for name, df in sheets.items()}

    # 1) Remplacement des emails par un agent_id stable, colonne renommée `agent_id`
    rename_map = {
        "Utilisateurs": {"Email": "agent_id"},
        "Roles": {"Email": "agent_id"},
        "Utilisateurs_Projets": {"Email_User": "agent_id"},
        "Filtre_Performance": {"Email_Utilisateur": "agent_id"},
        "Interventions": {"Utilisateur": "agent_id"},
        "Journal_Chantier": {"Utilisateur": "agent_id"},
    }
    for feuille, mapping in rename_map.items():
        if feuille in anon:
            for old, new in mapping.items():
                if old in anon[feuille].columns:
                    anon[feuille][old] = anon[feuille][old].map(email_mapping).fillna(
                        anon[feuille][old]
                    )
                    anon[feuille] = anon[feuille].rename(columns={old: new})

    # 2) Suppression des colonnes PII sans mapping (téléphone, noms, GPS précis)
    for feuille, cols in COLUMNS_TO_DROP.items():
        if feuille in anon:
            existantes = [c for c in cols if c in anon[feuille].columns]
            anon[feuille] = anon[feuille].drop(columns=existantes)

    return anon


# ----------------------------------------------------------------------------
# Pseudonymisation des localités/communes — décision D5 (reports/cadrage_jour1.md)
#
# Contrairement aux emails/GPS (PII au sens strict, traité ci-dessus), les noms
# de localités et communes sont des données publiques (divisions administratives
# du Bénin). Leur pseudonymisation répond à un risque différent : la
# confidentialité contractuelle/institutionnelle d'un marché financé par un
# bailleur international, une fois croisées avec des données de performance
# nommées (avancement, retard, anomalies). Les départements restent en clair
# (information déjà publique de l'existence du projet dans ces 4 départements).
# ----------------------------------------------------------------------------
def build_locality_pseudonym_mapping(localites: list[str]) -> dict[str, str]:
    """Construit un mapping localité réelle -> pseudonyme stable (Localite_A, B...).

    Ordre alphabétique des noms réels pour un mapping déterministe et
    reproductible (même entrée -> même pseudonyme à chaque exécution).
    """
    noms_ordonnes = sorted(set(localites))
    if len(noms_ordonnes) <= 26:
        lettres = [chr(65 + i) for i in range(len(noms_ordonnes))]
        return {nom: f"Localite_{l}" for nom, l in zip(noms_ordonnes, lettres)}
    return {nom: f"Localite_{i+1:03d}" for i, nom in enumerate(noms_ordonnes)}


def build_commune_pseudonym_mapping(communes: list[str]) -> dict[str, str]:
    """Idem pour les communes (Commune_A, B...)."""
    noms_ordonnes = sorted(set(communes))
    lettres = [chr(65 + i) for i in range(len(noms_ordonnes))]
    return {nom: f"Commune_{l}" for nom, l in zip(noms_ordonnes, lettres)}


def pseudonymize_table(
    df: pd.DataFrame,
    mapping_localite: dict[str, str],
    mapping_commune: dict[str, str],
    col_localite: str = "Localite",
    col_commune: str = "Commune",
) -> pd.DataFrame:
    """Retourne une copie de df avec les colonnes localité/commune pseudonymisées.

    Le Département n'est jamais touché (décision D5 : information publique).
    Les colonnes ID_Localite (codes déjà opaques type 'ATA_Nat_08') sont
    laissées telles quelles : elles n'exposent pas de nom en clair, et les
    conserver permet de recouper les tables publiques entre elles.
    """
    out = df.copy()
    if col_localite in out.columns:
        out[col_localite] = out[col_localite].map(mapping_localite).fillna(out[col_localite])
    if col_commune in out.columns:
        out[col_commune] = out[col_commune].map(mapping_commune).fillna(out[col_commune])
    return out


def audit_pii(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Petit rapport listant, feuille par feuille, les colonnes jugées sensibles."""
    lignes = []
    pii_cols_connues = set()
    for feuille, col in EMAIL_COLUMNS.items():
        pii_cols_connues.add((feuille, col))
    for feuille, cols in COLUMNS_TO_DROP.items():
        for c in cols:
            pii_cols_connues.add((feuille, c))

    for feuille, col in sorted(pii_cols_connues):
        if feuille in sheets and col in sheets[feuille].columns:
            n_non_nul = sheets[feuille][col].notna().sum()
            lignes.append(
                {
                    "Feuille": feuille,
                    "Colonne": col,
                    "Type_PII": "email" if "mail" in col.lower() or col == "Utilisateur" else
                                ("GPS" if "GPS" in col or col == "Localisation" else
                                 ("téléphone" if col == "Telephone" else "nom")),
                    "Valeurs_non_nulles": int(n_non_nul),
                    "Traitement": "email -> agent_id" if (feuille, col) in
                                  [(f, c) for f, c in EMAIL_COLUMNS.items()] else "colonne supprimée",
                }
            )
    return pd.DataFrame(lignes)
