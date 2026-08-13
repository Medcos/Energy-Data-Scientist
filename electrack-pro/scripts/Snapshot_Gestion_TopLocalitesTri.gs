// ================================================================
// Gestion_TopLocalitesTri.gs
//
// L'onglet "Top_Localites_Tri" est configuré en LECTURE SEULE côté
// AppSheet (le formulaire/l'app ne peut pas écrire dans les colonnes
// A et B). Ces deux colonnes doivent donc être maintenues côté
// Google Apps Script :
//
//   Colonne A — ID_Top_Localite :
//     Si la ligne a une valeur dans la colonne d'ancrage (par défaut
//     ID_Localite, col. C) ET que ID_Top_Localite est vide,
//     on génère un identifiant unique.
//
//   Colonne B — Rang :
//     Si la ligne a une valeur dans la colonne d'ancrage ET que Tri
//     est vide, on incrémente de 1 la dernière valeur de Tri déjà
//     attribuée dans la feuille (compteur strictement croissant,
//     jamais réattribué).
//
//   Cohérence inverse (nettoyage) :
//     Si la colonne d'ancrage est VIDE, ID_Top_Localite et Tri DOIVENT
//     rester vides eux aussi. Si l'un des deux contient déjà une valeur
//     (ex. ligne créée par une synchro externe avant que ID_Localite ne
//     soit renseigné, ou ID_Localite effacé après coup), le script
//     l'efface. Cas observé en production : ligne avec ID_Top_Localite
//     et Tri déjà attribués alors que ID_Localite était encore vide.
//
// Choix de génération d'ID : Utilities.getUuid().substring(0,8) —
// et non une saisie/concat manuelle — conformément au correctif
// préconisé dans l'audit BD suite aux IDs corrompus détectés dans
// Geo_Config ("2pc17c4d1", "a9of7a981") et Top_Localites_Tri elle-même
// ("46cfa5g8" : caractère 'g' non hexadécimal). On vérifie en plus
// l'unicité contre les ID déjà présents en colonne A avant d'écrire.
//
// Lecture des colonnes par NOM d'en-tête (pas par lettre) : le script
// reste valide même si l'ordre des colonnes change — cohérent avec
// les autres scripts du projet (Snapshot_HelperCalcul, Snapshot_Geo).
//
// ⚠️ Avant déploiement en production : tester d'abord sur une copie
// du classeur nommée "... TEST" ou "... COPIE", conformément au
// workflow habituel du projet.
// ================================================================

const CONFIG_TOP_LOC_TRI = {
  SHEET_NOM        : "Top_Localites_Tri",
  COL_ID           : "ID_Top_Localite",   // colonne A à générer
  COL_TRI          : "Rang",               // colonne B à incrémenter
  COL_ANCRAGE      : "ID_Localite",        // colonne qui déclenche le remplissage
  LONGUEUR_ID      : 8,                    // cohérent avec les autres ID du projet (8 car. hexa)
};

// ================================================================
// DÉCLENCHEUR — Exécuter configurerDeclencheur_TopLocalitesTri()
// UNE SEULE FOIS. Cadence 30 min, alignée sur Snapshot_HelperCalcul
// qui alimente indirectement cette feuille (Top_Localites → tri).
// ================================================================
function configurerDeclencheur_TopLocalitesTri() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "gererIDsEtTri_TopLocalitesTri") {
      ScriptApp.deleteTrigger(t);
      Logger.log("🗑 Supprimé : ancien trigger gererIDsEtTri_TopLocalitesTri");
    }
  });

  ScriptApp.newTrigger("gererIDsEtTri_TopLocalitesTri")
    .timeBased()
    .everyMinutes(30)
    .create();

  Logger.log("✅ gererIDsEtTri_TopLocalitesTri → toutes les 30 min");
}

// ================================================================
// UTILITAIRE — retry sur lecture Sheets (erreurs serveur ponctuelles)
// ================================================================
function avecRetry_TopLocTri(fn, tentatives = 3, delaiMs = 2000) {
  for (let i = 0; i < tentatives; i++) {
    try {
      return fn();
    } catch (e) {
      if (i === tentatives - 1) throw e;
      Logger.log("⚠️ Tentative " + (i + 1) + " échouée (" + e.message + "), nouvel essai dans " + delaiMs + "ms");
      Utilities.sleep(delaiMs);
    }
  }
}

// Génère un ID unique de LONGUEUR_ID caractères, hexadécimal garanti
// (contrairement aux ID historiques saisis à la main), en évitant
// toute collision avec les ID déjà présents dans idsExistants.
function _genererIdUnique_TopLocTri(idsExistants) {
  let id;
  do {
    id = Utilities.getUuid().replace(/-/g, "").substring(0, CONFIG_TOP_LOC_TRI.LONGUEUR_ID);
  } while (idsExistants.has(id));
  idsExistants.add(id);
  return id;
}

// ================================================================
// FONCTION PRINCIPALE
// ================================================================
function gererIDsEtTri_TopLocalitesTri() {
  Logger.log("🚀 gererIDsEtTri_TopLocalitesTri démarré");

  try {
    const ss  = SpreadsheetApp.getActiveSpreadsheet();
    const sh  = ss.getSheetByName(CONFIG_TOP_LOC_TRI.SHEET_NOM);
    if (!sh) throw new Error("Onglet introuvable : " + CONFIG_TOP_LOC_TRI.SHEET_NOM);

    const lastRow = sh.getLastRow();
    const lastCol = sh.getLastColumn();
    if (lastRow < 2) {
      Logger.log("ℹ️ Aucune ligne de données — rien à faire");
      return;
    }

    const headers = avecRetry_TopLocTri(() =>
      sh.getRange(1, 1, 1, lastCol).getValues()[0]
    );

    const iID      = headers.indexOf(CONFIG_TOP_LOC_TRI.COL_ID);
    const iTri     = headers.indexOf(CONFIG_TOP_LOC_TRI.COL_TRI);
    const iAncrage = headers.indexOf(CONFIG_TOP_LOC_TRI.COL_ANCRAGE);

    if (iID === -1 || iTri === -1 || iAncrage === -1) {
      throw new Error(
        "Colonne(s) introuvable(s) — vérifier les en-têtes exacts : " +
        CONFIG_TOP_LOC_TRI.COL_ID + " / " +
        CONFIG_TOP_LOC_TRI.COL_TRI + " / " +
        CONFIG_TOP_LOC_TRI.COL_ANCRAGE
      );
    }

    const data = avecRetry_TopLocTri(() =>
      sh.getRange(2, 1, lastRow - 1, lastCol).getValues()
    );

    // Set des ID déjà présents (unicité) + max Tri déjà attribué (compteur)
    const idsExistants = new Set(
      data.map(r => String(r[iID]).trim()).filter(v => v !== "")
    );
    let maxTri = data.reduce((max, r) => {
      const v = Number(r[iTri]);
      return (!isNaN(v) && v > max) ? v : max;
    }, 0);

    let nbIdsGeneres  = 0;
    let nbTrisGeneres = 0;
    let nbIdsEffaces   = 0;
    let nbTrisEffaces  = 0;

    data.forEach(row => {
      const ancrageNonVide = String(row[iAncrage]).trim() !== "";

      if (!ancrageNonVide) {
        // Cohérence défensive : ID_Localite vide → ID_Top_Localite et Tri
        // doivent l'être aussi. On efface toute valeur résiduelle plutôt
        // que de la laisser en incohérence silencieuse (cf. cas observé :
        // ligne avec A/B déjà remplis alors que l'ancrage était encore vide).
        if (String(row[iID]).trim() !== "") {
          idsExistants.delete(String(row[iID]).trim()); // libère l'ID pour réutilisation future
          row[iID] = "";
          nbIdsEffaces++;
        }
        if (String(row[iTri]).trim() !== "") {
          row[iTri] = "";
          nbTrisEffaces++;
        }
        return;
      }

      if (String(row[iID]).trim() === "") {
        row[iID] = _genererIdUnique_TopLocTri(idsExistants);
        nbIdsGeneres++;
      }

      if (String(row[iTri]).trim() === "") {
        maxTri += 1;
        row[iTri] = maxTri;
        nbTrisGeneres++;
      }
    });

    if (nbIdsGeneres === 0 && nbTrisGeneres === 0 && nbIdsEffaces === 0 && nbTrisEffaces === 0) {
      Logger.log("✅ Rien à faire — toutes les lignes sont cohérentes (ancrage ⇔ ID/Tri)");
      return;
    }

    // Écriture en une seule passe (colonnes A et B uniquement)
    const colID  = data.map(r => [r[iID]]);
    const colTri = data.map(r => [r[iTri]]);
    sh.getRange(2, iID + 1, colID.length, 1).setValues(colID);
    sh.getRange(2, iTri + 1, colTri.length, 1).setValues(colTri);

    Logger.log("✅ " + nbIdsGeneres + " ID_Top_Localite généré(s), " +
               nbTrisGeneres + " valeur(s) de Tri attribuée(s)" +
               (nbIdsEffaces > 0 || nbTrisEffaces > 0
                 ? " | 🧹 " + nbIdsEffaces + " ID + " + nbTrisEffaces + " Tri effacé(s) (ancrage vide)"
                 : ""));

  } catch (e) {
    Logger.log("❌ gererIDsEtTri_TopLocalitesTri — " + e.message);
    throw e;
  }
}

// ================================================================
// DEBUG — lecture seule, aucune écriture (pour valider avant prod)
// ================================================================
function debugTopLocalitesTri() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(CONFIG_TOP_LOC_TRI.SHEET_NOM);
  const lastRow = sh.getLastRow();
  const lastCol = sh.getLastColumn();
  const headers = sh.getRange(1, 1, 1, lastCol).getValues()[0];

  const iID      = headers.indexOf(CONFIG_TOP_LOC_TRI.COL_ID);
  const iTri     = headers.indexOf(CONFIG_TOP_LOC_TRI.COL_TRI);
  const iAncrage = headers.indexOf(CONFIG_TOP_LOC_TRI.COL_ANCRAGE);

  const data = sh.getRange(2, 1, lastRow - 1, lastCol).getValues();
  let manquants = 0;
  let orphelins = 0;

  data.forEach((row, i) => {
    const ancrageNonVide = String(row[iAncrage]).trim() !== "";
    const idVide  = String(row[iID]).trim() === "";
    const triVide = String(row[iTri]).trim() === "";

    if (ancrageNonVide && (idVide || triVide)) {
      manquants++;
      Logger.log("  ⏳ Ligne " + (i + 2) + " — ID vide: " + idVide + " | Tri vide: " + triVide +
                 " | Ancrage: " + row[iAncrage]);
    }

    if (!ancrageNonVide && (!idVide || !triVide)) {
      orphelins++;
      Logger.log("  🧹 Ligne " + (i + 2) + " — ANCRAGE VIDE mais ID=" + row[iID] +
                 " | Tri=" + row[iTri] + " → sera effacé au prochain passage réel");
    }
  });

  Logger.log("🔍 " + manquants + " ligne(s) à compléter, " + orphelins +
             " ligne(s) orpheline(s) à nettoyer (aucune écriture effectuée)");
}