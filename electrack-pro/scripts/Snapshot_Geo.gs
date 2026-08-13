// ================================================================
// Snapshot_Geo — Version SaaS
// Aucune valeur projet codée en dur.
// ID_Projet et départements sont lus dynamiquement depuis Sheets.
//
// Sources dynamiques :
//   ID_Projet   ← Projets_Config (premier projet Actif)
//   Départements ← Top_Localites col "Departement" (valeurs uniques)
//
// Structure Historique_Avnt_Geo (colonnes 1→8) :
//   1:ID_Historique 2:ID_Projet 3:Localite 4:Semaine
//   5:Num_Semaine   6:Avancement_HTA_% 7:Avancement_BT_% 8:Avancement
// ================================================================

const CONFIG_GEO = {
  SHEET_PROJETS   : "Projets_Config",
  SHEET_SOURCE    : "Top_Localites",
  SHEET_HISTORIQUE: "Historique_Avnt_Geo",
  LABEL_GLOBAL    : "Toutes",
  TIMEOUT_MS      : 25000,
};

// ================================================================
// DÉCLENCHEURS — Exécuter configurerDeclencheurs_Geo() UNE SEULE FOIS
// ================================================================
function configurerDeclencheurs_Geo() {

  const fonctions = ["snapshotHebdomadaire_Geo", "miseAJourSemaineCourante_Geo"];

  ScriptApp.getProjectTriggers().forEach(t => {
    if (fonctions.includes(t.getHandlerFunction())) {
      ScriptApp.deleteTrigger(t);
      Logger.log("🗑 Supprimé : " + t.getHandlerFunction());
    }
  });

  // Mardi 02h — décalé d'1h après le script global
  ScriptApp.newTrigger("snapshotHebdomadaire_Geo")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.TUESDAY)
    .atHour(2)
    .create();
  Logger.log("✅ snapshotHebdomadaire_Geo    → chaque mardi 02h");

  // 23h30 — décalé de 30min après le script global
  ScriptApp.newTrigger("miseAJourSemaineCourante_Geo")
    .timeBased()
    .everyDays(1)
    .atHour(23)
    .nearMinute(30)
    .create();
  Logger.log("✅ miseAJourSemaineCourante_Geo → quotidien 23h30");

  Logger.log("─────────────────────────────");
  ScriptApp.getProjectTriggers().forEach(t => {
    Logger.log("  ▶ " + t.getHandlerFunction() + " | " + t.getEventType());
  });
  Logger.log("✅ Configuration terminée — ne plus exécuter cette fonction");
}

// ================================================================
// UTILITAIRES PRIVÉS
// ================================================================

function _getWeekNumber_Geo(date) {
  const d   = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const year = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d - year) / 86400000) + 1) / 7);
}

function _getLundiSemaine_Geo(date) {
  const dayOfWeek = date.getDay();
  const diff      = (dayOfWeek === 0) ? -6 : 1 - dayOfWeek;
  const lundi     = new Date(date);
  lundi.setDate(date.getDate() + diff);
  lundi.setHours(0, 0, 0, 0);
  return lundi;
}

function _round2_Geo(v) {
  return Math.round(v * 100) / 100;
}

// ================================================================
// LECTURE DYNAMIQUE — Projet & Départements
// ================================================================

function _lireIdProjetActif_Geo() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(CONFIG_GEO.SHEET_PROJETS);
  if (!SRC) throw new Error("Onglet '" + CONFIG_GEO.SHEET_PROJETS + "' introuvable");

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const iID    = headers.indexOf("ID_Projet");
  const iActif = headers.indexOf("Actif");
  if (iID < 0 || iActif < 0)
    throw new Error("Colonnes ID_Projet ou Actif introuvables dans " + CONFIG_GEO.SHEET_PROJETS);

  const data = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();
  for (let i = 0; i < data.length; i++) {
    const actif = String(data[i][iActif]).trim().toUpperCase();
    if (actif === "TRUE" || actif === "VRAI" || actif === "1") {
      const id = String(data[i][iID]).trim();
      Logger.log("  🏗 Projet actif : " + id);
      return id;
    }
  }
  throw new Error("Aucun projet Actif trouvé dans " + CONFIG_GEO.SHEET_PROJETS);
}

// Lit les départements uniques depuis Top_Localites
// Retourne [{label, colDept}, ...] + {label:"Toutes", colDept:null} en dernier
function _lireDepartements_Geo(src) {
  const { data, iDept } = src;
  const vus  = {};
  const deps = [];

  data.forEach(row => {
    const d = String(row[iDept]).trim();
    if (d && !vus[d]) {
      vus[d] = true;
      // Normalisation casse : ex. "NORD" (saisi en majuscules) → "Nord"
      const label = d.charAt(0).toUpperCase() + d.slice(1).toLowerCase();
      deps.push({ label: label, colDept: d });
    }
  });

  deps.push({ label: CONFIG_GEO.LABEL_GLOBAL, colDept: null });
  Logger.log("  📍 Entités : " + deps.map(d => d.label).join(", "));
  return deps;
}

// ================================================================
// CALCUL
// ================================================================

function _chargerTopLocalites_Geo() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(CONFIG_GEO.SHEET_SOURCE);
  if (!SRC) throw new Error("Onglet '" + CONFIG_GEO.SHEET_SOURCE + "' introuvable");

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const lastRow = SRC.getLastRow();
  const data    = lastRow > 1
    ? SRC.getRange(2, 1, lastRow - 1, headers.length).getValues()
    : [];

  const idx = name => {
    const i = headers.indexOf(name);
    if (i === -1) throw new Error("Colonne introuvable dans " + CONFIG_GEO.SHEET_SOURCE + " : " + name);
    return i;
  };

  return {
    data,
    iDept : idx("Departement"),
    iHTA  : idx("Avancement_HTA_%"),
    iBT   : idx("Avancement_BT_%"),
    iAva  : idx("Avancement"),
    iID   : idx("ID_Localite"),
  };
}

function _calculerMoyennes_Geo(src, colDept) {
 const { data, iDept, iHTA, iBT, iAva, iID } = src;

  const lignes = data.filter(row => {
    if (row[iID] === "" || row[iID] === null) return false;
    if (colDept === null) return true;
    return String(row[iDept]).trim() === colDept;
  });

  if (lignes.length === 0) {
    Logger.log("  ⚠️ Aucune localité trouvée" + (colDept ? " pour " + colDept : ""));
    return null;
  }

  const n   = lignes.length;
  const sum = arr => arr.reduce((a, b) => a + b, 0);

  // round2 appliqué sur chaque valeur lue pour éliminer les résidus flottants
const moyHTA = round2(sum(lignes.map(r => round2(Number(r[iHTA]) || 0))) / n * 100);
const moyBT  = round2(sum(lignes.map(r => round2(Number(r[iBT])  || 0))) / n * 100);
const moyAva = round2(sum(lignes.map(r => round2(Number(r[iAva]) || 0))) / n * 100);

  Logger.log("  📊 " + (colDept || "Toutes") + " (" + n + " loc.)"
             + " | HTA: " + moyHTA + " | BT: " + moyBT + " | Global: " + moyAva);

  return { moyHTA, moyBT, moyAva };
}

function _trouverLigne_Geo(sheet, labelSem, labelLocalite) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return -1;

  const vals = sheet.getRange(2, 3, lastRow - 1, 3).getValues();
  for (let i = 0; i < vals.length; i++) {
    if (String(vals[i][0]).trim() === labelLocalite &&
        String(vals[i][2]).trim() === labelSem) {
      return i + 2;
    }
  }
  return -1;
}

// ================================================================
// ÉCRITURE
// ================================================================

function _ecrireLigne_Geo(sheet, idProjet, dept, labelSem, dateFmt, moyHTA, moyBT, moyAva, modeCreation) {
  const { label } = dept;
  const ligneExist = _trouverLigne_Geo(sheet, labelSem, label);

  if (ligneExist > 0) {
    sheet.getRange(ligneExist, 6, 1, 3).setValues([[moyHTA, moyBT, moyAva]]);
    Logger.log("  ✅ MIS À JOUR : " + label + " — " + labelSem);
  } else if (modeCreation) {
    const uid    = Utilities.getUuid().substring(0, 8);
    const newRow = [uid, idProjet, label, dateFmt, labelSem, moyHTA, moyBT, moyAva];
    sheet.getRange(sheet.getLastRow() + 1, 1, 1, 8).setValues([newRow]);
    Logger.log("  ✅ CRÉÉ : " + label + " — " + labelSem);
  } else {
    Logger.log("  ⏳ " + label + " : " + labelSem + " absente → attente snapshot mardi");
  }
}

// ================================================================
// FONCTIONS PRINCIPALES
// ================================================================

function snapshotHebdomadaire_Geo() {
  const start = Date.now();
  Logger.log("🚀 snapshotHebdomadaire_Geo démarré");

  try {
    const SS   = SpreadsheetApp.getActiveSpreadsheet();
    const DEST = SS.getSheetByName(CONFIG_GEO.SHEET_HISTORIQUE);
    if (!DEST) throw new Error("Onglet '" + CONFIG_GEO.SHEET_HISTORIQUE + "' introuvable");

    const lundi    = _getLundiSemaine_Geo(new Date());
    const numSem   = _getWeekNumber_Geo(lundi);
    const labelSem = "S" + numSem + "-" + lundi.getFullYear();
    const dateFmt  = Utilities.formatDate(lundi, Session.getScriptTimeZone(), "dd/MM/yyyy");

    Logger.log("📅 Semaine : " + labelSem + " | Lundi : " + dateFmt);

    // ← Tout lu dynamiquement depuis Sheets
    const idProjet = _lireIdProjetActif_Geo();
    const src      = _chargerTopLocalites_Geo();
    const depts    = _lireDepartements_Geo(src);

    depts.forEach(dept => {
      if (Date.now() - start > CONFIG_GEO.TIMEOUT_MS) {
        Logger.log("⚠️ Timeout — arrêt"); return;
      }
      const moy = _calculerMoyennes_Geo(src, dept.colDept);
      if (!moy) return;
      _ecrireLigne_Geo(DEST, idProjet, dept, labelSem, dateFmt,
                       moy.moyHTA, moy.moyBT, moy.moyAva, true);
    });

    Logger.log("⏱ " + (Date.now() - start) + " ms | ✅ " + depts.length + " lignes écrites");

  } catch(e) {
    Logger.log("❌ snapshotHebdomadaire_Geo — " + e.message);
    throw e;
  }
}

function miseAJourSemaineCourante_Geo() {
  const start = Date.now();

  try {
    const SS   = SpreadsheetApp.getActiveSpreadsheet();
    const DEST = SS.getSheetByName(CONFIG_GEO.SHEET_HISTORIQUE);
    if (!DEST) return;

    const lundi    = _getLundiSemaine_Geo(new Date());
    const numSem   = _getWeekNumber_Geo(lundi);
    const labelSem = "S" + numSem + "-" + lundi.getFullYear();
    const dateFmt  = Utilities.formatDate(lundi, Session.getScriptTimeZone(), "dd/MM/yyyy");

    const src      = _chargerTopLocalites_Geo();
    const depts    = _lireDepartements_Geo(src);
    const idProjet = _lireIdProjetActif_Geo();

    // Vérifier que la semaine existe (premier dept non-global)
    const premierDept = depts.find(d => d.colDept !== null);
    if (premierDept && _trouverLigne_Geo(DEST, labelSem, premierDept.label) < 0) {
      Logger.log("⏳ " + labelSem + " absente → attente snapshot mardi"); return;
    }

    if (Date.now() - start > CONFIG_GEO.TIMEOUT_MS) {
      Logger.log("⚠️ Timeout préventif"); return;
    }

    depts.forEach(dept => {
      if (Date.now() - start > CONFIG_GEO.TIMEOUT_MS) {
        Logger.log("⚠️ Timeout — arrêt"); return;
      }
      const moy = _calculerMoyennes_Geo(src, dept.colDept);
      if (!moy) return;
      _ecrireLigne_Geo(DEST, idProjet, dept, labelSem, dateFmt,
                       moy.moyHTA, moy.moyBT, moy.moyAva, false);
    });

    Logger.log("✅ MàJ Geo " + labelSem + " | ⏱ " + (Date.now() - start) + " ms");

  } catch(e) {
    Logger.log("❌ miseAJourSemaineCourante_Geo — " + e.message);
  }
}

// ================================================================
// DEBUG & TESTS
// ================================================================

function debugCalcul_Geo() {
  Logger.log("🔍 DEBUG — lecture seule");
  const idProjet = _lireIdProjetActif_Geo();
  const src      = _chargerTopLocalites_Geo();
  const depts    = _lireDepartements_Geo(src);
  Logger.log("Projet : " + idProjet + " | " + depts.length + " entités");
  depts.forEach(dept => _calculerMoyennes_Geo(src, dept.colDept));
}

function debugHistorique_Geo() {
  const SS       = SpreadsheetApp.getActiveSpreadsheet();
  const DEST     = SS.getSheetByName(CONFIG_GEO.SHEET_HISTORIQUE);
  const lundi    = _getLundiSemaine_Geo(new Date());
  const labelSem = "S" + _getWeekNumber_Geo(lundi) + "-" + lundi.getFullYear();

  Logger.log("🔍 Semaine : [" + labelSem + "] | Tz : " + Session.getScriptTimeZone());
  const lastRow = DEST.getLastRow();
  const data    = DEST.getRange(2, 1, lastRow - 1, 8).getValues();
  data.forEach((row, i) => {
    Logger.log("L" + (i+2) + " | [" + row[2] + "] [" + row[4] + "]"
      + " HTA:" + row[5] + " BT:" + row[6] + " Ava:" + row[7]);
  });

  const src   = _chargerTopLocalites_Geo();
  const depts = _lireDepartements_Geo(src);
  depts.forEach(dept => {
    const l = _trouverLigne_Geo(DEST, labelSem, dept.label);
    Logger.log(l > 0 ? "✅ " + dept.label + " → L" + l : "❌ " + dept.label + " introuvable");
  });
}

function forcerSnapshot_Geo() {
  Logger.log("⚡ Snapshot Geo forcé");
  snapshotHebdomadaire_Geo();
}
