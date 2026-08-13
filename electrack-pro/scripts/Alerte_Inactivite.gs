// ================================================================
// Alerte_Inactivite — Version réutilisable
// Envoie un email listant les localités inactives depuis plus de
// N jours et non terminées.
//
// MISE À JOUR (réutilisabilité) :
//   - Roles_Destinataires_Alertes et Seuil_Inactivite_Jours ne sont
//     plus codés en dur : ils sont lus depuis Projets_Config (ligne
//     du projet actif), exactement comme COEFF_HTA_GLOBAL/COEFF_BT_GLOBAL
//     dans Parametres_Poids. Un autre déploiement/client peut donc
//     changer ces réglages sans toucher au script.
//   - Bug corrigé : l'ancienne version ne gardait qu'UN SEUL email par
//     rôle (la dernière ligne trouvée écrasait les précédentes). S'il y
//     avait 2 "Admin" dans Utilisateurs, un seul recevait l'alerte,
//     silencieusement. Corrigé : tous les emails correspondant aux
//     rôles configurés sont maintenant collectés.
//   - Nom du projet/produit dans le sujet et la signature de l'email lu
//     dynamiquement depuis Projets_Config!Nom_Projet (ligne du projet
//     actif), au lieu d'être codé en dur.
//
// MISE À JOUR (fiabilité, session précédente) : wrapper avecRetry()
// autour des lectures Sheets, pour absorber les erreurs serveur
// ponctuelles ("We're sorry, a server error occurred...").
// ================================================================

const INACTIVITE_CONFIG = {
  SHEET_LOCALITES    : "Top_Localites",
  SHEET_INTERVENTIONS: "Interventions",
  SHEET_USERS        : "Utilisateurs",
  SHEET_PROJETS      : "Projets_Config",
  // Valeurs de repli utilisées UNIQUEMENT si Projets_Config n'a pas
  // encore les colonnes Roles_Destinataires_Alertes / Seuil_Inactivite_Jours
  // (ex. avant migration), ou si la colonne existe mais est vide.
  // Choix volontairement restrictif : seul Admin reçoit l'alerte par
  // défaut, plutôt que d'élargir silencieusement à d'autres rôles.
  ROLES_PAR_DEFAUT   : ["Admin"],
  SEUIL_PAR_DEFAUT   : 30,
  JOUR_ENVOI         : ScriptApp.WeekDay.MONDAY,
  HEURE_ENVOI        : 5,
  // Repli si Projets_Config n'a pas la colonne Nom_Projet, si elle est
  // vide, ou si aucune ligne Actif=TRUE n'est trouvée.
  NOM_PROJET_PAR_DEFAUT: "Gestion de Chantier",
};

// ================================================================
// DÉCLENCHEUR — Exécuter configurerDeclencheurInactivite() UNE SEULE FOIS
// ================================================================
function configurerDeclencheurInactivite() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "alerteInactiviteLocalites") {
      ScriptApp.deleteTrigger(t);
      Logger.log("🗑 Supprimé : alerteInactiviteLocalites");
    }
  });

  ScriptApp.newTrigger("alerteInactiviteLocalites")
    .timeBased()
    .onWeekDay(INACTIVITE_CONFIG.JOUR_ENVOI)
    .atHour(INACTIVITE_CONFIG.HEURE_ENVOI)
    .create();

  Logger.log("✅ alerteInactiviteLocalites → chaque lundi " + INACTIVITE_CONFIG.HEURE_ENVOI + "h");
}

// ================================================================
// UTILITAIRES
// ================================================================

function diffJours(date1, date2) {
  const MS_PAR_JOUR = 1000 * 60 * 60 * 24;
  return Math.floor((date2 - date1) / MS_PAR_JOUR);
}
function round2(v) {
  return Math.round(v * 100) / 100;
}

function avecRetry(fn, tentatives = 3, delaiMs = 2000) {
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

// ================================================================
// CONFIG DYNAMIQUE — lue depuis Projets_Config (ligne du projet actif)
// ================================================================

function lireConfigAlerte() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(INACTIVITE_CONFIG.SHEET_PROJETS);
  if (!SRC) {
    Logger.log("⚠️ Onglet " + INACTIVITE_CONFIG.SHEET_PROJETS + " introuvable — repli sur Admin uniquement");
    return {
      roles: INACTIVITE_CONFIG.ROLES_PAR_DEFAUT,
      seuilJours: INACTIVITE_CONFIG.SEUIL_PAR_DEFAUT,
      nomProjet: INACTIVITE_CONFIG.NOM_PROJET_PAR_DEFAUT,
    };
  }

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const iRoles  = headers.indexOf("Roles_Destinataires_Alertes");
  const iSeuil  = headers.indexOf("Seuil_Inactivite_Jours");
  const iActif  = headers.indexOf("Actif");
  const iNom    = headers.indexOf("Nom_Projet");

  const data = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();
  const ligneActive = data.find(row => {
    const v = String(row[iActif]).trim().toUpperCase();
    return v === "TRUE" || v === "VRAI" || v === "1";
  });

  let roles = INACTIVITE_CONFIG.ROLES_PAR_DEFAUT;
  let seuilJours = INACTIVITE_CONFIG.SEUIL_PAR_DEFAUT;
  let nomProjet = INACTIVITE_CONFIG.NOM_PROJET_PAR_DEFAUT;

  if (!ligneActive) {
    Logger.log("⚠️ Aucun projet Actif trouvé dans " + INACTIVITE_CONFIG.SHEET_PROJETS + " — repli sur Admin uniquement");
    return { roles, seuilJours, nomProjet };
  }

  if (iRoles !== -1 && ligneActive[iRoles]) {
    roles = String(ligneActive[iRoles]).split(",").map(r => r.trim()).filter(r => r !== "");
  } else {
    Logger.log("⚠️ Colonne Roles_Destinataires_Alertes absente/vide dans Projets_Config — repli sur : " + roles.join(", "));
  }

  if (iSeuil !== -1 && ligneActive[iSeuil] !== "" && ligneActive[iSeuil] !== null) {
    seuilJours = Number(ligneActive[iSeuil]) || INACTIVITE_CONFIG.SEUIL_PAR_DEFAUT;
  } else {
    Logger.log("⚠️ Colonne Seuil_Inactivite_Jours absente/vide dans Projets_Config — repli sur : " + seuilJours + "j");
  }

  if (iNom !== -1 && ligneActive[iNom]) {
    nomProjet = String(ligneActive[iNom]).trim();
  } else {
    Logger.log("⚠️ Colonne Nom_Projet absente/vide dans Projets_Config — repli sur : " + nomProjet);
  }

  Logger.log("  ⚙️ Config alerte → rôles: [" + roles.join(", ") + "] | seuil: " + seuilJours + "j | projet: " + nomProjet);
  return { roles, seuilJours, nomProjet };
}

// ================================================================
// LECTURE DES DONNÉES
// ================================================================

// Retourne TOUS les emails des utilisateurs dont le rôle figure dans
// `roles` (liste dynamique) — corrige le bug d'écrasement de
// l'ancienne version qui ne gardait qu'un email par rôle.
function lireDestinataires(roles) {
  const SS    = SpreadsheetApp.getActiveSpreadsheet();
  const USERS = SS.getSheetByName(INACTIVITE_CONFIG.SHEET_USERS);
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

function lireLocalites() {
  const SS      = SpreadsheetApp.getActiveSpreadsheet();
  const SRC     = SS.getSheetByName(INACTIVITE_CONFIG.SHEET_LOCALITES);
  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const data    = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();

  const idx = name => {
    const i = headers.indexOf(name);
    if (i < 0) throw new Error("Colonne introuvable dans " + INACTIVITE_CONFIG.SHEET_LOCALITES + " : " + name);
    return i;
  };

  return {
    data,
    iID    : idx("ID_Localite"),
    iNom   : idx("Localite"),
    iDept  : idx("Departement"),
    iAvnt  : idx("Avancement"),
    iStatut: idx("Statut"),
  };
}

function lireDerniereIntervention() {
  const SS      = SpreadsheetApp.getActiveSpreadsheet();
  const SRC     = SS.getSheetByName(INACTIVITE_CONFIG.SHEET_INTERVENTIONS);
  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const data    = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();

  const iLoc  = headers.indexOf("ID_Localite");
  const iDate = headers.indexOf("Date_Saisie");

  if (iLoc < 0 || iDate < 0) {
    throw new Error("Colonnes ID_Localite ou Date_Saisie introuvables dans Interventions");
  }

  const derniereDate = new Map();

  data.forEach(row => {
    const loc  = String(row[iLoc]).trim();
    const date = row[iDate];
    if (!loc || !date) return;

    const d = new Date(date);
    if (!derniereDate.has(loc) || d > derniereDate.get(loc)) {
      derniereDate.set(loc, d);
    }
  });

  Logger.log("  📅 " + derniereDate.size + " localités avec interventions trouvées");
  return derniereDate;
}

// ================================================================
// DÉTECTION DES INACTIVES
// ================================================================

function detecterInactives(localites, derniereIntervention, seuilJours) {
  const aujourd_hui = new Date();
  const inactives   = [];

  localites.data.forEach(row => {
    const id     = String(row[localites.iID]).trim();
    const nom    = String(row[localites.iNom]).trim();
    const dept   = String(row[localites.iDept]).trim();
    const avnt   = round2((Number(row[localites.iAvnt]) || 0) * 100);
    const statut = String(row[localites.iStatut]).trim();

    if (!id) return;

    if (statut === "Terminé" || avnt >= 100) {
      Logger.log("  ⏭ " + nom + " → Terminée, ignorée");
      return;
    }

    let joursInactivite;
    if (derniereIntervention.has(id)) {
      joursInactivite = diffJours(derniereIntervention.get(id), aujourd_hui);
    } else {
      joursInactivite = 999; // Jamais d'intervention
    }

    if (joursInactivite >= seuilJours) {
      inactives.push({
        id             : id,
        nom            : nom,
        dept           : dept,
        avnt           : avnt,
        joursInactivite: joursInactivite,
        dernierContact : derniereIntervention.has(id)
          ? Utilities.formatDate(
              derniereIntervention.get(id),
              Session.getScriptTimeZone(),
              "dd/MM/yyyy"
            )
          : "Aucune intervention",
      });

      Logger.log("  🚨 " + nom + " → " + joursInactivite + " jours d'inactivité");
    }
  });

  inactives.sort((a, b) => b.joursInactivite - a.joursInactivite);

  return inactives;
}

// ================================================================
// CONSTRUCTION DE L'EMAIL
// ================================================================

function construireEmail(inactives, seuilJours, nomProjet) {
  const aujourd_hui = Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    "dd/MM/yyyy"
  );

  let corps = "Bonjour,\n\n";
  corps += "⚠️ " + inactives.length + " localité(s) sans activité depuis plus de ";
  corps += seuilJours + " jours (au " + aujourd_hui + ") :\n\n";

  const parDept = {};
  inactives.forEach(loc => {
    if (!parDept[loc.dept]) parDept[loc.dept] = [];
    parDept[loc.dept].push(loc);
  });

  Object.keys(parDept).sort().forEach(dept => {
    corps += "════════════════════════════\n";
    corps += "📍 " + dept + "\n";
    corps += "════════════════════════════\n";

    parDept[dept].forEach((loc, i) => {
      const jours = loc.joursInactivite === 999
        ? "Jamais démarrée"
        : loc.joursInactivite + " jours";

      corps += "\n  " + (i + 1) + ". " + loc.nom + "\n";
      corps += "     🕒 Inactivité     : " + jours + "\n";
      corps += "     📅 Dernier contact : " + loc.dernierContact + "\n";
      corps += "     📊 Avancement      : " + loc.avnt + "%\n";
    });

    corps += "\n";
  });

  corps += "─────────────────────────────\n";
  corps += "Action requise : vérifier l'avancement de ces chantiers\n";
  corps += "et relancer les équipes concernées.\n\n";
  corps += "— " + (nomProjet || "Gestion de Chantier");

  return corps;
}

// ================================================================
// FONCTION PRINCIPALE
// ================================================================

function alerteInactiviteLocalites() {
  Logger.log("🚀 alerteInactiviteLocalites démarré");

  try {
    // 1. Config dynamique (rôles + seuil + nom du projet) — Projets_Config
    const { roles, seuilJours, nomProjet } = avecRetry(() => lireConfigAlerte());

    // 2. Destinataires — tous les emails correspondant aux rôles configurés
    const destinatairesListe = avecRetry(() => lireDestinataires(roles));
    const destinataires = destinatairesListe.join(",");

    if (!destinataires) {
      Logger.log("❌ Aucun destinataire trouvé — arrêt");
      return;
    }

    // 3. Données
    const localites            = avecRetry(() => lireLocalites());
    const derniereIntervention = avecRetry(() => lireDerniereIntervention());

    // 4. Détection (calcul pur, pas d'appel Sheets — pas de retry nécessaire)
    const inactives = detecterInactives(localites, derniereIntervention, seuilJours);

    if (inactives.length === 0) {
      Logger.log("✅ Aucune localité inactive détectée — pas d'email envoyé");
      return;
    }

    Logger.log("🚨 " + inactives.length + " localité(s) inactive(s) détectée(s)");

    const corps = construireEmail(inactives, seuilJours, nomProjet);
    const sujet = "⚠️ " + inactives.length
      + " localité(s) inactive(s) depuis +"
      + seuilJours
      + "j — " + nomProjet;

    GmailApp.sendEmail(destinataires, sujet, corps);
    Logger.log("✅ Email envoyé à : " + destinataires);

  } catch(e) {
    Logger.log("❌ alerteInactiviteLocalites — " + e.message);
    throw e;
  }
}

// ================================================================
// TEST & DEBUG
// ================================================================

function debugInactivite() {
  Logger.log("🔍 DEBUG — lecture seule, pas d'email envoyé");
  const { roles, seuilJours, nomProjet } = avecRetry(() => lireConfigAlerte());
  const localites              = avecRetry(() => lireLocalites());
  const derniereIntervention   = avecRetry(() => lireDerniereIntervention());
  const inactives              = detecterInactives(localites, derniereIntervention, seuilJours);

  Logger.log("📊 " + inactives.length + " localité(s) inactive(s)");
  Logger.log("─── Corps email ───");
  Logger.log(construireEmail(inactives, seuilJours, nomProjet));
}