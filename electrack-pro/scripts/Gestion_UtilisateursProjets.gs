// ================================================================
// Gestion_UtilisateursProjets.gs
//
// L'onglet "Utilisateurs_Projets" (table de jonction ID_UP / Email_User /
// ID_Projet, créée suite à l'audit pour remplacer l'EnumList fragile
// Utilisateurs.Projet_Affecte) n'était alimenté par AUCUN mécanisme
// automatique : les lignes étaient créées à la main. Ce script comble
// ce trou, sur le même principe que Gestion_TopLocalitesTri.gs :
//
//   1. SYNCHRONISATION (création) :
//      Pour chaque utilisateur Actif=TRUE dans "Utilisateurs", on éclate
//      son Projet_Affecte (potentiellement multi-valeurs séparées par
//      virgule) et on vérifie, pour chaque ID_Projet obtenu, qu'une ligne
//      Email_User + ID_Projet existe déjà dans Utilisateurs_Projets.
//      Si absente ET que l'ID_Projet est valide (existe dans
//      Projets_Config), on la crée avec un ID_UP unique
//      (Utilities.getUuid().substring(0,8), cohérent avec les autres ID
//      du projet — cf. correctif audit sur les ID corrompus de Geo_Config
//      et Top_Localites_Tri).
//
//   2. DÉTECTION D'ANOMALIES (jamais de suppression automatique — même
//      principe que Retrait_Referentiels.gs : on signale, l'admin décide) :
//      - ID_Projet dans Projet_Affecte introuvable dans Projets_Config
//        (typo probable sur l'EnumList saisie à la main).
//      - Ligne Utilisateurs_Projets orpheline : Email_User introuvable
//        dans Utilisateurs, ou utilisateur retrouvé mais Actif=FALSE.
//      - Ligne Utilisateurs_Projets orpheline : ID_Projet introuvable
//        dans Projets_Config.
//      - Doublon strict (même Email_User + même ID_Projet en double
//        dans Utilisateurs_Projets).
//
//   3. RAPPORT EMAIL :
//      Envoyé uniquement s'il y a eu une création ou une anomalie
//      détectée. Destinataires lus dynamiquement depuis
//      Projets_Config!Roles_Destinataires_Alertes (repli : Admin
//      uniquement), comme les autres scripts d'alerte du projet.
//
// Lecture des colonnes par NOM d'en-tête (pas par lettre), écriture en
// une seule passe, wrapper de retry — conventions identiques au reste
// du projet. Aucun préfixe client/projet dans les noms (produit
// réutilisable multi-client, V2 = un classeur par client).
//
// ⚠️ Avant déploiement en production : tester d'abord sur une copie du
// classeur ("... TEST" / "... COPIE"), conformément au workflow habituel.
// ================================================================

const CONFIG_UTIL_PROJETS = {
  SHEET_UTILISATEURS   : "Utilisateurs",
  SHEET_PROJETS_CONFIG : "Projets_Config",
  SHEET_UP             : "Utilisateurs_Projets",

  // Colonnes attendues dans Utilisateurs
  COL_U_EMAIL          : "Email",
  COL_U_PROJET_AFFECTE : "Projet_Affecte",
  COL_U_ACTIF          : "Actif",

  // Colonnes attendues dans Projets_Config
  COL_PC_ID_PROJET     : "ID_Projet",

  // Colonnes attendues dans Utilisateurs_Projets
  COL_UP_ID            : "ID_UP",
  COL_UP_EMAIL         : "Email_User",
  COL_UP_PROJET        : "ID_Projet",

  SEPARATEUR_PROJETS   : ",",   // Projet_Affecte : "PROJ_A" ou "PROJ_A, PROJ_B"
  LONGUEUR_ID          : 8,     // cohérent avec les autres ID hexa du projet

  // Repli si Projets_Config n'a pas la colonne Roles_Destinataires_Alertes,
  // si elle est vide, ou si aucune ligne Actif=TRUE n'est trouvée.
  ROLES_PAR_DEFAUT       : ["Admin"],
  NOM_PROJET_PAR_DEFAUT  : "Gestion de Chantier",
};

// ================================================================
// DÉCLENCHEUR — Exécuter configurerDeclencheur_UtilisateursProjets()
// UNE SEULE FOIS PAR DÉPLOIEMENT/CLASSEUR CLIENT.
// Cadence quotidienne : la provision d'utilisateurs est un événement
// rare, contrairement aux snapshots de terrain — inutile de consommer
// le quota Apps Script toutes les 30 min pour ça.
// ================================================================
function configurerDeclencheur_UtilisateursProjets() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "synchroniserUtilisateursProjets") {
      ScriptApp.deleteTrigger(t);
      Logger.log("🗑 Supprimé : ancien trigger synchroniserUtilisateursProjets");
    }
  });

  ScriptApp.newTrigger("synchroniserUtilisateursProjets")
    .timeBased()
    .everyDays(1)
    .atHour(4)
    .create();

  Logger.log("✅ synchroniserUtilisateursProjets → tous les jours vers 4h");
}

// ================================================================
// FONCTION PRINCIPALE
// ================================================================
function synchroniserUtilisateursProjets() {
  Logger.log("🚀 synchroniserUtilisateursProjets démarré");
  const lock = LockService.getScriptLock();
  const gotLock = lock.tryLock(5000);
  if (!gotLock) {
    Logger.log("⏭ Exécution précédente encore en cours, passage ignoré.");
    return;
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    const shU  = ss.getSheetByName(CONFIG_UTIL_PROJETS.SHEET_UTILISATEURS);
    const shPC = ss.getSheetByName(CONFIG_UTIL_PROJETS.SHEET_PROJETS_CONFIG);
    const shUP = ss.getSheetByName(CONFIG_UTIL_PROJETS.SHEET_UP);
    if (!shU || !shPC || !shUP) {
      throw new Error("Onglet(s) introuvable(s) : vérifier Utilisateurs / Projets_Config / Utilisateurs_Projets");
    }

    // ── 1. Lire les projets valides (ID_Projet existants) ──────────
    const projetsValides = _lireProjetsValides(shPC);

    // ── 2. Lire les utilisateurs actifs et leurs projets affectés ──
    const utilisateurs = _lireUtilisateurs(shU); // [{email, actif, projets:[...]}]

    // ── 3. Lire l'état actuel de Utilisateurs_Projets ───────────────
    const headersUP = shUP.getRange(1, 1, 1, shUP.getLastColumn()).getValues()[0];
    const iID    = headersUP.indexOf(CONFIG_UTIL_PROJETS.COL_UP_ID);
    const iEmail = headersUP.indexOf(CONFIG_UTIL_PROJETS.COL_UP_EMAIL);
    const iProj  = headersUP.indexOf(CONFIG_UTIL_PROJETS.COL_UP_PROJET);
    if (iID === -1 || iEmail === -1 || iProj === -1) {
      throw new Error("Colonnes ID_UP / Email_User / ID_Projet introuvables dans Utilisateurs_Projets");
    }

    const lastRowUP = shUP.getLastRow();
    const dataUP = lastRowUP >= 2
      ? shUP.getRange(2, 1, lastRowUP - 1, headersUP.length).getValues()
      : [];

    const idsExistants = new Set(
      dataUP.map(r => String(r[iID]).trim()).filter(v => v !== "")
    );

    const pairesExistantes = new Set();     // "email||idprojet"
    const pairesVues = new Set();           // pour détecter les doublons stricts
    const anomalies = [];

    dataUP.forEach((row, idx) => {
      const email = String(row[iEmail]).trim();
      const idProjet = String(row[iProj]).trim();
      if (!email && !idProjet) return; // ligne vide, on ignore

      const cle = email.toLowerCase() + "||" + idProjet;
      pairesExistantes.add(cle);

      if (pairesVues.has(cle)) {
        anomalies.push("Doublon strict (ligne " + (idx + 2) + ") : " + email + " / " + idProjet);
      }
      pairesVues.add(cle);

      const userConnu = utilisateurs.find(u => u.email.toLowerCase() === email.toLowerCase());
      if (!userConnu) {
        anomalies.push("Ligne orpheline (ligne " + (idx + 2) + ") : email \"" + email + "\" absent de Utilisateurs");
      } else if (!userConnu.actif) {
        anomalies.push("Ligne pour utilisateur INACTIF (ligne " + (idx + 2) + ") : " + email + " / " + idProjet);
      }

      if (idProjet && !projetsValides.has(idProjet)) {
        anomalies.push("ID_Projet inconnu (ligne " + (idx + 2) + ") : \"" + idProjet + "\" absent de Projets_Config");
      }
    });

    // ── 4. Déterminer les lignes manquantes à créer ─────────────────
    const lignesACreer = [];

    utilisateurs.forEach(u => {
      if (!u.actif) return; // on ne provisionne que les utilisateurs actifs

      u.projets.forEach(idProjet => {
        if (!idProjet) return;

        if (!projetsValides.has(idProjet)) {
          anomalies.push("Projet_Affecte invalide pour " + u.email + " : \"" + idProjet + "\" introuvable dans Projets_Config (typo probable)");
          return; // on ne crée pas de ligne pour un projet qui n'existe pas
        }

        const cle = u.email.toLowerCase() + "||" + idProjet;
        if (pairesExistantes.has(cle)) return; // déjà présent

        const nouvelId = _genererIdUnique_UtilisateursProjets(idsExistants);
        lignesACreer.push({ id: nouvelId, email: u.email, idProjet });
        pairesExistantes.add(cle); // évite doublon si Projet_Affecte contient 2x le même ID
      });
    });

    // ── 5. Écriture en une seule passe (append) ─────────────────────
    if (lignesACreer.length > 0) {
      const startRow = shUP.getLastRow() + 1;
      const valeurs = lignesACreer.map(l => {
        const row = new Array(headersUP.length).fill("");
        row[iID] = l.id;
        row[iEmail] = l.email;
        row[iProj] = l.idProjet;
        return row;
      });
      shUP.getRange(startRow, 1, valeurs.length, headersUP.length).setValues(valeurs);
      Logger.log("✅ " + lignesACreer.length + " ligne(s) créée(s) dans Utilisateurs_Projets");
    } else {
      Logger.log("✅ Aucune ligne à créer — tous les utilisateurs actifs sont déjà provisionnés");
    }

    if (anomalies.length > 0) {
      Logger.log("⚠️ " + anomalies.length + " anomalie(s) détectée(s) :");
      anomalies.forEach(a => Logger.log("   - " + a));
    }

    // ── 6. Rapport email si création(s) et/ou anomalie(s) ───────────
    if (lignesACreer.length > 0 || anomalies.length > 0) {
      avecRetry_UtilisateursProjets(() => _envoyerRapport_UtilisateursProjets(lignesACreer, anomalies));
    }

    Logger.log("🏁 synchroniserUtilisateursProjets terminé");
  } finally {
    lock.releaseLock();
  }
}

// ================================================================
// LECTURE
// ================================================================

function _lireProjetsValides(shPC) {
  const headers = shPC.getRange(1, 1, 1, shPC.getLastColumn()).getValues()[0];
  const iId = headers.indexOf(CONFIG_UTIL_PROJETS.COL_PC_ID_PROJET);
  if (iId === -1) throw new Error("Colonne ID_Projet introuvable dans Projets_Config");

  const lastRow = shPC.getLastRow();
  const set = new Set();
  if (lastRow >= 2) {
    shPC.getRange(2, iId + 1, lastRow - 1, 1).getValues().forEach(r => {
      const v = String(r[0]).trim();
      if (v) set.add(v);
    });
  }
  return set;
}

function _lireUtilisateurs(shU) {
  const headers = shU.getRange(1, 1, 1, shU.getLastColumn()).getValues()[0];
  const iEmail  = headers.indexOf(CONFIG_UTIL_PROJETS.COL_U_EMAIL);
  const iProjet = headers.indexOf(CONFIG_UTIL_PROJETS.COL_U_PROJET_AFFECTE);
  const iActif  = headers.indexOf(CONFIG_UTIL_PROJETS.COL_U_ACTIF);
  if (iEmail === -1 || iProjet === -1) {
    throw new Error("Colonnes Email / Projet_Affecte introuvables dans Utilisateurs");
  }

  const lastRow = shU.getLastRow();
  if (lastRow < 2) return [];

  const data = shU.getRange(2, 1, lastRow - 1, headers.length).getValues();
  return data
    .filter(row => String(row[iEmail]).trim() !== "")
    .map(row => {
      const email = String(row[iEmail]).trim();
      const actifRaw = iActif !== -1 ? String(row[iActif]).trim().toUpperCase() : "TRUE";
      const actif = actifRaw === "TRUE" || actifRaw === "VRAI" || actifRaw === "1";
      const projets = String(row[iProjet] || "")
        .split(CONFIG_UTIL_PROJETS.SEPARATEUR_PROJETS)
        .map(p => p.trim())
        .filter(p => p !== "");
      return { email, actif, projets };
    });
}

// ================================================================
// GÉNÉRATION D'ID UNIQUE (même principe que Gestion_TopLocalitesTri.gs)
// ================================================================
function _genererIdUnique_UtilisateursProjets(idsExistants) {
  let id;
  do {
    id = Utilities.getUuid().substring(0, CONFIG_UTIL_PROJETS.LONGUEUR_ID);
  } while (idsExistants.has(id));
  idsExistants.add(id);
  return id;
}

// ================================================================
// CONFIG DYNAMIQUE — rôles destinataires + nom du projet, lus depuis
// Projets_Config (mêmes colonnes que les autres scripts d'alerte).
// Noms suffixés "_UtilisateursProjets" pour éviter toute collision de
// nom de fonction avec les autres fichiers .gs du même classeur.
// ================================================================
function _lireRolesDestinataires_UtilisateursProjets() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(CONFIG_UTIL_PROJETS.SHEET_PROJETS_CONFIG);
  if (!SRC) return CONFIG_UTIL_PROJETS.ROLES_PAR_DEFAUT;

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const iRoles = headers.indexOf("Roles_Destinataires_Alertes");
  const iActif = headers.indexOf("Actif");
  if (iRoles === -1) return CONFIG_UTIL_PROJETS.ROLES_PAR_DEFAUT;

  const data = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();
  const ligneActive = data.find(row => {
    const v = String(row[iActif]).trim().toUpperCase();
    return v === "TRUE" || v === "VRAI" || v === "1";
  });
  if (!ligneActive || !ligneActive[iRoles]) return CONFIG_UTIL_PROJETS.ROLES_PAR_DEFAUT;

  return String(ligneActive[iRoles]).split(",").map(r => r.trim()).filter(r => r !== "");
}

function _lireNomProjet_UtilisateursProjets() {
  const SS  = SpreadsheetApp.getActiveSpreadsheet();
  const SRC = SS.getSheetByName(CONFIG_UTIL_PROJETS.SHEET_PROJETS_CONFIG);
  if (!SRC) return CONFIG_UTIL_PROJETS.NOM_PROJET_PAR_DEFAUT;

  const headers = SRC.getRange(1, 1, 1, SRC.getLastColumn()).getValues()[0];
  const iNom = headers.indexOf("Nom_Projet");
  const iActif = headers.indexOf("Actif");
  if (iNom === -1) return CONFIG_UTIL_PROJETS.NOM_PROJET_PAR_DEFAUT;

  const data = SRC.getRange(2, 1, SRC.getLastRow() - 1, headers.length).getValues();
  const ligneActive = data.find(row => {
    const v = String(row[iActif]).trim().toUpperCase();
    return v === "TRUE" || v === "VRAI" || v === "1";
  });
  if (!ligneActive || !ligneActive[iNom]) return CONFIG_UTIL_PROJETS.NOM_PROJET_PAR_DEFAUT;

  return String(ligneActive[iNom]).trim();
}

function _lireDestinataires_UtilisateursProjets(roles) {
  const SS = SpreadsheetApp.getActiveSpreadsheet();
  const USERS = SS.getSheetByName(CONFIG_UTIL_PROJETS.SHEET_UTILISATEURS);
  const headers = USERS.getRange(1, 1, 1, USERS.getLastColumn()).getValues()[0];
  const iEmail = headers.indexOf(CONFIG_UTIL_PROJETS.COL_U_EMAIL);
  const iRole  = headers.indexOf("Role");

  const data = USERS.getRange(2, 1, USERS.getLastRow() - 1, headers.length).getValues();
  const emails = new Set();
  data.forEach(row => {
    const role = String(row[iRole]).trim();
    const email = String(row[iEmail]).trim();
    if (email && roles.includes(role)) emails.add(email);
  });
  return [...emails];
}

// ================================================================
// RAPPORT EMAIL
// ================================================================
function _envoyerRapport_UtilisateursProjets(lignesCreees, anomalies) {
  const roles = _lireRolesDestinataires_UtilisateursProjets();
  const destinataires = _lireDestinataires_UtilisateursProjets(roles);
  const nomProjet = _lireNomProjet_UtilisateursProjets();

  if (destinataires.length === 0) {
    Logger.log("❌ Aucun destinataire trouvé pour le rapport Utilisateurs_Projets — envoi annulé");
    return;
  }

  let sujet = "🔄 " + nomProjet + " — Synchronisation Utilisateurs_Projets";
  let corps = "Synchronisation automatique de l'onglet Utilisateurs_Projets\n";
  corps += "─────────────────────────────\n\n";

  if (lignesCreees.length > 0) {
    corps += "✅ " + lignesCreees.length + " ligne(s) créée(s) :\n";
    lignesCreees.forEach(l => {
      corps += "   - " + l.email + " → " + l.idProjet + " (ID_UP: " + l.id + ")\n";
    });
    corps += "\n";
  }

  if (anomalies.length > 0) {
    sujet = "⚠️ " + nomProjet + " — Anomalies Utilisateurs_Projets";
    corps += "⚠️ " + anomalies.length + " anomalie(s) à vérifier manuellement :\n";
    anomalies.forEach(a => { corps += "   - " + a + "\n"; });
    corps += "\nCes lignes ne sont PAS supprimées automatiquement — merci de les\n";
    corps += "vérifier dans Utilisateurs_Projets et de corriger à la main si besoin.\n";
  }

  corps += "\n— " + nomProjet;

  GmailApp.sendEmail(destinataires.join(","), sujet, corps);
  Logger.log("📧 Rapport envoyé à : " + destinataires.join(", "));
}

// ================================================================
// UTILITAIRE — retry (suffixé pour éviter toute collision avec
// l'avecRetry() déjà défini dans Alerte_Inactivite.gs)
// ================================================================
function avecRetry_UtilisateursProjets(fn, tentatives = 3, delaiMs = 2000) {
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
