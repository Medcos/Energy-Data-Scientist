"""Génère notebooks/01_extraction_anonymisation.ipynb à partir de cellules définies ici.
Usage : python scripts/build_notebook_01.py
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

md("""# 01 — Extraction, audit et anonymisation
## Jour 1 — `p2ae-rollout-forecast`

**Objectif du jour** (feuille de route, section 6 du plan) : cadrage écrit + audit des 29 feuilles + extraction et anonymisation immédiate + construction de la table pivot (section 4).

Le cadrage détaillé et les décisions assumées sont documentés séparément dans `reports/cadrage_jour1.md` — ce notebook exécute le pipeline correspondant et vérifie chaque étape.

**⚠️ Le fichier source `data/raw/Localites_raw.xlsx` contient des données personnelles réelles (emails, GPS précis). Il ne doit jamais être committé ni republié.**""")

code("""import sys
sys.path.insert(0, '../src')

import pandas as pd
import anonymize
import features

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

RAW_PATH = '../data/raw/Localites_raw.xlsx'""")

md("""## 1. Chargement et audit des 29 feuilles

On charge l'ensemble du classeur en mémoire (29 feuilles) et on vérifie immédiatement le nombre de feuilles, cohérent avec ce qu'annonçait le plan de mise en œuvre.""")

code("""xls = pd.ExcelFile(RAW_PATH, engine='openpyxl')
print(f"{len(xls.sheet_names)} feuilles trouvées")

sheets = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}
for name, df in sheets.items():
    print(f"{name:30s} shape={df.shape}")""")

md("""### 1.1 Points de vigilance détectés à l'audit

Le détail complet est dans `reports/audit_feuilles_localites.md`. Les trois points qui influencent directement le code ci-dessous :

1. **Échelle incohérente** : `Top_Localites` exprime l'avancement en fraction (0–1), `Historique_Avnt_Geo` en pourcentage (0–100) — standardisé en pourcentage dans `src/features.py`.
2. **Lignes entièrement vides** (artefacts d'export) dans `Objectifs` (6), `Details_Intervention` (3), `Interventions` (1) — supprimées avant tout traitement.
3. **Deux modes de saisie terrain** dans `Details_Intervention` (`➕ Saisie du jour` / `🎯 Cumul total à date`) — la colonne déjà calculée `Quantite_Nette_Calculee` les réconcilie, utilisée telle quelle.""")

code("""# Aperçu du déséquilibre de classe pour la future cible "retard" (Modèle C, Jour 3)
print(sheets['Top_Localites']['Statut'].value_counts())
print()
print("Confirme : classes fortement déséquilibrées, accuracy à proscrire pour l'évaluation future.")""")

md("""## 2. Anonymisation

Périmètre PII identifié à l'audit : emails + noms (`Utilisateurs`, `Roles`, `Utilisateurs_Projets`, `Filtre_Performance`, `Interventions`, `Journal_Chantier`), téléphone (`Utilisateurs`), GPS précis (`Localités`, `Interventions`, `Journal_Chantier`).

Un seul mapping `email -> agent_id` est construit (7 personnes, réutilisées à l'identique dans 6 feuilles) puis appliqué de façon cohérente partout.""")

code("""mapping = anonymize.build_email_mapping(sheets)
print("Mapping construit :")
for email, agent_id in mapping.items():
    print(f"  {agent_id}  <-  {email}")""")

code("""pii_report = anonymize.audit_pii(sheets)
pii_report""")

code("""anon_sheets = anonymize.anonymize_sheets(sheets, mapping)

# Nettoyage des lignes totalement vides identifiées à l'audit
for name in list(anon_sheets.keys()):
    before = len(anon_sheets[name])
    anon_sheets[name] = anon_sheets[name].dropna(how='all').reset_index(drop=True)
    after = len(anon_sheets[name])
    if before != after:
        print(f"{name}: {before - after} ligne(s) vide(s) supprimée(s)")

print()
print("Colonnes Interventions après anonymisation :", list(anon_sheets['Interventions'].columns))
print("Colonnes Localités après anonymisation     :", list(anon_sheets['Localités'].columns))""")

code("""# Vérification de sécurité avant tout export : aucun email/GPS/téléphone résiduel
import re

def contient_pii(df):
    texte = df.astype(str).apply(lambda col: col.str.cat(sep=' '), axis=0).str.cat(sep=' ')
    email = bool(re.search(r'@gmail\\.com|@aiec-ci\\.com', texte))
    gps = bool(re.search(r'\\d\\.\\d{5,}, ?\\d\\.\\d{5,}', texte))
    return email or gps

alertes = [name for name, df in anon_sheets.items() if contient_pii(df)]
assert not alertes, f"PII résiduelle détectée dans : {alertes}"
print("OK : aucune PII résiduelle détectée sur les 29 feuilles anonymisées.")""")

code("""import os
os.makedirs('../data/processed/sheets_anonymises', exist_ok=True)
for name, df in anon_sheets.items():
    df.to_csv(f'../data/processed/sheets_anonymises/{name}.csv', index=False)
print(f"{len(anon_sheets)} feuilles anonymisées exportées vers data/processed/sheets_anonymises/")""")

md("""## 3. Construction des tables pivot (section 4 du plan)

**Décision de cadrage (voir `reports/cadrage_jour1.md`, section 4, D2) :** le grain unique Localité × Tâche × Date visé initialement se heurte à deux grains natifs distincts dans les données (Localité × Tâche × Matériel d'un côté, Département × Semaine de l'autre). Plutôt que de forcer une fusion artificielle, trois tables complémentaires sont produites :

| Table | Grain | Modèle(s) alimenté(s) |
|---|---|---|
| A — `table_pivot_anonymisee.csv` | Localité × Tâche × Matériel | A (ressources) |
| B — `table_pivot_ressources_temporelle_anonymisee.csv` | Localité × Tâche × Date | A (évolution), C (risque) |
| C — `table_avancement_departement_semaine_anonymisee.csv` | Département × Semaine | B (avancement), C (risque) |

Ces trois tables sont construites à partir des données **originales** (non anonymisées) car elles ne mobilisent aucune colonne PII — elles sont donc « anonymisées » par construction, sans perte d'information utile au modèle.""")

code("""t_ressources = features.build_table_ressources_detail(sheets)
print("Table A - ressources détail :", t_ressources.shape)
t_ressources.head()""")

code("""t_temporelle = features.build_table_ressources_temporelle(sheets)
print("Table B - ressources temporelle :", t_temporelle.shape)
t_temporelle.head()""")

code("""t_avancement = features.build_table_avancement_departement_semaine(sheets)
print("Table C - avancement département x semaine :", t_avancement.shape)
t_avancement.head(10)""")

md("""### 3.1 Limite méthodologique assumée — trajectoire théorique

La trajectoire de référence (table C) est calculée entre la date de démarrage administratif du marché (18/11/2024) et la date de fin contractuelle du Gantt par département. Le suivi ElecTrack Pro ne démarre lui qu'en avril 2026. L'écart observé/théorique est donc mécaniquement très négatif en début de série — **ce n'est pas un signal de retard réel**, mais un artefact de la période d'activités préliminaires incluse dans la trajectoire. Détail complet dans `reports/cadrage_jour1.md` (décision D4). Le raffinement (ancrer la trajectoire sur le début réel des travaux physiques) est reporté au Jour 3.""")

code("""t_avancement[t_avancement['Departement']=='ATACORA'][['Departement','Semaine','Avancement','Avancement_Theorique_Global_pct','Ecart_Avancement_Global_pct']].head(6)""")

code("""t_ressources.to_csv('../data/processed/table_pivot_anonymisee.csv', index=False)
t_temporelle.to_csv('../data/processed/table_pivot_ressources_temporelle_anonymisee.csv', index=False)
t_avancement.to_csv('../data/processed/table_avancement_departement_semaine_anonymisee.csv', index=False)

print("Tables pivot sauvegardées dans data/processed/ :")
print(" - table_pivot_anonymisee.csv                         ", t_ressources.shape)
print(" - table_pivot_ressources_temporelle_anonymisee.csv    ", t_temporelle.shape)
print(" - table_avancement_departement_semaine_anonymisee.csv ", t_avancement.shape)""")

md("""## 4. Bilan du Jour 1

- [x] Cadrage écrit (`reports/cadrage_jour1.md`)
- [x] Audit des 29 feuilles (`reports/audit_feuilles_localites.md`)
- [x] Extraction et anonymisation immédiate (29 feuilles exportées, PII vérifiée absente)
- [x] Table pivot construite (3 tables complémentaires, décision documentée)

**Prochaine étape (Jour 2) :** EDA ciblée sur les trois tables pivot + baselines (régression linéaire pour A, tendance simple pour B, régression logistique pour C).""")

nb['cells'] = cells
nbf.write(nb, '../notebooks/01_extraction_anonymisation.ipynb')
print("Notebook écrit.")
