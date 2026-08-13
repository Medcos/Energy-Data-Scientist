/**
 * Snapshot_HelperCalcul.gs
 *
 * Recalcule Helper_Calcul en une passe et écrit le résultat en valeurs statiques
 * (remplace la chaîne ARRAYFORMULA/BYROW live). Alimente Top_Localites,
 * Recap_Localites et Recap_Materiaux_Realisés, qui lisent Helper_Calcul par
 * référence de cellule (SUMPRODUCT/SUMIFS/VLOOKUP).
 *
 * Reproduit exactement la logique actuellement en formules GSheets dans
 * Helper_Calcul (colonnes G à L), vérifiée contre le fichier réel avant écriture
 * de ce script. Les colonnes Localite/Nom_Geo_1 (M, N) sont réintégrées ici :
 * bien qu'aucune des 3 feuilles Recap_* ne les lise (vérifié par scan complet
 * du classeur), un 4e consommateur a été identifié — Slice_Depassements /
 * vue "Dépassements" côté AppSheet — qui affiche le nom de la localité en
 * première colonne. Plutôt que de recréer ce champ via une colonne virtuelle
 * AppSheet (SELECT/LOOKUP), on le réintègre ici pour rester cohérent avec le
 * rôle de Helper_Calcul comme table de snapshot dénormalisée.
 * Source : Localités[ID_Localite] -> Localite, Nom_Geo_1 (déjà dénormalisées
 * dans Localités elle-même, une seule jointure suffit).
 *
 * Colonne Categorie (O) : ajoutée pour rendre les formules Top_Localites
 * (A_Travaux_HTA/BT, Avancement_HTA/BT_%) indépendantes de toute liste de
 * noms de tâches codée en dur. Elle reflète Parametres_Poids[Categorie]
 * ("Travaux HTA" / "Travaux BT" / "Global") — source unique. Ajouter une
 * nouvelle tâche dans Parametres_Poids avec la bonne Categorie suffit
 * désormais ; aucune formule Sheets ni script ne doit être modifiée.
 *
 * Colonne Actif (Parametres_Poids) : lue à titre informatif uniquement,
 * jamais utilisée pour filtrer le calcul (voir commentaire dans le corps
 * du script). Actif gouverne uniquement les listes déroulantes AppSheet
 * pour la saisie de nouvelles données, jamais le recalcul d'un historique
 * déjà engagé.
 *
 * Aucun identifiant de projet, client ou déploiement n'est codé en dur dans
 * ce script — noms de fonctions et de feuilles génériques, réutilisables
 * tels quels pour tout nouveau déploiement client (architecture cible :
 * un classeur Google Sheets dédié par client).
 *
 * À déclencher via un trigger horaire toutes les 15-30 min (voir
 * configurerDeclencheurHelperCalcul ci-dessous — à exécuter UNE SEULE FOIS
 * par déploiement/classeur).
 *
 * Coexiste avec les autres scripts d'alerte/snapshot du même classeur
 * (alerte matériau non prévu, alerte d'inactivité des localités — celle-ci
 * lit Top_Localites, qui dépend de Helper_Calcul, d'où la cadence 15-30 min
 * qui garantit la fraîcheur des données avant l'envoi hebdomadaire).
 */

// ================================================================
// DÉCLENCHEUR — Exécuter configurerDeclencheurHelperCalcul() UNE SEULE FOIS
// PAR DÉPLOIEMENT/CLASSEUR CLIENT
// ================================================================
function configurerDeclencheurHelperCalcul() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "Snapshot_HelperCalcul") {
      ScriptApp.deleteTrigger(t);
      Logger.log("🗑 Supprimé : ancien trigger Snapshot_HelperCalcul");
    }
  });

  // 30 min (et non 15) : ce classeur fait tourner plusieurs scripts qui
  // partagent le même quota d'exécution Apps Script quotidien (90 min/jour
  // compte grand public, 6h/jour Workspace). Le saut rapide dans
  // Snapshot_HelperCalcul_Run limite encore le coût réel.
  ScriptApp.newTrigger("Snapshot_HelperCalcul")
    .timeBased()
    .everyMinutes(30)
    .create();

  Logger.log("✅ Snapshot_HelperCalcul → toutes les 30 min");
  Logger.log("─────────────────────────────");
  ScriptApp.getProjectTriggers().forEach(t => {
    Logger.log("  ▶ " + t.getHandlerFunction() + " | " + t.getEventType());
  });
}

// ================================================================
// UTILITAIRE DE TEST — Exécuter manuellement pour forcer un recalcul complet
// (bypass l'heuristique "aucun changement détecté"). Utile après toute
// modification du code du script, puisque la signature HC_SIGNATURE ne
// reflète que le volume de données, pas le code exécuté.
// ================================================================
function forcerRecalculHelperCalcul() {
  PropertiesService.getScriptProperties().deleteProperty('HC_SIGNATURE');
  Logger.log('🔄 Signature HC_SIGNATURE réinitialisée — le prochain passage recalculera tout.');
  Snapshot_HelperCalcul_Run();
}

function Snapshot_HelperCalcul() {
  // Verrou : évite qu'une exécution démarre par-dessus une précédente encore
  // en cours (risque réel si Details_Intervention grossit vers 5000-15000
  // lignes et qu'une exécution dépasse l'intervalle du trigger).
  const lock = LockService.getScriptLock();
  const gotLock = lock.tryLock(5000); // attend 5s max, sinon abandonne ce passage
  if (!gotLock) {
    Logger.log("⏭ Snapshot_HelperCalcul : exécution précédente encore en cours, passage ignoré.");
    return;
  }

  try {
    Snapshot_HelperCalcul_Run();
  } finally {
    lock.releaseLock();
  }
}

// Saut rapide si rien n'a changé depuis le dernier passage : compare le
// nombre de lignes de Details_Intervention et Objectifs à la dernière
// exécution (stocké dans Script Properties). Heuristique : les corrections
// terrain s'ajoutent en nouvelles lignes (jamais d'édition en place), donc
// un nombre de lignes inchangé signifie qu'aucune saisie n'est arrivée.
// Coût d'un passage "rien à faire" : ~1 seconde au lieu de plusieurs
// dizaines pour un recalcul complet — protège le quota partagé du classeur.
function Snapshot_HelperCalcul_Run() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const shObjectifs = ss.getSheetByName('Objectifs');
  const shDetails   = ss.getSheetByName('Details_Intervention');
  const shPoids     = ss.getSheetByName('Parametres_Poids');
  const shLocalites = ss.getSheetByName('Localités');
  const shHelper    = ss.getSheetByName('Helper_Calcul');

  if (!shObjectifs || !shDetails || !shPoids || !shLocalites || !shHelper) {
    throw new Error('Snapshot_HelperCalcul: une des feuilles requises est introuvable.');
  }

  const props = PropertiesService.getScriptProperties();
  const signatureActuelle = shObjectifs.getLastRow() + '|' + shDetails.getLastRow();
  const signaturePrecedente = props.getProperty('HC_SIGNATURE');

  if (signatureActuelle === signaturePrecedente) {
    Logger.log('⏭ Snapshot_HelperCalcul : aucun changement détecté (Objectifs/Details_Intervention), passage ignoré.');
    return;
  }

  // --- Objectifs ---
  const objData = shObjectifs.getDataRange().getValues();
  const objHeaders = objData[0];
  const idxObj = {
    ID_Objectif:      objHeaders.indexOf('ID_Objectif'),
    ID_Localite:       objHeaders.indexOf('ID_Localite'),
    ID_Tache:          objHeaders.indexOf('ID_Tache'),
    Designation:       objHeaders.indexOf('Designation'),
    Quantite_Prevue:   objHeaders.indexOf('Quantite_Prevue')
  };
  for (const k in idxObj) {
    if (idxObj[k] === -1) throw new Error('Colonne Objectifs introuvable: ' + k);
  }
  const objectifs = objData.slice(1).filter(r => r[idxObj.ID_Objectif] !== '');

  // --- Localités -> map par ID_Localite (Localite, Nom_Geo_1) ---
  const locData = shLocalites.getDataRange().getValues();
  const locHeaders = locData[0];
  const idxLoc = {
    ID_Localite: locHeaders.indexOf('ID_Localite'),
    Nom_Geo_1:   locHeaders.indexOf('Nom_Geo_1'),
    Localite:    locHeaders.indexOf('Localite')
  };
  for (const k in idxLoc) {
    if (idxLoc[k] === -1) throw new Error('Colonne Localités introuvable: ' + k);
  }
  const localitesMap = {};
  locData.slice(1).forEach(r => {
    const id = r[idxLoc.ID_Localite];
    if (id !== '') {
      localitesMap[id] = { localite: r[idxLoc.Localite], nomGeo1: r[idxLoc.Nom_Geo_1] };
    }
  });

  // --- Parametres_Poids -> map par ID_Tache ---
  const poidsData = shPoids.getDataRange().getValues();
  const poidsHeaders = poidsData[0];
  const idxPoids = {
    ID_Tache:  poidsHeaders.indexOf('ID_Tache'),
    Poids:     poidsHeaders.indexOf('Poids'),
    Nom_Tache: poidsHeaders.indexOf('Nom_Tache')
  };
  for (const k in idxPoids) {
    if (idxPoids[k] === -1) throw new Error('Colonne Parametres_Poids introuvable: ' + k);
  }
  const idxPoidsCategorie = poidsHeaders.indexOf('Categorie');
  if (idxPoidsCategorie === -1) throw new Error('Colonne Parametres_Poids introuvable: Categorie');

  // Actif (pilote les listes déroulantes AppSheet). Lue ici à titre
  // informatif uniquement : on NE FILTRE PAS le calcul dessus. Raison :
  // Helper_Calcul recalcule l'avancement des Objectifs déjà engagés, pas une
  // liste de choix pour une nouvelle saisie. Si une tâche est désactivée en
  // cours de projet, les Objectifs existants qui la référencent doivent
  // continuer à être calculés normalement (Poids/Categorie/Nom_Tache
  // corrects), sinon leur avancement retomberait silencieusement à 0 (valeur
  // de repli de pInfo ci-dessous). Actif ne gouverne que la sélection de
  // nouvelles tâches côté formulaire AppSheet, jamais le recalcul historique.
  const idxPoidsActif = poidsHeaders.indexOf('Actif');
  // Colonne optionnelle : ne pas throw si absente, pour rester compatible
  // avant/après son ajout dans Parametres_Poids sur un déploiement donné.

  const poidsMap = {};
  poidsData.slice(1).forEach(r => {
    const id = r[idxPoids.ID_Tache];
    if (id !== '') {
      poidsMap[id] = {
        poids: Number(r[idxPoids.Poids]) || 0,
        nomTache: r[idxPoids.Nom_Tache],
        categorie: r[idxPoidsCategorie],
        actif: idxPoidsActif === -1 ? true : (r[idxPoidsActif] === true || String(r[idxPoidsActif]).trim().toUpperCase() === 'TRUE')
      };
    }
  });

  // --- Details_Intervention -> groupé par ID_Localite|Tache|Designation ---
  const detData = shDetails.getDataRange().getValues();
  const detHeaders = detData[0];
  const idxDet = {
    Mode_Saisie:        detHeaders.indexOf('Mode_Saisie'),
    Quantite:            detHeaders.indexOf('Quantite'),
    Quantite_Cumulee:    detHeaders.indexOf('Quantite_Cumulee'),
    Date:                detHeaders.indexOf('Date'),
    ID_Localite:         detHeaders.indexOf('ID_Localite'),
    Tache:               detHeaders.indexOf('Tache'),
    Designation:         detHeaders.indexOf('Designation')
  };
  for (const k in idxDet) {
    if (idxDet[k] === -1) throw new Error('Colonne Details_Intervention introuvable: ' + k);
  }

  const detGroups = {};
  detData.slice(1).forEach(r => {
    const loc = r[idxDet.ID_Localite];
    if (!loc) return;
    const key = loc + '|' + r[idxDet.Tache] + '|' + r[idxDet.Designation];
    if (!detGroups[key]) detGroups[key] = [];
    detGroups[key].push({
      mode:        String(r[idxDet.Mode_Saisie] || ''),
      qte:         Number(r[idxDet.Quantite]) || 0,
      qteCumulee:  Number(r[idxDet.Quantite_Cumulee]) || 0,
      date:        r[idxDet.Date] ? new Date(r[idxDet.Date]).getTime() : 0
    });
  });

  // Reproduit la logique: si aucune ligne "Cumul", somme des "Saisie".
  // Sinon: valeur cumulée à la date la plus récente + saisies postérieures à cette date.
  function calcQteRealisee(key) {
    const rows = detGroups[key];
    if (!rows) return 0;

    const cumulRows = rows.filter(x => x.mode.indexOf('Cumul') !== -1);
    if (cumulRows.length === 0) {
      return rows
        .filter(x => x.mode.indexOf('Saisie') !== -1)
        .reduce((s, x) => s + x.qte, 0);
    }

    const maxCumul = cumulRows.reduce((a, b) => (b.date > a.date ? b : a));
    const saisiesApres = rows
      .filter(x => x.mode.indexOf('Saisie') !== -1 && x.date > maxCumul.date)
      .reduce((s, x) => s + x.qte, 0);

    return maxCumul.qteCumulee + saisiesApres;
  }

  // --- Qte_Prevue_Total par groupe ID_Localite|ID_Tache ---
  const prevueTotalMap = {};
  objectifs.forEach(r => {
    const key = r[idxObj.ID_Localite] + '|' + r[idxObj.ID_Tache];
    prevueTotalMap[key] = (prevueTotalMap[key] || 0) + (Number(r[idxObj.Quantite_Prevue]) || 0);
  });

  // --- Construction des lignes Helper_Calcul ---
  const tachesInactivesUtilisees = new Set();

  const output = objectifs.map((r, i) => {
    const idLocalite = r[idxObj.ID_Localite];
    const idTache     = r[idxObj.ID_Tache];
    const designation = r[idxObj.Designation];
    const qtePrevue    = Number(r[idxObj.Quantite_Prevue]) || 0;

    const detKey     = idLocalite + '|' + idTache + '|' + designation;
    const qteRealisee = calcQteRealisee(detKey);

    const pInfo          = poidsMap[idTache] || { poids: 0, nomTache: '', categorie: '', actif: true };
    const qtePrevueTotal = prevueTotalMap[idLocalite + '|' + idTache] || 0;
    const locInfo         = localitesMap[idLocalite] || { localite: '', nomGeo1: '' };

    // Signalement (pas de blocage) : un Objectif actif référence une tâche
    // désactivée dans Parametres_Poids. Le calcul continue normalement avec
    // le Poids/Categorie d'origine (voir commentaire sur poidsMap ci-dessus).
    if (pInfo.actif === false) {
      tachesInactivesUtilisees.add(idTache + ' (' + pInfo.nomTache + ')');
    }

    const tauxRealisation = qtePrevue > 0 ? Math.min(1, qteRealisee / qtePrevue) : 0;
    const avancementPondere = qtePrevueTotal > 0
      ? tauxRealisation * pInfo.poids * (qtePrevue / qtePrevueTotal)
      : 0;

    return [
      'HC-' + (i + 1),           // ID_Helper
      r[idxObj.ID_Objectif],     // ID_Objectif
      idLocalite,                // ID_Localite
      idTache,                   // ID_Tache
      designation,                // Designation
      qtePrevue,                  // Qte_Prevue
      pInfo.nomTache,             // Taches
      pInfo.poids,                 // Poids
      qteRealisee,                 // Qte_Realisee
      tauxRealisation,             // Taux_Realisation
      qtePrevueTotal,              // Qte_Prevue_Total
      avancementPondere,           // Avancement_Pondere
      locInfo.localite,            // Localite (réintégrée pour Slice_Depassements)
      locInfo.nomGeo1,             // Nom_Geo_1 (réintégrée par cohérence, non consommée par les Recap_*)
      pInfo.categorie               // Categorie (dynamique, source unique = Parametres_Poids ;
                                     // remplace les listes de noms de tâches codées en dur dans
                                     // les formules Top_Localites A_Travaux_HTA/BT, Avancement_HTA/BT_%)
    ];
  });

  // --- Écriture: on efface l'ancienne plage puis on écrit en une seule passe ---
  const numCols = 15; // A..O (Categorie ajoutée en O — voir commentaire ci-dessus)
  const lastRow = shHelper.getLastRow();
  if (lastRow > 1) {
    shHelper.getRange(2, 1, lastRow - 1, Math.max(shHelper.getLastColumn(), numCols)).clearContent();
  }
  if (output.length > 0) {
    shHelper.getRange(2, 1, output.length, numCols).setValues(output);
  }

  props.setProperty('HC_SIGNATURE', signatureActuelle);

  if (tachesInactivesUtilisees.size > 0) {
    Logger.log('⚠️ ' + tachesInactivesUtilisees.size + ' tâche(s) désactivée(s) dans Parametres_Poids '
      + 'mais encore référencée(s) par des Objectifs actifs (calcul non affecté, à titre informatif) : '
      + [...tachesInactivesUtilisees].join(', '));
  }

  Logger.log('Snapshot_HelperCalcul: ' + output.length + ' lignes écrites.');
}