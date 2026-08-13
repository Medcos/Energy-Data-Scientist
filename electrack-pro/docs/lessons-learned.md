# Leçons Apprises — Pièges AppSheet & Apps Script

Ce document rassemble les pièges réels rencontrés en durcissant ElecTrack Pro pour un déploiement commercial multi-client. Chaque entrée est le résultat d'un bug en production, diagnostiqué et corrigé — pas d'une lecture de documentation. Aucune donnée client n'apparaît ci-dessous : les exemples sont génériques.

---

## Pièges AppSheet

### `LOOKUP()` échoue silencieusement sur les colonnes de type Ref

**Symptôme :** une formule `LOOKUP()` pointant vers une colonne de type Ref (référence vers une autre table) retourne systématiquement la première ligne de la table cible, quel que soit l'enregistrement source — même en encadrant la clé avec `TEXT()`.

**Pourquoi c'est dangereux :** l'erreur ne se manifeste pas comme une erreur. La formule renvoie une valeur plausible, souvent correcte pour le premier enregistrement testé — ce qui la fait passer les tests manuels superficiels et n'apparaît qu'en production sur un jeu de données plus large.

**Correction fiable :**
```
ANY(SELECT(Table[colonne_retour], [colonne_clé] = [_THISROW].[colonne_ref]))
```

---

### Conflit App Formula + Initial Value sur une clé dérivée

**Symptôme :** une App Formula qui dérive un identifiant de projet à partir d'une colonne pas encore renseignée au moment de la saisie (ex. avant que l'utilisateur ait choisi la localité) laisse le champ vide au moment critique — ce qui casse silencieusement tous les `Valid_If` et `Suggested_Values` qui en dépendent en aval.

**Correction :** ne conserver **qu'une seule** des deux mécaniques, jamais les deux en simultané. Pour un identifiant qui doit exister dès l'ouverture du formulaire, préférer l'Initial Value seule :
```
ANY(SELECT(Projets_Config[ID_Projet], [Actif] = TRUE))
```

---

### `Suggested_Values` doit être renseigné même si `Valid_If` fonctionne

Un `Valid_If` correct sans `Suggested_Values` correspondant produit un menu déroulant vide côté utilisateur, alors que la validation elle-même fonctionne parfaitement en arrière-plan. Les deux doivent toujours être maintenus en parallèle.

---

### Déduplication dans `SELECT()`

Quand la table source contient plusieurs lignes pour une même valeur logique (ex. plusieurs lignes de configuration géographique par commune), `SELECT()` sans son troisième paramètre `TRUE` retourne des doublons dans la liste de suggestion. Toujours utiliser :
```
SELECT(Table[colonne], [condition], TRUE)
```

---

### Comparaisons booléennes : type strict

`[Actif] = TRUE` fonctionne ; `[Actif] = "TRUE"` échoue silencieusement (comparaison booléen vs chaîne de caractères). Ce piège est particulièrement insidieux dans les filtres de sécurité, où l'échec silencieux se traduit par un accès *trop large*, pas par une erreur visible.

---

### Précision décimale sur les colonnes virtuelles calculées

Une colonne virtuelle de type Pourcentage ou Décimal utilisée comme **entrée** d'un calcul en aval (pas seulement affichée) doit conserver suffisamment de décimales stockées. Un arrondi à 2 décimales sur un poids de tâche a propagé une erreur silencieuse dans une formule d'avancement pondéré dépendante — invisible à l'œil nu, mais mesurable sur des agrégats à grande échelle. Correction : augmenter la précision stockée (4 décimales), pas retoucher la formule de calcul elle-même.

---

### `ISCHANGED()` non supporté dans les conditions de Bot Event

Laisser la condition vide, ou utiliser `ISNOTBLANK()` comme substitut fonctionnel.

---

### Auto-référence circulaire impossible dans une Security Filter

Une table ne peut pas référencer sa propre Security Filter pour se filtrer elle-même (cas typique : filtrer la table des utilisateurs selon le rôle... de l'utilisateur, lui-même stocké dans cette même table). Solution : créer une table miroir en lecture seule (formule `ARRAYFORMULA` recopiant les colonnes nécessaires), et faire pointer la Security Filter vers ce miroir plutôt que vers la table elle-même.

---

### App Formula au-dessus d'une formule Sheet native : ne jamais empiler

Quand un champ est déjà calculé par une formule Google Sheets native (`ARRAYFORMULA`, `RECHERCHEX`) directement dans la feuille, ajouter une App Formula AppSheet par-dessus casse le calcul plutôt que de le compléter. Les deux mécanismes ne coexistent pas proprement sur le même champ.

---

## Conventions Apps Script (règles permanentes)

### Jamais de préfixe client dans le code

Aucun préfixe spécifique à un client dans les noms de fonctions, de variables, ou de fichiers `.gs`. Un préfixe codé en dur est exactement le même anti-pattern qu'une valeur codée en dur dans une formule — dans un produit multi-client, le code doit rester générique. (Incident réel : un déclencheur planifié pointant vers un nom de fonction générique a échoué parce que le code de la fonction utilisait encore l'ancien préfixe.)

### Espace de nommage global partagé

Tous les fichiers `.gs` d'un même projet Apps Script partagent un espace de nommage global unique — une déclaration `const` dupliquée entre deux fichiers provoque une erreur de compilation qui peut être difficile à localiser.

### Apps Script plutôt que les Bots AppSheet pour l'envoi d'email

Les Bots AppSheet en version gratuite envoient tous les emails automatisés au créateur de l'application, pas aux destinataires visés. `GmailApp` via Apps Script contourne cette limitation.

### Verrouillage, écriture en une passe, réessai

- `LockService` pour empêcher les exécutions simultanées d'un même script déclenché
- Écriture groupée (`setValues()`) uniquement quand un changement réel existe — pas d'écriture systématique à chaque exécution, pour préserver le quota Apps Script partagé
- Wrapper de réessai sur toutes les lectures Google Sheets, pour absorber les erreurs transitoires de l'API

### Ne jamais désactiver silencieusement l'historique

Un champ de statut (`Actif`) sur un référentiel (ex. catégorie de tâche) ne doit gouverner **que** les listes déroulantes de saisie — jamais les calculs sur l'historique existant. Désactiver une tâche ne doit pas "zérofier" l'avancement déjà enregistré pour les enregistrements existants qui la référencent. La bonne pratique : continuer à calculer sur les données existantes, et émettre un simple avertissement dans les logs si un enregistrement actif référence un élément de référentiel désactivé.

### Suppression automatique : jamais sur des données utilisateur

Un script de contrôle qui détecte des incohérences (ex. rattachements utilisateur-projet orphelins après désactivation d'un compte) doit **signaler par email**, jamais supprimer automatiquement. La décision de suppression reste humaine.

---

## Pourquoi ce document a de la valeur

Chaque piège ci-dessus a été découvert par un écart mesuré entre un résultat attendu et un résultat observé en production — pas par une lecture de documentation. C'est ce processus de validation systématique (comparaison ligne à ligne avec les données réelles, tests sur copie avant déploiement, vérification en aval sur plusieurs tables consommatrices) qui a permis de les détecter avant qu'ils n'affectent un client final.
