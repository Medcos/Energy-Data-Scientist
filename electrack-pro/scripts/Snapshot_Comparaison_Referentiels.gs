/**
 * Snapshot_Comparaison_Referentiels.gs
 * ================================================================
 * Complète OnEdit_Propagation_Referentiels.gs : un trigger onEdit
 * (simple ET installable) ne se déclenche JAMAIS pour une écriture
 * faite par programmation (API Sheets), ce qui inclut toute
 * modification faite depuis l'interface AppSheet. Ce script comble
 * ce trou par comparaison périodique : il relit les tables de
 * référence, compare chaque valeur à un instantané de la dernière
 * lecture connue (stocké dans un onglet caché dédié), et réutilise
 * _traiterRenommage() pour tout écart détecté — même comportement,
 * mêmes emails, quelle que soit la source de la modification
 * (Google Sheets ou AppSheet).
 *
 * DÉPEND DE (même projet Apps Script, fichier
 * OnEdit_Propagation_Referentiels.gs) :
 *   - SHEET_COLONNES_SURVEILLEES
 *   - SHEET_CLE_ID
 *   - _traiterRenommage()
 *   - _envoyerMailAlerteVerification()
 *
 * INSTALLATION (à faire UNE SEULE FOIS) :
 *   Exécuter configurerDeclencheurComparaisonReferentiels() depuis
 *   l'éditeur Apps Script.
 *
 * COMPORTEMENT AU PREMIER PASSAGE :
 *   Aucun instantané précédent n'existe encore → le script capture
 *   simplement l'état actuel comme référence, SANS rien propager
 *   (sinon tout le contenu existant serait traité comme un
 *   renommage). Les comparaisons réelles démarrent à partir du
 *   deuxième passage.
 *
 * LIMITE ASSUMÉE :
 *   Ne rattrape pas rétroactivement un changement survenu AVANT la
 *   mise en place de ce script (ex. l'incident "Déroulauge" →
 *   "Déroulage" propagé depuis AppSheet avant l'installation) — ces
 *   cas doivent être corrigés manuellement une fois, après quoi le
 *   suivi automatique prend le relais.
 * ================================================================
 */

const SNAPSHOT_REFERENTIELS_SHEET = 'Referentiels_Snapshot'; // onglet caché, créé automatiquement

// ================================================================
// DÉCLENCHEUR — à exécuter UNE SEULE FOIS
// ================================================================
function configurerDeclencheurComparaisonReferentiels() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'comparerEtPropagerReferentiels') {
      ScriptApp.deleteTrigger(t);
      Logger.log('🗑 Supprimé : ancien trigger comparerEtPropagerReferentiels');
    }
  });

  ScriptApp.newTrigger('comparerEtPropagerReferentiels')
    .timeBased()
    .everyMinutes(15)
    .create();

  Logger.log('✅ comparerEtPropagerReferentiels → toutes les 15 min');
}

// ================================================================
// FONCTION PRINCIPALE
// ================================================================
function comparerEtPropagerReferentiels() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    Logger.log('⏭ Comparaison référentiels ignorée (verrou occupé)');
    return;
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const shSnapshot = _obtenirOuCreerOngletSnapshot(ss);
    const snapshotPrecedent = _chargerSnapshot(shSnapshot);
    const snapshotActuel = new Map();
    const premierRun = snapshotPrecedent.size === 0;

    Object.keys(SHEET_COLONNES_SURVEILLEES).forEach(sheetName => {
      const sh = ss.getSheetByName(sheetName);
      if (!sh) { Logger.log('⚠️ Onglet introuvable : ' + sheetName); return; }

      const idCol = SHEET_CLE_ID[sheetName];
      if (!idCol) { Logger.log('⚠️ Pas de colonne ID configurée pour ' + sheetName); return; }

      const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
      const idIdx = headers.indexOf(idCol);
      if (idIdx === -1) { Logger.log('⚠️ Colonne ID "' + idCol + '" introuvable dans ' + sheetName); return; }

      const colonnesSurveillees = SHEET_COLONNES_SURVEILLEES[sheetName];
      const colIdxMap = {};
      colonnesSurveillees.forEach(c => colIdxMap[c] = headers.indexOf(c));

      const lastRow = sh.getLastRow();
      if (lastRow < 2) return;
      const data = sh.getRange(2, 1, lastRow - 1, sh.getLastColumn()).getValues();

      data.forEach(row => {
        const id = String(row[idIdx]).trim();
        if (!id) return; // ligne vide

        colonnesSurveillees.forEach(colonne => {
          const idx = colIdxMap[colonne];
          if (idx === -1) return;

          const valeurActuelle = String(row[idx]).trim();
          const cle = sheetName + '|' + id + '|' + colonne;
          snapshotActuel.set(cle, valeurActuelle);

          if (premierRun) return; // capture de référence seulement, pas de comparaison

          const valeurPrecedente = snapshotPrecedent.get(cle);

          if (valeurPrecedente === undefined) return; // ligne apparue depuis le dernier passage → nouvelle entrée, pas un renommage
          if (valeurPrecedente === valeurActuelle) return; // pas de changement
          if (valeurPrecedente === '') return; // était vide → ajout, pas un renommage

          if (valeurActuelle === '') {
            // Valeur effacée hors Google Sheets (ex. AppSheet) — même prudence
            // que le trigger onEdit : pas de propagation d'un blanc.
            _envoyerMailAlerteVerification(sheetName, [colonne], 'ID ' + id,
              'La valeur "' + valeurPrecedente + '" a été effacée (détecté hors Google Sheets, ' +
              'ex. via AppSheet) — aucune propagation automatique n\'a été faite.');
            return;
          }

          Logger.log('🔁 Changement détecté hors Sheets : ' + cle + ' : "' + valeurPrecedente + '" → "' + valeurActuelle + '"');
          _traiterRenommage(sheetName, colonne, valeurPrecedente, valeurActuelle);
        });
      });
    });

    _sauvegarderSnapshot(shSnapshot, snapshotActuel);

    if (premierRun) {
      Logger.log('📸 Référentiel initial capturé (' + snapshotActuel.size + ' valeur(s)) — aucune comparaison sur ce premier passage.');
    } else {
      Logger.log('✅ Comparaison terminée (' + snapshotActuel.size + ' valeur(s) suivies)');
    }

  } finally {
    lock.releaseLock();
  }
}

// ================================================================
// STOCKAGE DE L'INSTANTANÉ — onglet caché dédié
// ================================================================
function _obtenirOuCreerOngletSnapshot(ss) {
  let sh = ss.getSheetByName(SNAPSHOT_REFERENTIELS_SHEET);
  if (!sh) {
    sh = ss.insertSheet(SNAPSHOT_REFERENTIELS_SHEET);
    sh.getRange(1, 1, 1, 2).setValues([['Cle', 'Valeur']]);
    sh.hideSheet();
    Logger.log('📄 Onglet créé : ' + SNAPSHOT_REFERENTIELS_SHEET);
  }
  return sh;
}

function _chargerSnapshot(sh) {
  const map = new Map();
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return map;
  const data = sh.getRange(2, 1, lastRow - 1, 2).getValues();
  data.forEach(row => {
    if (row[0]) map.set(row[0], row[1]);
  });
  return map;
}

function _sauvegarderSnapshot(sh, map) {
  sh.getRange(2, 1, Math.max(sh.getLastRow() - 1, 1), 2).clearContent();
  if (map.size === 0) return;
  const rows = [...map.entries()];
  sh.getRange(2, 1, rows.length, 2).setValues(rows);
}

// ================================================================
// DEBUG — lecture seule, aucune écriture ni propagation
// (pour valider avant de laisser tourner le trigger automatique)
// ================================================================
function debugComparaisonReferentiels() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const shSnapshot = ss.getSheetByName(SNAPSHOT_REFERENTIELS_SHEET);
  const snapshotPrecedent = shSnapshot ? _chargerSnapshot(shSnapshot) : new Map();
  const premierRun = snapshotPrecedent.size === 0;

  if (premierRun) {
    Logger.log('ℹ️ Aucun instantané précédent — le prochain run réel capturera la référence sans propager.');
    return;
  }

  let ecarts = 0;

  Object.keys(SHEET_COLONNES_SURVEILLEES).forEach(sheetName => {
    const sh = ss.getSheetByName(sheetName);
    if (!sh) return;

    const idCol = SHEET_CLE_ID[sheetName];
    const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
    const idIdx = headers.indexOf(idCol);
    if (idIdx === -1) return;

    const colonnesSurveillees = SHEET_COLONNES_SURVEILLEES[sheetName];
    const colIdxMap = {};
    colonnesSurveillees.forEach(c => colIdxMap[c] = headers.indexOf(c));

    const lastRow = sh.getLastRow();
    if (lastRow < 2) return;
    const data = sh.getRange(2, 1, lastRow - 1, sh.getLastColumn()).getValues();

    data.forEach(row => {
      const id = String(row[idIdx]).trim();
      if (!id) return;

      colonnesSurveillees.forEach(colonne => {
        const idx = colIdxMap[colonne];
        if (idx === -1) return;
        const valeurActuelle = String(row[idx]).trim();
        const cle = sheetName + '|' + id + '|' + colonne;
        const valeurPrecedente = snapshotPrecedent.get(cle);

        if (valeurPrecedente !== undefined && valeurPrecedente !== valeurActuelle) {
          ecarts++;
          Logger.log('  🔁 ' + cle + ' : "' + valeurPrecedente + '" → "' + valeurActuelle + '"');
        }
      });
    });
  });

  Logger.log('🔍 ' + ecarts + ' écart(s) détecté(s) (aucune écriture ni email envoyé par ce debug)');
}
