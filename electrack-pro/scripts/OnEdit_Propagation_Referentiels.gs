/**
 * OnEdit_Propagation_Referentiels.gs
 * ================================================================
 * Déclenchement AUTOMATIQUE à chaque modification d'une cellule
 * dans l'une des colonnes de référence suivantes :
 *   - Geo_Config.Nom_Geo_1 / Nom_Geo_2
 *   - Localités.Localite
 *   - Categories_Taches.Categorie
 *   - Type_Travaux.Type_Travaux
 *   - Catalogue_Materiel.Designation
 *
 * À chaque modification détectée :
 *   1. Propage automatiquement l'ancienne → nouvelle valeur dans
 *      toutes les copies dénormalisées connues (texte figé
 *      uniquement — les cellules en formule se corrigent seules).
 *   2. Force un recalcul immédiat de Helper_Calcul si le script
 *      Snapshot_HelperCalcul.gs est présent dans le projet.
 *   3. Envoie un email de confirmation à l'Admin et au Chef de
 *      Mission (rôles lus dynamiquement depuis Utilisateurs).
 *
 * INSTALLATION (à faire UNE SEULE FOIS) :
 *   Exécuter configurerDeclencheurOnEdit() depuis l'éditeur Apps
 *   Script. Un déclencheur simple (onEdit(e) automatique) NE PEUT
 *   PAS envoyer d'email (droits insuffisants) — un déclencheur
 *   installable est donc obligatoire ici.
 *
 * LIMITES CONNUES (documentées, pas contournables techniquement) :
 *   - Édition multi-cellules (collage, import, remplissage) : Google
 *     Sheets ne fournit PAS la valeur précédente de chaque cellule
 *     dans ce cas (e.oldValue est vide). Le script n'essaie donc PAS
 *     de deviner une propagation — il envoie une alerte demandant
 *     une vérification manuelle (script de propagation manuelle :
 *     previsualiserRenommage / appliquerRenommage).
 *   - Categories_Taches.Categorie : les colonnes virtuelles AppSheet
 *     comparent "Travaux HTA"/"Travaux BT" en dur. Le script propage
 *     quand même les copies texte (utile et sans risque), mais
 *     ENVOIE TOUJOURS un avertissement listant l'action manuelle
 *     requise dans AppSheet Editor.
 *   - onEdit (simple ET installable) ne se déclenche JAMAIS pour une
 *     écriture faite par programmation (API Sheets), ce qui inclut
 *     toute modification faite depuis l'interface AppSheet. Ce trou
 *     de couverture est comblé séparément par
 *     Snapshot_Comparaison_Referentiels.gs (comparaison périodique),
 *     qui réutilise _traiterRenommage() défini ici.
 * ================================================================
 */

// ================================================================
// CONFIGURATION
// ================================================================

// Colonnes surveillées, par onglet
const SHEET_COLONNES_SURVEILLEES = {
  'Geo_Config':         ['Nom_Geo_1', 'Nom_Geo_2'],
  'Localités':          ['Localite'],
  'Categories_Taches':  ['Categorie'],
  'Type_Travaux':       ['Type_Travaux'],
  'Catalogue_Materiel': ['Designation']
};

// Colonne ID stable de chaque table surveillée — sert de clé de
// comparaison à Snapshot_Comparaison_Referentiels.gs pour détecter
// les changements qui n'ont pas déclenché onEdit (ex. écriture via
// l'API AppSheet). Non utilisée par ce fichier lui-même, mais
// centralisée ici avec SHEET_COLONNES_SURVEILLEES pour n'avoir
// qu'un seul endroit à maintenir si un onglet/une colonne change.
const SHEET_CLE_ID = {
  'Geo_Config':         'ID_Geo',
  'Localités':          'ID_Localite',
  'Categories_Taches':  'ID_Categorie',
  'Type_Travaux':       'ID_Type_Travaux',
  'Catalogue_Materiel': 'ID_Materiel'
};

// Copies dénormalisées à mettre à jour pour chaque colonne surveillée
// (la table source elle-même n'est pas listée : elle vient déjà
// d'être modifiée par l'utilisateur — c'est ce qui déclenche le script)
const PROPAGATION_MAP = {

  'Geo_Config.Nom_Geo_1': [
    { sheet: 'Localités',            colonne: 'Nom_Geo_1' },
    { sheet: 'Objectifs',            colonne: 'Nom_Geo_1' },
    { sheet: 'Journal_Chantier',     colonne: 'Nom_Geo_1' },
    { sheet: 'Interventions',        colonne: 'Filtre_Geo_1' },
    { sheet: 'Details_Intervention', colonne: 'Filtre_Geo_1' },
    { sheet: 'Utilisateurs',         colonne: 'Zone_Affectation', sensible: true },
    { sheet: 'Filtre_Performance',   colonne: 'Choix_Geo_1' },
    { sheet: 'Historique_Avnt_Geo',  colonne: 'Localite' }
  ],

  'Geo_Config.Nom_Geo_2': [
    { sheet: 'Localités',           colonne: 'Nom_Geo_2' },
    { sheet: 'Objectifs',           colonne: 'Nom_Geo_2' },
    { sheet: 'Journal_Chantier',    colonne: 'Nom_Geo_2' },
    { sheet: 'Interventions',       colonne: 'Filtre_Geo_2' },
    { sheet: 'Filtre_Performance',  colonne: 'Choix_Geo_2' }
  ],

  'Localités.Localite': [
    { sheet: 'Details_Intervention', colonne: 'Localite' },
    { sheet: 'Filtre_Performance',   colonne: 'Choix_Localite' }
  ],

  'Categories_Taches.Categorie': [
    { sheet: 'Parametres_Poids',   colonne: 'Categorie' },
    { sheet: 'Catalogue_Materiel', colonne: 'Categorie' },
    { sheet: 'Interventions',      colonne: 'Categorie' }
  ],

  'Type_Travaux.Type_Travaux': [
    { sheet: 'Catalogue_Materiel', colonne: 'Type_Travaux' },
    { sheet: 'Interventions',      colonne: 'Type_Travaux' }
  ],

  'Catalogue_Materiel.Designation': [
    { sheet: 'Objectifs',            colonne: 'Designation' },
    { sheet: 'Details_Intervention', colonne: 'Designation' }
  ]
};

// Avertissement à toujours inclure dans l'email pour certaines colonnes
// (action manuelle requise hors de portée d'Apps Script)
const AVERTISSEMENTS_CRITIQUES = {
  'Categories_Taches.Categorie':
    'Les colonnes virtuelles AppSheet (Objectifs/Localités : A_Travaux_HTA, ' +
    'A_Travaux_BT, Avancement_HTA_%, Avancement_BT_%, Avancement, Statut) ' +
    'comparent la valeur EXACTE de Categorie en dur dans leurs formules App ' +
    'Formula (AppSheet Editor). Ce script vient de mettre à jour les copies ' +
    'texte dans Google Sheets, mais NE PEUT PAS modifier ces formules. ' +
    'Merci d\'ouvrir AppSheet Editor et de corriger manuellement toute ' +
    'formule qui compare encore à l\'ancienne valeur, sous peine de voir ' +
    'l\'avancement HTA/BT retomber silencieusement à 0%.'
};

// Rôles destinataires des emails de confirmation
const ROLES_DESTINATAIRES = ['Admin', 'Chef de Mission'];

// ================================================================
// INSTALLATION DU DÉCLENCHEUR — à exécuter UNE SEULE FOIS
// ================================================================

function configurerDeclencheurOnEdit() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'onModificationReference') {
      ScriptApp.deleteTrigger(t);
      Logger.log('🗑 Supprimé : ancien trigger onModificationReference');
    }
  });

  ScriptApp.newTrigger('onModificationReference')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onEdit()
    .create();

  Logger.log('✅ Déclencheur installable "onModificationReference" créé.');
  Logger.log('   Surveille : ' + Object.keys(SHEET_COLONNES_SURVEILLEES).join(', '));
}

// ================================================================
// GESTIONNAIRE PRINCIPAL — appelé automatiquement à chaque édition
// ================================================================

function onModificationReference(e) {
  try {
    if (!e || !e.range) return;

    const sheet = e.range.getSheet();
    const sheetName = sheet.getName();
    const colonnesSurveillees = SHEET_COLONNES_SURVEILLEES[sheetName];
    if (!colonnesSurveillees) return; // onglet non concerné → sortie rapide

    // Édition multi-cellules (collage, import, remplissage) : la valeur
    // précédente de chaque cellule n'est pas exploitable de façon fiable.
    if (e.range.getNumRows() > 1 || e.range.getNumColumns() > 1) {
      _gererEditionNonFiable(sheet, colonnesSurveillees, e.range.getA1Notation(),
        'Édition portant sur plusieurs cellules à la fois (collage/import) — ' +
        'impossible de déterminer la valeur précédente de chaque cellule.');
      return;
    }

    const colIdx = e.range.getColumn();
    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const nomColonne = headers[colIdx - 1];

    if (colonnesSurveillees.indexOf(nomColonne) === -1) return; // colonne non suivie

    const ancienneValeur = e.oldValue;
    const nouvelleValeur = e.value;

    // Cellule vide → remplie : nouvelle entrée, pas un renommage, rien à propager
    if (ancienneValeur === undefined || ancienneValeur === null || String(ancienneValeur).trim() === '') {
      Logger.log('ℹ️ Nouvelle valeur (pas un renommage) : ' + sheetName + '.' + nomColonne + ' = "' + nouvelleValeur + '"');
      return;
    }

    // Valeur vidée (suppression, pas un renommage) : ne pas propager un blanc
    if (nouvelleValeur === undefined || nouvelleValeur === null || String(nouvelleValeur).trim() === '') {
      _gererEditionNonFiable(sheet, [nomColonne], e.range.getA1Notation(),
        'La valeur "' + ancienneValeur + '" a été effacée (pas remplacée par une nouvelle valeur) — ' +
        'aucune propagation automatique n\'a été faite pour éviter de vider les copies liées par erreur.');
      return;
    }

    if (String(ancienneValeur).trim() === String(nouvelleValeur).trim()) return; // pas de changement réel

    _traiterRenommage(sheetName, nomColonne, ancienneValeur, nouvelleValeur);

  } catch (err) {
    Logger.log('❌ onModificationReference — ' + err.message);
  }
}

// ================================================================
// PROPAGATION
// ================================================================
// Point d'entrée commun, appelé aussi bien par onModificationReference
// (édition directe dans Google Sheets) que par
// comparerEtPropagerReferentiels (Snapshot_Comparaison_Referentiels.gs,
// pour les écritures faites hors Sheets, ex. via AppSheet). Les deux
// chemins convergent ici pour garantir un comportement identique.
// ================================================================

function _traiterRenommage(sheetName, nomColonne, ancienneValeur, nouvelleValeur) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    Logger.log('⏭ Propagation ignorée (verrou occupé) : ' + sheetName + '.' + nomColonne);
    return;
  }

  try {
    const cle = sheetName + '.' + nomColonne;
    const cibles = PROPAGATION_MAP[cle] || [];
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const details = [];

    cibles.forEach(cible => {
      const sh = ss.getSheetByName(cible.sheet);
      if (!sh) {
        details.push({ sheet: cible.sheet, colonne: cible.colonne, erreur: 'Onglet introuvable' });
        return;
      }
      const res = _remplacerValeurDansColonne(sh, cible.colonne, ancienneValeur, nouvelleValeur);
      details.push(Object.assign({ sheet: cible.sheet, colonne: cible.colonne, sensible: !!cible.sensible }, res));
    });

    // Helper_Calcul (Localite/Nom_Geo_1/Categorie) se régénère tout seul
    // depuis Localités/Parametres_Poids : on force un recalcul immédiat
    // plutôt que d'attendre le prochain passage du trigger (30 min).
    if (typeof forcerRecalculHelperCalcul === 'function') {
      forcerRecalculHelperCalcul();
    }

    Logger.log('✅ Propagation ' + cle + ' : "' + ancienneValeur + '" → "' + nouvelleValeur + '"');
    details.forEach(d => Logger.log('   • ' + d.sheet + '.' + d.colonne + ' — ' + (d.remplaces || 0) + ' remplacée(s)'));

    // N'envoie l'email que si quelque chose a réellement été propagé (ou
    // qu'une erreur est survenue) — évite un email en double, à contenu
    // vide ("0 remplacée(s)" partout), quand la même modification a déjà
    // été traitée par l'autre point d'entrée (onEdit vs comparaison
    // périodique de Snapshot_Comparaison_Referentiels.gs).
    const totalRemplaces = details.reduce((somme, d) => somme + (d.remplaces || 0), 0);
    const contientErreur = details.some(d => d.erreur);
    if (totalRemplaces === 0 && !contientErreur) {
      Logger.log('ℹ️ Rien à propager (déjà synchronisé) : ' + cle);
      return;
    }

    _envoyerMailConfirmation(cle, ancienneValeur, nouvelleValeur, details, AVERTISSEMENTS_CRITIQUES[cle] || null);

  } finally {
    lock.releaseLock();
  }
}

// Remplace ancienneValeur → nouvelleValeur dans une colonne, en ignorant
// les cellules qui contiennent une formule (elles se corrigent seules).
function _remplacerValeurDansColonne(sheet, nomColonne, ancienneValeur, nouvelleValeur) {
  const colIdx = _trouverIndexColonne(sheet, nomColonne);
  if (colIdx === -1) return { trouve: false, remplaces: 0, ignoresFormule: 0 };

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return { trouve: true, remplaces: 0, ignoresFormule: 0 };

  const range    = sheet.getRange(2, colIdx, lastRow - 1, 1);
  const formules = range.getFormulas();
  const valeurs  = range.getValues();

  let remplaces = 0, ignoresFormule = 0;
  const nouvelles = valeurs.map((row, i) => {
    const val        = row[0];
    const estFormule = formules[i][0] !== '';
    const correspond = String(val).trim() === String(ancienneValeur).trim();

    if (estFormule) {
      if (correspond) ignoresFormule++;
      return [val];
    }
    if (correspond) { remplaces++; return [nouvelleValeur]; }
    return [val];
  });

  if (remplaces > 0) range.setValues(nouvelles);
  return { trouve: true, remplaces, ignoresFormule };
}

function _trouverIndexColonne(sheet, nomColonne) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const i = headers.indexOf(nomColonne);
  return i === -1 ? -1 : i + 1;
}

// ================================================================
// ÉDITIONS NON FIABLES (multi-cellules ou valeur effacée)
// ================================================================

function _gererEditionNonFiable(sheet, colonnesConcernees, plage, raison) {
  Logger.log('⚠️ ' + sheet.getName() + ' [' + plage + '] — ' + raison);
  _envoyerMailAlerteVerification(sheet.getName(), colonnesConcernees, plage, raison);
}

// ================================================================
// EMAILS
// ================================================================

function _listerDestinataires() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('Utilisateurs');
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return [];

  const data = sh.getRange(2, 1, lastRow - 1, 4).getValues(); // Email, Nom_Complet, Role, ...
  const emails = new Set();
  data.forEach(row => {
    const email = String(row[0]).trim();
    const role  = String(row[2]).trim();
    if (email && ROLES_DESTINATAIRES.indexOf(role) !== -1) emails.add(email);
  });
  return [...emails];
}

function _envoyerMailConfirmation(cle, ancienneValeur, nouvelleValeur, details, avertissement) {
  const destinataires = _listerDestinataires();
  if (destinataires.length === 0) {
    Logger.log('❌ Aucun destinataire (Admin/Chef de Mission) trouvé — email non envoyé');
    return;
  }

  const [sheetName, colonne] = cle.split('.');
  let sujet = '✅ Mise à jour référentiel propagée — ' + sheetName + '.' + colonne;

  let corps = 'Bonjour,\n\n';
  corps += 'Une valeur de référence a été modifiée dans le classeur et propagée automatiquement :\n\n';
  corps += '  Onglet          : ' + sheetName + '\n';
  corps += '  Colonne         : ' + colonne + '\n';
  corps += '  Ancienne valeur : ' + ancienneValeur + '\n';
  corps += '  Nouvelle valeur : ' + nouvelleValeur + '\n\n';
  corps += 'Mise à jour appliquée dans :\n';
  details.forEach(d => {
    if (d.erreur) { corps += '  ❌ ' + d.sheet + '.' + d.colonne + ' — ' + d.erreur + '\n'; return; }
    corps += '  • ' + d.sheet + '.' + d.colonne + ' — ' + (d.remplaces || 0) + ' cellule(s) mise(s) à jour'
      + (d.ignoresFormule ? ', ' + d.ignoresFormule + ' cellule(s) en formule (mise à jour automatique)' : '')
      + (d.sensible ? '  [colonne sensible — accès/sécurité]' : '') + '\n';
  });

  if (avertissement) {
    sujet = '⚠️ ACTION REQUISE — ' + sujet;
    corps += '\n⚠️ ACTION MANUELLE REQUISE (AppSheet Editor) :\n' + avertissement + '\n';
  }

  corps += '\n— ElecTrack Pro / Mise à jour automatique des référentiels';

  GmailApp.sendEmail(destinataires.join(','), sujet, corps);
  Logger.log('📧 Email envoyé à : ' + destinataires.join(', '));
}

function _envoyerMailAlerteVerification(sheetName, colonnes, plage, raison) {
  const destinataires = _listerDestinataires();
  if (destinataires.length === 0) return;

  const sujet = '⚠️ Vérification manuelle requise — ' + sheetName;
  const corps = 'Bonjour,\n\n' +
    'Une modification nécessitant une vérification manuelle a été détectée :\n\n' +
    '  Onglet                        : ' + sheetName + '\n' +
    '  Colonne(s) surveillée(s)      : ' + colonnes.join(', ') + '\n' +
    '  Plage éditée                  : ' + plage + '\n' +
    '  Raison                        : ' + raison + '\n\n' +
    'La propagation automatique n\'a PAS été effectuée pour cette édition.\n' +
    'Si un renommage a bien eu lieu, veuillez utiliser le script de propagation ' +
    'manuelle (previsualiserRenommage / appliquerRenommage) pour le traiter en toute sécurité.\n\n' +
    '— ElecTrack Pro / Mise à jour automatique des référentiels';

  GmailApp.sendEmail(destinataires.join(','), sujet, corps);
  Logger.log('📧 Email d\'alerte (vérification requise) envoyé à : ' + destinataires.join(', '));
}
