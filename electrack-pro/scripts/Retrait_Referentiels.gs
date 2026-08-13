/**
 * Retrait_Referentiels.gs
 * ================================================================
 * Gestion de la SUPPRESSION (retrait) de valeurs dans les
 * référentiels suivants, sans casser l'application :
 *   - Geo_Config      (clé : ID_Geo)
 *   - Localités       (clé : ID_Localite)
 *   - Categories_Taches (clé : Categorie — pas d'ID stable, dette
 *     technique connue, gérée en mode "texte")
 *   - Type_Travaux    (clé : Type_Travaux — idem, mode "texte")
 *   - Catalogue_Materiel (clé : ID_Materiel)
 *
 * PRINCIPE (généralisé à partir d'un cas de retrait de localité
 * traité manuellement précédemment) :
 *   Une valeur de référence encore utilisée par des données réelles
 *   NE DOIT JAMAIS être supprimée physiquement (Is_Part_Of n'étant
 *   pas activé, cela orphelinerait les lignes filles). Le script :
 *     1. Compte les dépendances dans toutes les tables filles connues.
 *     2. Désactive la ligne (Actif = FALSE) plutôt que la supprimer
 *        — elle disparaît des futures saisies, l'historique reste intact.
 *     3. Supprime physiquement UNIQUEMENT si aucune dépendance n'existe
 *        ET si explicitement demandé (supprimerLigne:true).
 *     4. Envoie un email de rapport à l'Admin et au Chef de Mission.
 *
 * ACTION MANUELLE REQUISE UNE SEULE FOIS (AppSheet Editor, hors de
 * portée d'Apps Script) : pour que les valeurs désactivées
 * disparaissent réellement des listes déroulantes de saisie, filtrer
 * les Valid_If / Suggested values de ces colonnes sur [Actif]=TRUE,
 * par ex. :
 *   Valid_If (Objectifs.ID_Localite) =
 *     IN([_THISROW].[ID_Localite], SELECT(Localités[ID_Localite], [Actif]=TRUE))
 *
 * FILET DE SÉCURITÉ : un déclencheur onChange (configurerDeclencheurOnChange)
 * détecte toute suppression de ligne faite DIRECTEMENT dans l'interface
 * (sans passer par retirerValeurReference) et alerte immédiatement,
 * pour rattraper une erreur humaine (Ctrl+Z encore possible).
 * ================================================================
 */

// ================================================================
// CONFIGURATION — dépendances par référentiel
// ================================================================
const DEPENDANCES_MAP = {

  'Geo_Config.ID_Geo': {
    colonneLabel: 'Nom_Geo_1',
    dependances: [
      { sheet: 'Localités',            colonne: 'ID_Geo' },
      { sheet: 'Objectifs',            colonne: 'ID_Geo' },
      { sheet: 'Interventions',        colonne: 'ID_Geo' },
      { sheet: 'Details_Intervention', colonne: 'ID_Geo' },
      { sheet: 'Journal_Chantier',     colonne: 'ID_Geo' }
    ],
    // Zone_Affectation stocke le LIBELLÉ (Nom_Geo_1) en texte, pas l'ID_Geo
    dependancesTexte: [
      { sheet: 'Utilisateurs', colonne: 'Zone_Affectation' }
    ]
  },

  'Localités.ID_Localite': {
    colonneLabel: 'Localite',
    dependances: [
      { sheet: 'Objectifs',            colonne: 'ID_Localite' },
      { sheet: 'Interventions',        colonne: 'ID_Localite' },
      { sheet: 'Details_Intervention', colonne: 'ID_Localite' },
      { sheet: 'Journal_Chantier',     colonne: 'ID_Localite' }
    ]
  },

  'Categories_Taches.Categorie': {
    colonneLabel: 'Categorie', // la clé EST déjà le libellé (pas d'ID)
    dependances: [
      { sheet: 'Parametres_Poids',   colonne: 'Categorie' },
      { sheet: 'Catalogue_Materiel', colonne: 'Categorie' },
      { sheet: 'Interventions',      colonne: 'Categorie' }
    ]
  },

  'Type_Travaux.Type_Travaux': {
    colonneLabel: 'Type_Travaux',
    dependances: [
      { sheet: 'Catalogue_Materiel', colonne: 'Type_Travaux' },
      { sheet: 'Interventions',      colonne: 'Type_Travaux' }
    ]
  },

  'Catalogue_Materiel.ID_Materiel': {
    colonneLabel: 'Designation',
    dependances: [
      { sheet: 'Objectifs',            colonne: 'ID_Materiel' },
      { sheet: 'Details_Intervention', colonne: 'ID_Materiel' }
    ]
  }
};

// ROLES_DESTINATAIRES n'est PAS redéclaré ici : il est déjà défini en
// const dans OnEdit_Propagation_Referentiels.gs, présent dans le même
// projet Apps Script. Tous les fichiers .gs d'un projet partagent le
// même espace global — redéclarer la même const dans deux fichiers
// provoque une SyntaxError au chargement, avant même l'exécution. Si
// ce fichier est utilisé SEUL (sans OnEdit_Propagation_Referentiels.gs
// dans le projet), décommenter la ligne suivante :
// const ROLES_DESTINATAIRES = ['Admin', 'Chef de Mission'];

// ================================================================
// UTILITAIRES (communs avec les scripts précédents)
// ================================================================

function _trouverIndexColonne(sheet, nomColonne) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const i = headers.indexOf(nomColonne);
  return i === -1 ? -1 : i + 1;
}

function _assurerColonneActif(sheet) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  if (headers.indexOf('Actif') !== -1) return;
  const col = sheet.getLastColumn() + 1;
  sheet.getRange(1, col).setValue('Actif');
  const lastRow = sheet.getLastRow();
  if (lastRow >= 2) {
    sheet.getRange(2, col, lastRow - 1, 1).setValues(Array(lastRow - 1).fill([true]));
  }
  Logger.log('➕ Colonne Actif ajoutée à ' + sheet.getName());
}

function _desactiverLigne(sheet, colCle, valeurCle) {
  _assurerColonneActif(sheet);
  const colCleIdx   = _trouverIndexColonne(sheet, colCle);
  const colActifIdx = _trouverIndexColonne(sheet, 'Actif');
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;
  const cles = sheet.getRange(2, colCleIdx, lastRow - 1, 1).getValues();
  for (let i = 0; i < cles.length; i++) {
    if (String(cles[i][0]).trim() === String(valeurCle).trim()) {
      sheet.getRange(i + 2, colActifIdx).setValue(false);
      return true;
    }
  }
  return false;
}

function _listerDestinataires() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('Utilisateurs');
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return [];
  const data = sh.getRange(2, 1, lastRow - 1, 4).getValues();
  const emails = new Set();
  data.forEach(row => {
    const email = String(row[0]).trim();
    const role  = String(row[2]).trim();
    if (email && ROLES_DESTINATAIRES.indexOf(role) !== -1) emails.add(email);
  });
  return [...emails];
}

// Recherche d'une clé par son libellé humain (pratique pour appeler
// les fonctions ci-dessous sans connaître l'ID technique)
function trouverIdParLibelle(sheetName, colonneId, colonneLibelle, libelle) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(sheetName);
  const colId  = _trouverIndexColonne(sh, colonneId);
  const colLib = _trouverIndexColonne(sh, colonneLibelle);
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return null;
  const data = sh.getRange(2, 1, lastRow - 1, sh.getLastColumn()).getValues();
  for (const row of data) {
    if (String(row[colLib - 1]).trim() === String(libelle).trim()) return row[colId - 1];
  }
  return null;
}

// ================================================================
// RETRAIT GÉNÉRIQUE
// ================================================================

function retirerValeurReference(cle, valeurCle, options) {
  options = options || {};
  const config = DEPENDANCES_MAP[cle];
  if (!config) throw new Error('Référentiel non configuré : ' + cle);

  const [sheetName, colonneCle] = cle.split('.');
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(sheetName);
  if (!sh) throw new Error('Onglet introuvable : ' + sheetName);

  // Libellé humain pour le rapport (si la clé est un ID technique)
  const libelle = colonneCle === config.colonneLabel
    ? valeurCle
    : _recupererValeurColonne(sh, colonneCle, valeurCle, config.colonneLabel) || valeurCle;

  // 1. Dépendances par ID/valeur directe
  const dependances = config.dependances.map(d => _compterDependance(d.sheet, d.colonne, valeurCle));

  // 2. Dépendances "texte" (ex. Zone_Affectation stocke le libellé, pas l'ID)
  const dependancesTexte = (config.dependancesTexte || [])
    .map(d => _compterDependance(d.sheet, d.colonne, libelle, true));

  const toutesDependances = dependances.concat(dependancesTexte);
  const total = toutesDependances.reduce((s, d) => s + d.count, 0);

  Logger.log('📋 Dépendances pour ' + cle + ' = "' + libelle + '" : ' +
    toutesDependances.map(d => d.sheet + '.' + d.colonne + '=' + d.count).join(', ') +
    ' (total ' + total + ')');

  // 3. Désactivation (jamais de suppression physique par défaut)
  const desactive = _desactiverLigne(sh, colonneCle, valeurCle);
  if (!desactive) {
    const msg = 'Valeur introuvable dans ' + cle + ' : "' + valeurCle + '"';
    Logger.log('❌ ' + msg);
    return { succes: false, message: msg };
  }
  Logger.log('✅ Désactivé : ' + cle + ' = "' + libelle + '"' + (total > 0 ? ' (' + total + ' dépendance(s) préservée(s))' : ' (aucune dépendance)'));

  // 4. Suppression physique — uniquement si explicitement demandée
  let supprimePhysiquement = false;
  if (options.supprimerLigne) {
    if (total > 0 && !options.force) {
      Logger.log('⛔ Suppression physique refusée : ' + total + ' dépendance(s) active(s). ' +
        'Relancer avec { force:true } pour forcer (déconseillé — orphelinera des lignes).');
    } else {
      supprimePhysiquement = _supprimerLignePhysique(sh, colonneCle, valeurCle);
      Logger.log((options.force && total > 0 ? '⚠️ Suppression FORCÉE' : '✅ Suppression physique') +
        ' de ' + cle + ' = "' + libelle + '"');
    }
  }

  _envoyerMailRetrait(cle, libelle, toutesDependances, total, desactive, supprimePhysiquement);

  return { succes: true, desactive, supprimePhysiquement, dependances: toutesDependances, total };
}

function _compterDependance(sheetName, colonne, valeurRecherchee, texte) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(sheetName);
  const colIdx = _trouverIndexColonne(sh, colonne);
  const lastRow = sh.getLastRow();
  let n = 0;
  if (lastRow >= 2 && colIdx !== -1) {
    sh.getRange(2, colIdx, lastRow - 1, 1).getValues().forEach(r => {
      if (String(r[0]).trim() === String(valeurRecherchee).trim()) n++;
    });
  }
  return { sheet: sheetName, colonne, count: n, texte: !!texte };
}

function _recupererValeurColonne(sh, colonneCle, valeurCle, colonneCible) {
  const colCleIdx    = _trouverIndexColonne(sh, colonneCle);
  const colCibleIdx  = _trouverIndexColonne(sh, colonneCible);
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return null;
  const data = sh.getRange(2, 1, lastRow - 1, sh.getLastColumn()).getValues();
  for (const row of data) {
    if (String(row[colCleIdx - 1]).trim() === String(valeurCle).trim()) return row[colCibleIdx - 1];
  }
  return null;
}

function _supprimerLignePhysique(sh, colonneCle, valeurCle) {
  const colIdx = _trouverIndexColonne(sh, colonneCle);
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return false;
  const vals = sh.getRange(2, colIdx, lastRow - 1, 1).getValues();
  for (let i = 0; i < vals.length; i++) {
    if (String(vals[i][0]).trim() === String(valeurCle).trim()) {
      sh.deleteRow(i + 2);
      return true;
    }
  }
  return false;
}

// ================================================================
// RACCOURCIS PAR RÉFÉRENTIEL (identification par libellé humain)
// ================================================================

function retirerZoneGeo(nomGeo1, options) {
  const idGeo = trouverIdParLibelle('Geo_Config', 'ID_Geo', 'Nom_Geo_1', nomGeo1);
  if (!idGeo) return { succes: false, message: 'Zone géographique introuvable : ' + nomGeo1 };
  return retirerValeurReference('Geo_Config.ID_Geo', idGeo, options);
}

function retirerLocalite(nomLocalite, options) {
  const idLoc = trouverIdParLibelle('Localités', 'ID_Localite', 'Localite', nomLocalite);
  if (!idLoc) return { succes: false, message: 'Localité introuvable : ' + nomLocalite };
  return retirerValeurReference('Localités.ID_Localite', idLoc, options);
}

function retirerCategorie(nomCategorie, options) {
  return retirerValeurReference('Categories_Taches.Categorie', nomCategorie, options);
}

function retirerTypeTravaux(nomTypeTravaux, options) {
  return retirerValeurReference('Type_Travaux.Type_Travaux', nomTypeTravaux, options);
}

function retirerMateriau(designation, options) {
  const idMat = trouverIdParLibelle('Catalogue_Materiel', 'ID_Materiel', 'Designation', designation);
  if (!idMat) return { succes: false, message: 'Matériau introuvable : ' + designation };
  return retirerValeurReference('Catalogue_Materiel.ID_Materiel', idMat, options);
}

// ================================================================
// EMAIL DE RAPPORT
// ================================================================

function _envoyerMailRetrait(cle, libelle, dependances, total, desactive, supprimePhysiquement) {
  const destinataires = _listerDestinataires();
  if (destinataires.length === 0) {
    Logger.log('❌ Aucun destinataire (Admin/Chef de Mission) trouvé — email non envoyé');
    return;
  }

  const [sheetName, colonne] = cle.split('.');
  const sujet = (supprimePhysiquement ? '🗑️ Suppression' : '🔒 Désactivation') +
    ' de référentiel — ' + sheetName + ' : ' + libelle;

  let corps = 'Bonjour,\n\n';
  corps += 'La valeur suivante n\'est plus prise en compte pour le projet :\n\n';
  corps += '  Onglet  : ' + sheetName + '\n';
  corps += '  Colonne : ' + colonne + '\n';
  corps += '  Valeur  : ' + libelle + '\n\n';

  corps += supprimePhysiquement
    ? '➡️ Action effectuée : SUPPRESSION PHYSIQUE de la ligne (aucune donnée ne dépendait de cette valeur).\n\n'
    : '➡️ Action effectuée : DÉSACTIVATION (Actif = FALSE). La ligne reste dans le classeur ' +
      'pour préserver l\'historique et la cohérence des calculs déjà réalisés.\n\n';

  if (total > 0) {
    corps += '⚠️ ' + total + ' enregistrement(s) existant(s) référencent encore cette valeur ' +
      '(données conservées, aucun impact) :\n';
    dependances.filter(d => d.count > 0).forEach(d => {
      corps += '  • ' + d.sheet + '.' + d.colonne + ' : ' + d.count + ' ligne(s)' +
        (d.texte ? '  [référence texte]' : '') + '\n';
    });
    corps += '\n';
  } else {
    corps += 'Aucun enregistrement existant ne référence cette valeur.\n\n';
  }

  if (!supprimePhysiquement) {
    corps += 'ℹ️ Rappel : si ce n\'est pas déjà fait, filtrer les listes déroulantes AppSheet ' +
      'correspondantes (Valid_If / Suggested values) sur [Actif]=TRUE pour que cette valeur ' +
      'n\'apparaisse plus dans les nouveaux formulaires de saisie.\n\n';
  }

  corps += '— ElecTrack Pro / Gestion des référentiels';

  GmailApp.sendEmail(destinataires.join(','), sujet, corps);
  Logger.log('📧 Email de retrait envoyé à : ' + destinataires.join(', '));
}

// ================================================================
// FILET DE SÉCURITÉ — détection d'une suppression de ligne DIRECTE
// (faite dans l'interface, sans passer par retirerValeurReference)
// ================================================================

function configurerDeclencheurOnChange() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'onModificationStructurelle') {
      ScriptApp.deleteTrigger(t);
      Logger.log('🗑 Supprimé : ancien trigger onModificationStructurelle');
    }
  });

  ScriptApp.newTrigger('onModificationStructurelle')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onChange()
    .create();

  // Initialise les instantanés de référence (pour ne pas déclencher une
  // fausse alerte au premier passage après installation)
  _rafraichirTousLesSnapshots();

  Logger.log('✅ Déclencheur installable "onModificationStructurelle" créé (détection + confirmation des suppressions).');
}

function onModificationStructurelle(e) {
  try {
    if (!e || e.changeType !== 'REMOVE_ROW') return;
    _detecterSuppressionLigneReferentiel();
  } catch (err) {
    Logger.log('❌ onModificationStructurelle — ' + err.message);
  }
}

// ----------------------------------------------------------------
// Instantané (snapshot) de chaque référentiel : mémorise la paire
// {clé technique → libellé} de chaque ligne active, pour pouvoir
// identifier PRÉCISÉMENT quelle valeur a disparu (pas juste "une
// ligne a disparu" comme dans la version précédente basée sur un
// simple comptage de lignes).
// ----------------------------------------------------------------

function _cleSnapshotSheet(cle) {
  return 'SNAPSHOT_REF_' + cle;
}

function _construireSnapshotActuel(sheetName, colonneCle, colonneLabel) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(sheetName);
  if (!sh) return {};
  const colCleIdx   = _trouverIndexColonne(sh, colonneCle);
  const colLabelIdx = _trouverIndexColonne(sh, colonneLabel);
  const lastRow = sh.getLastRow();
  const snapshot = {};
  if (lastRow >= 2 && colCleIdx !== -1) {
    sh.getRange(2, 1, lastRow - 1, sh.getLastColumn()).getValues().forEach(row => {
      const cle = String(row[colCleIdx - 1]).trim();
      if (cle) snapshot[cle] = colLabelIdx !== -1 ? row[colLabelIdx - 1] : cle;
    });
  }
  return snapshot;
}

function _rafraichirTousLesSnapshots() {
  const props = PropertiesService.getScriptProperties();
  Object.keys(DEPENDANCES_MAP).forEach(cle => {
    const [sheetName, colonneCle] = cle.split('.');
    const config = DEPENDANCES_MAP[cle];
    const snapshot = _construireSnapshotActuel(sheetName, colonneCle, config.colonneLabel);
    props.setProperty(_cleSnapshotSheet(cle), JSON.stringify(snapshot));
  });
}

function _detecterSuppressionLigneReferentiel() {
  const props = PropertiesService.getScriptProperties();

  Object.keys(DEPENDANCES_MAP).forEach(cle => {
    const [sheetName, colonneCle] = cle.split('.');
    const config = DEPENDANCES_MAP[cle];

    const snapshotPrecedent = JSON.parse(props.getProperty(_cleSnapshotSheet(cle)) || 'null');
    const snapshotActuel    = _construireSnapshotActuel(sheetName, colonneCle, config.colonneLabel);

    if (snapshotPrecedent) {
      Object.keys(snapshotPrecedent)
        .filter(k => !(k in snapshotActuel))
        .forEach(cleSupprimee => {
          _traiterSuppressionDetectee(sheetName, snapshotPrecedent[cleSupprimee], cleSupprimee, config);
        });
    }

    props.setProperty(_cleSnapshotSheet(cle), JSON.stringify(snapshotActuel));
  });
}

function _traiterSuppressionDetectee(sheetName, libelle, valeurCle, config) {
  Logger.log('⚠️ Suppression directe détectée : ' + sheetName + ' — "' + libelle + '"');

  // Les lignes filles existent toujours et pointent encore vers la
  // valeur qui vient de disparaître : on peut donc évaluer l'impact.
  const dependances = config.dependances.map(d => _compterDependance(d.sheet, d.colonne, valeurCle));
  const dependancesTexte = (config.dependancesTexte || [])
    .map(d => _compterDependance(d.sheet, d.colonne, libelle, true));
  const toutesDependances = dependances.concat(dependancesTexte);
  const total = toutesDependances.reduce((s, d) => s + d.count, 0);

  // Boîte de dialogue de confirmation — si une session UI est active
  // (l'utilisateur qui vient de supprimer a le classeur ouvert).
  const confirmation = _demanderConfirmationUI(sheetName, libelle, total, toutesDependances);

  _envoyerMailAlerteSuppressionDirecte(sheetName, libelle, toutesDependances, total, confirmation);
}

// ----------------------------------------------------------------
// Boîte de dialogue de confirmation
// ----------------------------------------------------------------
// Important : la suppression a déjà eu lieu quand ce message
// s'affiche (Apps Script ne peut pas intercepter une suppression de
// ligne AVANT qu'elle ne se produise). Le rôle de cette boîte est
// donc d'informer immédiatement l'utilisateur de l'impact réel et
// de lui laisser la fenêtre pour annuler lui-même (Ctrl+Z) si besoin
// — pas de bloquer l'action, techniquement impossible ici.
function _demanderConfirmationUI(sheetName, valeur, total, dependances) {
  try {
    const ui = SpreadsheetApp.getUi();
    let message = 'La valeur "' + valeur + '" vient d\'être supprimée de l\'onglet "' + sheetName + '".\n\n';

    if (total > 0) {
      message += '⚠️ ' + total + ' enregistrement(s) existant(s) la référencent encore :\n';
      dependances.filter(d => d.count > 0).forEach(d => {
        message += '  • ' + d.sheet + '.' + d.colonne + ' : ' + d.count + ' ligne(s)\n';
      });
      message += '\nCes lignes vont devenir orphelines (référence cassée, sans erreur visible dans l\'app).\n\n';
    } else {
      message += 'Aucun enregistrement existant ne la référence — suppression sans risque connu.\n\n';
    }

    message += 'Confirmez-vous cette suppression ?\n' +
      '→ "Oui" : suppression actée, un email de confirmation sera envoyé.\n' +
      '→ "Non" : faites Ctrl+Z immédiatement pour l\'annuler.';

    const reponse = ui.alert('⚠️ Confirmation de suppression — ' + sheetName, message, ui.ButtonSet.YES_NO);
    const confirme = reponse === ui.Button.YES;
    Logger.log(confirme ? '✅ Suppression confirmée par l\'utilisateur' : '↩️ Utilisateur invité à annuler (Ctrl+Z)');
    return confirme;

  } catch (err) {
    // Pas de session UI active au moment du déclenchement (ex. édition
    // faite via API, ou déclencheur exécuté en arrière-plan) — on se
    // rabat sur l'email uniquement, sans bloquer le script.
    Logger.log('ℹ️ Boîte de dialogue non disponible (pas de session active) — notification par email uniquement.');
    return null; // indéterminé
  }
}

function _envoyerMailAlerteSuppressionDirecte(sheetName, libelle, dependances, total, confirmation) {
  const destinataires = _listerDestinataires();
  if (destinataires.length === 0) return;

  const statut = confirmation === true  ? '✅ Confirmée par l\'utilisateur dans la boîte de dialogue'
               : confirmation === false ? '↩️ Utilisateur invité à annuler (Ctrl+Z) — à vérifier'
               :                          'ℹ️ Non confirmée (aucune session active au moment de la détection)';

  const sujet = (confirmation === false ? '↩️ ' : '⚠️ ') +
    'Suppression détectée hors procédure — ' + sheetName + ' : ' + libelle;

  let corps = 'Bonjour,\n\n';
  corps += 'Une ligne a été supprimée DIRECTEMENT dans l\'interface, sans passer par ' +
    'la fonction de retrait sécurisé (retirerValeurReference) :\n\n';
  corps += '  Onglet  : ' + sheetName + '\n';
  corps += '  Valeur  : ' + libelle + '\n';
  corps += '  Statut  : ' + statut + '\n\n';

  if (total > 0) {
    corps += '⚠️ ' + total + ' enregistrement(s) existant(s) référencent encore cette valeur ' +
      '— ces lignes sont maintenant potentiellement orphelines :\n';
    dependances.filter(d => d.count > 0).forEach(d => {
      corps += '  • ' + d.sheet + '.' + d.colonne + ' : ' + d.count + ' ligne(s)' +
        (d.texte ? '  [référence texte]' : '') + '\n';
    });
    corps += '\n';
  } else {
    corps += 'Aucun enregistrement existant ne référençait cette valeur — pas d\'impact détecté.\n\n';
  }

  corps += 'Action recommandée : si cette suppression n\'était pas volontaire, restaurez la ligne ' +
    '(Ctrl+Z, ou Fichier > Historique des versions). Si elle était volontaire, préférez à l\'avenir ' +
    'retirerValeurReference() (ou ses raccourcis retirerZoneGeo/retirerLocalite/retirerCategorie/' +
    'retirerTypeTravaux/retirerMateriau) pour un retrait sécurisé qui préserve automatiquement la ' +
    'cohérence des données.\n\n' +
    '— ElecTrack Pro / Gestion des référentiels';

  GmailApp.sendEmail(destinataires.join(','), sujet, corps);
  Logger.log('📧 Email d\'alerte (suppression directe) envoyé à : ' + destinataires.join(', '));
}
