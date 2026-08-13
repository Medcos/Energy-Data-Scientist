// ================================================================
// alerteMateriauNonPrevu — Version réutilisable
//
// MISE À JOUR (réutilisabilité) :
//   - Les rôles destinataires ("Chef de Mission", "Admin") ne sont plus
//     codés en dur : lus depuis Projets_Config!Roles_Destinataires_Alertes
//     (même colonne que le script d'alerte d'inactivité — un seul réglage
//     pour tous les scripts d'alerte du projet).
//   - Bug corrigé : l'ancienne version ne gardait qu'UN SEUL email par
//     rôle (dernière ligne trouvée écrasait les précédentes). Corrigé :
//     tous les emails correspondant aux rôles configurés sont collectés.
//   - Nom du projet/produit dans le sujet et la signature de l'email lu
//     dynamiquement depuis Projets_Config!Nom_Projet (ligne du projet
//     actif), au lieu d'être codé en dur. Un autre déploiement/client
//     voit son propre nom de projet sans qu'aucune ligne de ce script
//     n'ait besoin d'être modifiée.
// ================================================================

const ANOMALIE_CONFIG = {
  SHEET_DETAILS  : "Details_Intervention",
  SHEET_OBJECTIFS: "Objectifs",
  SHEET_USERS    : "Utilisateurs",
  SHEET_PROJETS  : "Projets_Config",
  // Repli utilisé uniquement si Projets_Config n'a pas encore la colonne
  // Roles_Destinataires_Alertes, ou si elle existe mais est vide.
  // Choix volontairement restrictif : seul Admin reçoit l'alerte par
  // défaut, plutôt que d'élargir silencieusement à d'autres rôles.
  ROLES_PAR_DEFAUT: ["Admin"],
  // Repli utilisé uniquement si Projets_Config n'a pas la colonne Nom_Projet,
  // si elle est vide, ou si aucune ligne Actif=TRUE n'est trouvée.
  NOM_PROJET_PAR_DEFAUT: "Gestion de Chantier",
};

// ================================================================
// CONFIG DYNAMIQUE — rôles destinataires, lus depuis Projets_Config
// ================================================================
function _lireRolesDestinataires_Anomalie() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(ANOMALIE_CONFIG.SHEET_PROJETS);
  if (!SRC) {
    Logger.log("⚠️ Onglet " + ANOMALIE_CONFIG.SHEET_PROJETS + " introuvable — repli sur Admin uniquement");
    return ANOMALIE_CONFIG.ROLES_PAR_DEFAUT;
  }

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const iRoles  = headers.indexOf("Roles_Destinataires_Alertes");
  const iActif  = headers.indexOf("Actif");

  if (iRoles === -1) {
    Logger.log("⚠️ Colonne Roles_Destinataires_Alertes absente de Projets_Config — repli sur Admin uniquement");
    return ANOMALIE_CONFIG.ROLES_PAR_DEFAUT;
  }

  const data = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();
  const ligneActive = data.find(row => {
    const v = String(row[iActif]).trim().toUpperCase();
    return v === "TRUE" || v === "VRAI" || v === "1";
  });

  if (!ligneActive || !ligneActive[iRoles]) {
    Logger.log("⚠️ Aucun rôle configuré pour le projet actif — repli sur Admin uniquement");
    return ANOMALIE_CONFIG.ROLES_PAR_DEFAUT;
  }

  const roles = String(ligneActive[iRoles]).split(",").map(r => r.trim()).filter(r => r !== "");
  Logger.log("  ⚙️ Rôles destinataires : " + roles.join(", "));
  return roles;
}

// Lit le nom du projet/produit à afficher dans l'email (sujet + signature),
// depuis la ligne Actif=TRUE de Projets_Config. Repli sur une valeur neutre
// si l'onglet, la colonne, ou la ligne active sont introuvables — jamais
// d'erreur bloquante pour un simple problème d'affichage.
function _lireNomProjet_Anomalie() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(ANOMALIE_CONFIG.SHEET_PROJETS);
  if (!SRC) return ANOMALIE_CONFIG.NOM_PROJET_PAR_DEFAUT;

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const iNom   = headers.indexOf("Nom_Projet");
  const iActif = headers.indexOf("Actif");
  if (iNom === -1 || iActif === -1) return ANOMALIE_CONFIG.NOM_PROJET_PAR_DEFAUT;

  const data = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();
  const ligneActive = data.find(row => {
    const v = String(row[iActif]).trim().toUpperCase();
    return v === "TRUE" || v === "VRAI" || v === "1";
  });

  if (!ligneActive || !ligneActive[iNom]) return ANOMALIE_CONFIG.NOM_PROJET_PAR_DEFAUT;
  return String(ligneActive[iNom]).trim();
}

// Retourne TOUS les emails des utilisateurs dont le rôle figure dans
// `roles` — corrige le bug d'écrasement de l'ancienne version.
function _lireDestinataires_Anomalie(roles) {
  const SS    = SpreadsheetApp.getActiveSpreadsheet();
  const USERS = SS.getSheetByName(ANOMALIE_CONFIG.SHEET_USERS);
  const data  = USERS.getRange(2, 1, USERS.getLastRow() - 1, 4).getValues();

  const emails = new Set();
  data.forEach(row => {
    const role  = String(row[2]).trim();
    const email = String(row[0]).trim();
    if (email && roles.includes(role)) {
      emails.add(email);
    }
  });

  Logger.log("  👤 Destinataires (" + roles.join(", ") + ") : " + (emails.size ? [...emails].join(", ") : "aucun"));
  return [...emails];
}

function alerteMateriauNonPrevu() {
  const SS        = SpreadsheetApp.getActiveSpreadsheet();
  const DETAILS   = SS.getSheetByName(ANOMALIE_CONFIG.SHEET_DETAILS);
  const OBJECTIFS = SS.getSheetByName(ANOMALIE_CONFIG.SHEET_OBJECTIFS);

  // ── Destinataires — rôles lus dynamiquement depuis Projets_Config ──
  const roles = _lireRolesDestinataires_Anomalie();
  const destinatairesListe = _lireDestinataires_Anomalie(roles);
  const destinataires = destinatairesListe.join(",");

  // ── Nom du projet/produit — lu dynamiquement depuis Projets_Config ──
  const nomProjet = _lireNomProjet_Anomalie();

  // ── Lire les en-têtes Details_Intervention ─────────────────
  const detHeaders = DETAILS.getRange(1, 1, 1, DETAILS.getLastColumn()).getValues()[0];
  const detData    = DETAILS.getRange(2, 1, DETAILS.getLastRow() - 1, detHeaders.length).getValues();

  const iMat    = detHeaders.indexOf("ID_Materiel");
  const iLoc    = detHeaders.indexOf("ID_Localite");
  const iLocN   = detHeaders.indexOf("Localite");
  const iTache  = detHeaders.indexOf("Tache");
  const iDesign = detHeaders.indexOf("Designation");
  const iQte    = detHeaders.indexOf("Quantite_Nette_Calculee");
  const iDate   = detHeaders.indexOf("Date");
  const iGeo    = detHeaders.indexOf("Filtre_Geo_1");
  const iVerif  = detHeaders.indexOf("Anomalie_Signalee");

  if (iVerif === -1) {
    Logger.log("❌ Colonne 'Anomalie_Signalee' introuvable dans Details_Intervention");
    throw new Error("Colonne 'Anomalie_Signalee' introuvable — vérifier le nom exact dans Sheets");
  }

  // ── Lire les objectifs ─────────────────────────────────────
  const objHeaders = OBJECTIFS.getRange(1, 1, 1, OBJECTIFS.getLastColumn()).getValues()[0];
  const objData    = OBJECTIFS.getRange(2, 1, OBJECTIFS.getLastRow() - 1, objHeaders.length).getValues();

  const oLoc = objHeaders.indexOf("ID_Localite");
  const oMat = objHeaders.indexOf("ID_Materiel");

  const objSet = new Set();
  objData.forEach(row => {
    const key = String(row[oLoc]).trim() + "|" + String(row[oMat]).trim();
    objSet.add(key);
  });

  // ── Détecter les anomalies non encore signalées ────────────
  const anomalies = [];

  detData.forEach((row, i) => {
    const loc   = String(row[iLoc]).trim();
    const mat   = String(row[iMat]).trim();
    const verif = String(row[iVerif]).trim().toUpperCase();

    if (!loc || !mat) return;
    if (verif === "TRUE" || verif === "VRAI" || verif === "1") return;

    const key = loc + "|" + mat;
    if (!objSet.has(key)) {
      anomalies.push({
        rowIndex : i + 2,
        colVerif : iVerif + 1,
        geo      : String(row[iGeo]).trim(),
        loc      : loc,
        locNom   : String(row[iLocN]).trim(),
        tache    : String(row[iTache]).trim(),
        design   : String(row[iDesign]).trim(),
        qte      : row[iQte],
        date     : Utilities.formatDate(
                     new Date(row[iDate]),
                     Session.getScriptTimeZone(),
                     "dd/MM/yyyy"
                   ),
      });
    }
  });

  if (anomalies.length === 0) {
    Logger.log("✅ Aucune anomalie nouvelle détectée");
    return;
  }

  Logger.log("🚨 " + anomalies.length + " anomalie(s) détectée(s)");

  // ── Construire le corps de l'email ─────────────────────────
  let corps = "Bonjour,\n\n";
  corps += anomalies.length + " matériel(s) non prévu(s) ont été enregistrés :\n\n";

  anomalies.forEach((a, i) => {
    corps += "─────────────────────────────\n";
    corps += "Anomalie " + (i + 1) + "\n";
    corps += " Localité    : " + a.locNom + " (" + a.loc + ")\n";
    corps += " Département : " + a.geo    + "\n";
    corps += " Tâche       : " + a.tache  + "\n";
    corps += " Matériel    : " + a.design + "\n";
    corps += " Quantité    : " + a.qte    + "\n";
    corps += " Date        : " + a.date   + "\n\n";
  });

  corps += "─────────────────────────────\n";
  corps += "⚠️ Ces matériels ne sont pas prévus dans les objectifs.\n";
  corps += "Veuillez vérifier et mettre à jour les objectifs si nécessaire.\n\n";
  corps += "— " + nomProjet;

  if (!destinataires) {
    Logger.log("❌ Aucun destinataire trouvé — email non envoyé, marquage annulé");
    return;
  }

  try {
    GmailApp.sendEmail(
      destinataires,
      "🚨 " + anomalies.length + " matériel(s) non prévu(s) — " + nomProjet,
      corps
    );
    Logger.log("✅ Email envoyé à : " + destinataires);

    anomalies.forEach(a => {
      DETAILS.getRange(a.rowIndex, a.colVerif).setValue(true);
      Logger.log("  ✅ Marqué TRUE → ligne " + a.rowIndex + " (" + a.design + " / " + a.loc + ")");
    });

    Logger.log("✅ " + anomalies.length + " ligne(s) marquée(s) Anomalie_Signalee = TRUE");

  } catch(e) {
    Logger.log("❌ Échec envoi email — marquage annulé : " + e.message);
    throw e;
  }
}