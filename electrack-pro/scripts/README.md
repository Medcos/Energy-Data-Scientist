# Scripts Apps Script — ElecTrack Pro

Sélection de scripts de production, tels qu'exécutés dans le classeur, sans aucune modification de logique. Deux références résiduelles à des données client réelles ont été neutralisées avant publication (un préfixe de projet dans un commentaire, et un nom de localité dans un exemple) ; le reste était déjà conforme à la règle interne "aucun préfixe/nom client codé en dur" (voir `docs/lessons-learned.md`).

| Script | Rôle | Déclencheur |
|---|---|---|
| `Snapshot_HelperCalcul.gs` | Recalcule l'avancement pondéré par localité en une passe, écrit en valeurs statiques (remplace une chaîne de formules volatiles) | Toutes les 30 min |
| `Alerte_Inactivite.gs` | Détecte les chantiers sans activité au-delà d'un seuil configurable par projet, alerte les rôles concernés par email | Hebdomadaire (lundi) |
| `Alerte_Anomalie.gs` | Détecte les matériels enregistrés sur le terrain mais absents des objectifs prévus, alerte et marque la ligne traitée | Quotidien |
| `Snapshot_Gestion_TopLocalitesTri.gs` | Maintient les identifiants et le rang de tri d'une table en lecture seule côté application, avec nettoyage défensif des incohérences | Toutes les 30 min |
| `Snapshot_Comparaison_Referentiels.gs` | Détecte les renommages de référentiels effectués hors Google Sheets (ex. via l'application mobile) et déclenche la même propagation qu'un renommage natif | Toutes les 15 min |
| `Gestion_UtilisateursProjets.gs` | Provisionne automatiquement la table de jonction utilisateur↔projet à partir des affectations saisies, et signale (sans jamais supprimer) les rattachements incohérents ou orphelins | Quotidien (4h) |
| `OnEdit_Propagation_Referentiels.gs` | Propage en temps réel tout renommage d'une valeur de référence (géographie, catégories, matériel...) vers ses copies dénormalisées, avec garde-fous sur les éditions multi-cellules et les valeurs effacées | Déclencheur `onEdit` installable |
| `Retrait_Referentiels.gs` | Gère la désactivation sécurisée (jamais la suppression physique par défaut) d'une valeur de référence encore utilisée par des données existantes, avec calcul d'impact et filet de sécurité anti-suppression accidentelle | Appel manuel + déclencheur `onChange` |
| `Snapshot_Geo.gs` | Calcule et historise les moyennes d'avancement (HTA/BT/global) par zone géographique, semaine par semaine, à partir des localités déjà agrégées | Hebdomadaire (mardi) + rafraîchissement quotidien de la semaine en cours |

## Conventions communes visibles dans ces fichiers

- **Configuration par projet, jamais codée en dur** : rôles destinataires, seuils d'alerte, nom de projet — tous lus depuis une table de configuration (`Projets_Config`), avec repli explicite si absente
- **Verrouillage d'exécution** (`LockService`) pour éviter les collisions entre passages d'un même trigger
- **Wrapper de réessai** (`avecRetry`) sur les lectures Google Sheets, pour absorber les erreurs serveur transitoires
- **Écriture en une seule passe**, uniquement si un changement réel est détecté (comparaison de signature ou de compteur de lignes)
- **Lecture des colonnes par nom d'en-tête**, jamais par lettre — un script reste valide si l'ordre des colonnes change
- **Jamais de suppression automatique de données utilisateur** — `Gestion_UtilisateursProjets.gs` et `Retrait_Referentiels.gs` signalent systématiquement par email plutôt que d'agir seuls sur une décision à impact humain
- **Fonctions `debug*()` en lecture seule** livrées à côté de chaque script principal, pour valider le comportement avant tout déclenchement automatique

## Comment ces scripts s'articulent entre eux

`OnEdit_Propagation_Referentiels.gs` et `Snapshot_Comparaison_Referentiels.gs` illustrent un point d'architecture qui revient souvent en entretien technique : un déclencheur `onEdit`, même installable, ne se déclenche **jamais** pour une écriture faite par programmation — ce qui inclut toute modification faite depuis l'application mobile AppSheet. Plutôt que de contourner cette limite, le second script comble le trou par comparaison périodique, en réutilisant la même fonction de propagation (`_traiterRenommage()`) que le premier — même comportement, mêmes emails, peu importe la source de la modification.

## Non inclus dans cette sélection

Un script de snapshot général existe dans le projet mais n'a pas été retenu ici — il recoupe la logique déjà illustrée par les scripts ci-dessus.
