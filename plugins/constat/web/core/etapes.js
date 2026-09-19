import { ETAPES } from './etapes-consignes.js';
export { ETAPES, construirePrompt } from './etapes-consignes.js';
const REGISTRES = ['affirme', 'infere', 'hypothese', 'speculation'];
/* ---------------------------------------------------------- validation */

const POINTS_CHECKLIST = ['preuves_contraires', 'ancrage', 'effet_miroir',
  'surmediatisation', 'equipe_rouge', 'registres_distingues', 'lacunes_precisees'];



const ROLES_ACH_OBLIGATOIRES = ['dominante', 'dissidente', 'fractale'];
const ROLES_ACH = [...ROLES_ACH_OBLIGATOIRES, 'strategique', 'systemique'];
const ROLES_SCENARIO_OBLIGATOIRES = ['optimiste', 'probable', 'critique'];
const ROLES_SCENARIO = [...ROLES_SCENARIO_OBLIGATOIRES, 'fractal'];
const CONFIANCES = ['faible', 'moderee', 'elevee'];


const vide = (x) => !String(x ?? '').trim();

/**
 * Classement ACH, calculé ici et non demandé au modèle.
 *
 * L'hypothèse retenue n'est pas celle qui rassemble le plus de preuves
 * compatibles, mais celle qui rassemble le moins de preuves incompatibles.
 * Cette inversion force la recherche de réfutation. La laisser au modèle
 * reviendrait à lui laisser choisir sa propre conclusion.
 */
export function classerHypotheses(hypotheses, matrice) {
  const scores = hypotheses.map((h) => {
    let C = 0; let I = 0; let N = 0;
    for (const ligne of Object.values(matrice)) {
      const v = ligne?.[h.id];
      if (v === 'C') C++; else if (v === 'I') I++; else if (v === 'N') N++;
    }
    return { id: h.id, role: h.role, compatibles: C, incompatibles: I, neutres: N };
  });
  // Tri par incompatibles croissantes, puis compatibles décroissantes.
  return [...scores].sort((a, b) => a.incompatibles - b.incompatibles
    || b.compatibles - a.compatibles
    || a.id.localeCompare(b.id));
}

export function validerEtape5(brut, idsSources = []) {
  const ecartees = [];
  const connus = new Set(idsSources);

  const hypotheses = [];
  for (const h of [].concat(brut?.hypotheses ?? [])) {
    if (vide(h?.id) || vide(h?.enonce)) { ecartees.push({ objet: h, raison: 'hypothèse sans id ou sans énoncé' }); continue; }
    if (!ROLES_ACH.includes(h.role)) { ecartees.push({ objet: h, raison: `rôle inconnu : ${h.role}` }); continue; }
    if (vide(h.confirmerait) || vide(h.demolirait)) {
      ecartees.push({ objet: h, raison: 'hypothèse non testable : indicateur de confirmation ou de réfutation manquant' });
      continue;
    }
    hypotheses.push({ id: String(h.id), role: h.role, enonce: String(h.enonce),
      confirmerait: String(h.confirmerait), demolirait: String(h.demolirait) });
  }

  const manquants = ROLES_ACH_OBLIGATOIRES.filter((r) => !hypotheses.some((h) => h.role === r));
  if (manquants.length) ecartees.push({ objet: null, raison: `rôles obligatoires absents : ${manquants.join(', ')}` });
  if (hypotheses.length < 3) ecartees.push({ objet: null, raison: `${hypotheses.length} hypothèse(s) retenue(s), 3 minimum` });

  const preuves = [];
  const inventees = new Set();
  for (const p of [].concat(brut?.preuves ?? [])) {
    if (vide(p?.id) || vide(p?.enonce)) { ecartees.push({ objet: p, raison: 'preuve sans id ou sans énoncé' }); continue; }
    for (const s of p.sources || []) if (connus.size && !connus.has(s)) inventees.add(s);
    preuves.push({ id: String(p.id), enonce: String(p.enonce), sources: (p.sources || []).map(String) });
  }

  // Une case manquante n'est pas comblée par « neutre » : elle est signalée.
  // Compléter à la place du modèle fausserait le classement en sa faveur.
  const matrice = {};
  const cellulesManquantes = [];
  for (const p of preuves) {
    matrice[p.id] = {};
    for (const h of hypotheses) {
      const v = brut?.matrice?.[p.id]?.[h.id];
      if (v === 'C' || v === 'I' || v === 'N') matrice[p.id][h.id] = v;
      else cellulesManquantes.push(`${p.id}×${h.id}`);
    }
  }
  if (cellulesManquantes.length) {
    ecartees.push({ objet: null, raison: `${cellulesManquantes.length} case(s) de matrice manquante(s) ou invalide(s)` });
  }

  return {
    sortie: { hypotheses, preuves, matrice, classement: classerHypotheses(hypotheses, matrice) },
    ecartees,
    inventees: [...inventees].sort(),
    complet: !ecartees.length,
    cellulesManquantes,
  };
}

const CERTITUDE = /(^|[^\d])(100|0)\s*%|certitude absolue|[àa]\s+coup\s+s[ûu]r|in[ée]vitable|aucun\s+doute/i;

export function validerEtape7(brut, idsHypotheses = []) {
  const ecartees = [];
  const connues = new Set(idsHypotheses);
  const scenarios = [];

  for (const s of [].concat(brut?.scenarios ?? [])) {
    if (vide(s?.id) || vide(s?.titre)) { ecartees.push({ objet: s, raison: 'scénario sans id ou sans titre' }); continue; }
    if (!ROLES_SCENARIO.includes(s.role)) { ecartees.push({ objet: s, raison: `rôle inconnu : ${s.role}` }); continue; }
    if (!(s.indicateursBascule || []).filter((x) => !vide(x)).length) {
      // Sans indicateur observable, un scénario n'est pas surveillable : c'est
      // une histoire. Le §7 du skill en fait une exigence, pas une option.
      ecartees.push({ objet: s, raison: 'scénario sans indicateur de bascule observable' });
      continue;
    }
    if (!CONFIANCES.includes(s.confiance)) { ecartees.push({ objet: s, raison: `confiance hors échelle : ${s.confiance}` }); continue; }
    const texte = [s.titre, s.impact, ...(s.conditions || []), ...(s.drivers || [])].join(' ');
    if (CERTITUDE.test(texte)) { ecartees.push({ objet: s, raison: 'certitude ou probabilité de 0 ou 1' }); continue; }

    const orphelines = (s.hypotheses || []).filter((h) => connues.size && !connues.has(h));
    if (orphelines.length) { ecartees.push({ objet: s, raison: `hypothèses inconnues : ${orphelines.join(', ')}` }); continue; }

    scenarios.push({
      id: String(s.id), role: s.role, titre: String(s.titre),
      drivers: (s.drivers || []).map(String),
      conditions: (s.conditions || []).map(String),
      indicateursBascule: (s.indicateursBascule || []).map(String),
      impact: String(s.impact ?? ''), confiance: s.confiance,
      hypotheses: (s.hypotheses || []).map(String),
    });
  }

  const manquants = ROLES_SCENARIO_OBLIGATOIRES.filter((r) => !scenarios.some((s) => s.role === r));
  if (manquants.length) ecartees.push({ objet: null, raison: `rôles obligatoires absents : ${manquants.join(', ')}` });

  return { sortie: { scenarios }, ecartees, complet: !ecartees.length };
}

export function validerEtape10(brut) {
  const ecartees = [];
  const parPoint = new Map();

  for (const c of [].concat(brut?.checklist ?? [])) {
    if (!POINTS_CHECKLIST.includes(c?.point)) { ecartees.push({ objet: c, raison: `point inconnu : ${c?.point}` }); continue; }
    if (!['oui', 'non', 'partiel'].includes(c?.reponse)) { ecartees.push({ objet: c, raison: `réponse hors échelle : ${c?.reponse}` }); continue; }
    if (vide(c?.justification)) { ecartees.push({ objet: c, raison: `point « ${c.point} » sans justification` }); continue; }
    parPoint.set(c.point, {
      point: c.point, reponse: c.reponse,
      justification: String(c.justification), vise: (c.vise || []).map(String),
    });
  }

  const absents = POINTS_CHECKLIST.filter((p) => !parPoint.has(p));
  if (absents.length) ecartees.push({ objet: null, raison: `points de check-list absents : ${absents.join(', ')}` });

  // « Aucune démolition » n'est pas une réponse acceptable : c'est le signe que
  // l'équipe rouge n'a pas été jouée.
  if (vide(brut?.demolition)) ecartees.push({ objet: null, raison: 'aucune démolition proposée — l’équipe rouge n’a pas été jouée' });

  const lacunes = [].concat(brut?.lacunes ?? []).map(String).filter((x) => !vide(x));
  if (!lacunes.length) ecartees.push({ objet: null, raison: 'aucune lacune d’information déclarée' });

  return {
    sortie: {
      checklist: POINTS_CHECKLIST.map((p) => parPoint.get(p)).filter(Boolean),
      lacunes,
      demolition: String(brut?.demolition ?? ''),
    },
    ecartees,
    complet: !ecartees.length,
  };
}

/* ------------------------------------------------- étape 4 — analyse triple */

const COUCHES = ['factuelle', 'signaux', 'symbolique'];
const STATUTS = ['convergent', 'divergent', 'partiel'];

export function validerEtape4(brut, idsSources = []) {
  const ecartees = [];
  const connus = new Set(idsSources);
  const inventees = new Set();
  const sortie = { factuelle: [], signaux: [], symbolique: [], convergence: null };

  for (const item of [].concat(brut?.factuelle ?? [])) {
    if (vide(item?.texte)) { ecartees.push({ objet: item, raison: 'lecture factuelle vide' }); continue; }
    for (const s of item.sources || []) if (connus.size && !connus.has(s)) inventees.add(s);
    sortie.factuelle.push({ texte: String(item.texte), sources: (item.sources || []).map(String) });
  }

  for (const item of [].concat(brut?.signaux ?? [])) {
    if (vide(item?.texte)) { ecartees.push({ objet: item, raison: 'signal faible vide' }); continue; }
    sortie.signaux.push({ texte: String(item.texte), pourquoiNeglige: String(item.pourquoiNeglige ?? '') });
  }

  for (const item of [].concat(brut?.symbolique ?? [])) {
    if (vide(item?.texte)) { ecartees.push({ objet: item, raison: 'lecture symbolique vide' }); continue; }
    // Le piège nommé par le skill : un archétype plaqué sans fait est de la
    // spéculation déguisée. Sans appui factuel, l'énoncé ne passe pas.
    if (vide(item?.appui)) {
      ecartees.push({ objet: item, raison: 'lecture symbolique sans appui factuel — archétype plaqué' });
      continue;
    }
    sortie.symbolique.push({ texte: String(item.texte), appui: String(item.appui) });
  }

  for (const c of COUCHES) {
    if (!sortie[c].length) ecartees.push({ objet: null, raison: `couche « ${c} » vide` });
  }

  const cv = brut?.convergence;
  if (!STATUTS.includes(cv?.statut)) {
    ecartees.push({ objet: cv, raison: `statut de convergence inconnu : ${cv?.statut}` });
  } else if (cv.statut !== 'convergent' && vide(cv?.revele)) {
    // Une divergence non expliquée est une divergence lissée.
    ecartees.push({ objet: cv, raison: 'divergence déclarée sans dire ce qu’elle révèle' });
  } else {
    sortie.convergence = { statut: cv.statut, revele: String(cv.revele ?? '') };
  }

  return { sortie, ecartees, inventees: [...inventees].sort(), complet: !ecartees.length };
}

/* --------------------------------------------------- étape 8 — le risque */

const PROBABILITES = ['faible', 'moderee', 'elevee'];
const IMPACTS = ['mineur', 'important', 'critique'];
const DIMENSIONS = ['humaine', 'economique', 'politique', 'mediatique', 'operationnelle', 'symbolique'];

/**
 * Matrice 3×3 du skill. Le niveau de risque est calculé ici, jamais demandé au
 * modèle — même principe que le classement ACH. Un modèle qui annonce
 * « risque critique » a produit un jugement ; un modèle qui donne une
 * probabilité et un impact a produit deux observations, et le croisement est
 * une règle publique que l'on peut contester.
 */
const MATRICE_RISQUE = {
  elevee: { mineur: 'modere', important: 'eleve', critique: 'critique' },
  moderee: { mineur: 'faible', important: 'modere', critique: 'eleve' },
  faible: { mineur: 'tres-faible', important: 'faible', critique: 'modere' },
};

export function croiser(probabilite, impact) {
  return MATRICE_RISQUE[probabilite]?.[impact] ?? null;
}

export function validerEtape8(brut, idsScenarios = []) {
  const ecartees = [];
  const connus = new Set(idsScenarios);
  const evaluations = [];

  for (const e of [].concat(brut?.evaluations ?? [])) {
    if (connus.size && !connus.has(e?.scenario)) {
      ecartees.push({ objet: e, raison: `scénario inconnu : ${e?.scenario}` }); continue;
    }
    if (!PROBABILITES.includes(e?.probabilite)) {
      ecartees.push({ objet: e, raison: `probabilité hors échelle : ${e?.probabilite}` }); continue;
    }
    if (!IMPACTS.includes(e?.impact)) {
      ecartees.push({ objet: e, raison: `impact hors échelle : ${e?.impact}` }); continue;
    }
    // « Sans conditionnement, une évaluation de risque devient une prophétie —
    // donc une faute professionnelle. » La règle est appliquée, pas seulement
    // demandée.
    const conditions = (e.conditions || []).map(String).filter((c) => !vide(c));
    if (!conditions.length) {
      ecartees.push({ objet: e, raison: 'évaluation sans condition — une prophétie, pas une évaluation' });
      continue;
    }
    if (!CONFIANCES.includes(e?.confiance)) {
      ecartees.push({ objet: e, raison: `confiance hors échelle : ${e?.confiance}` }); continue;
    }
    evaluations.push({
      scenario: String(e.scenario), probabilite: e.probabilite, impact: e.impact,
      dimensions: (e.dimensions || []).map(String).filter((d) => DIMENSIONS.includes(d)),
      conditions, confiance: e.confiance, justification: String(e.justification ?? ''),
      niveau: croiser(e.probabilite, e.impact),
    });
  }

  // Deux travers symétriques, tous deux détectables par comptage.
  const niveaux = evaluations.map((e) => e.niveau);
  if (evaluations.length >= 3 && new Set(niveaux).size === 1) {
    ecartees.push({
      objet: null,
      raison: niveaux[0] === 'critique' || niveaux[0] === 'eleve'
        ? 'toutes les évaluations au même niveau élevé — inflation du risque, plus rien n’alerte'
        : 'toutes les évaluations au même niveau bas — nivellement, l’alerte est supprimée',
    });
  }

  return { sortie: { evaluations }, ecartees, complet: !ecartees.length };
}

/* ------------------------------------------ étape 9 — les recommandations */

const PRIORITES = ['haute', 'moyenne', 'basse'];
const TERMES = ['court', 'moyen', 'long'];

/** Anti-patterns nommés par le skill, plus les formules d'action contre un
 *  tiers. Chaque expression est testée individuellement. */
const RECOMMANDATIONS_VIDES = [
  /suivre\s+attentivement/i,
  /rester\s+vigilant/i,
  /renforcer\s+la\s+coop[ée]ration/i,
  /avant\s+qu[’']il\s+ne\s+soit\s+trop\s+tard/i,
  /continuer\s+[àa]\s+observer/i,
  /prendre\s+les\s+mesures\s+n[ée]cessaires/i,
];

const ACTION_CONTRE_TIERS = [
  /\bfrapper\b/i, /\bsanctionner\b/i, /\b[ée]liminer\b/i, /\bneutraliser\b/i,
  /\brenverser\b/i, /\bd[ée]stabiliser\b/i, /\bdiscr[ée]diter\b/i,
];

export function validerEtape9(brut, idsScenarios = []) {
  const ecartees = [];
  const connus = new Set(idsScenarios);
  const recommandations = [];

  for (const r of [].concat(brut?.recommandations ?? [])) {
    if (vide(r?.id) || vide(r?.action)) { ecartees.push({ objet: r, raison: 'recommandation sans id ou sans action' }); continue; }
    if (!PRIORITES.includes(r?.priorite)) { ecartees.push({ objet: r, raison: `priorité hors échelle : ${r?.priorite}` }); continue; }
    if (!TERMES.includes(r?.terme)) { ecartees.push({ objet: r, raison: `terme hors échelle : ${r?.terme}` }); continue; }
    if (vide(r?.ressources)) { ecartees.push({ objet: r, raison: 'recommandation non ressourcée : qui fait, avec quoi ?' }); continue; }
    if (vide(r?.risqueInaction)) { ecartees.push({ objet: r, raison: 'risque d’inaction non dit' }); continue; }

    const vide_ = RECOMMANDATIONS_VIDES.find((re) => re.test(r.action));
    if (vide_) { ecartees.push({ objet: r, raison: `formule vide : ${vide_.source}` }); continue; }

    const contre = ACTION_CONTRE_TIERS.find((re) => re.test(r.action));
    if (contre) {
      ecartees.push({ objet: r, raison: 'recommandation d’action contre un tiers — hors du périmètre de l’outil' });
      continue;
    }

    const orphelins = (r.scenarios || []).filter((s) => connus.size && !connus.has(s));
    if (orphelins.length) { ecartees.push({ objet: r, raison: `scénarios inconnus : ${orphelins.join(', ')}` }); continue; }

    recommandations.push({
      id: String(r.id), priorite: r.priorite, terme: r.terme,
      action: String(r.action), ressources: String(r.ressources),
      risqueInaction: String(r.risqueInaction), reversible: !!r.reversible,
      scenarios: (r.scenarios || []).map(String),
    });
  }

  // « 2 à 4 maximum, classées. » Au-delà, ce n'est plus une priorisation.
  if (recommandations.length > 4) {
    ecartees.push({ objet: null, raison: `${recommandations.length} recommandations — 4 maximum, sinon rien n’est prioritaire` });
  }
  if (recommandations.length < 2) {
    ecartees.push({ objet: null, raison: `${recommandations.length} recommandation(s) retenue(s), 2 minimum` });
  }

  const rang = (r) => PRIORITES.indexOf(r.priorite) * 10 + TERMES.indexOf(r.terme);
  return {
    sortie: { recommandations: [...recommandations].sort((a, b) => rang(a) - rang(b)) },
    ecartees, complet: !ecartees.length,
  };
}

/* ---------------------------------------------- étape 11 — la rétroaction */

const CLOTURES_INTERDITES = [
  /l[’']avenir\s+nous\s+le\s+dira/i,
  /tout\s+est\s+possible/i,
  /seul\s+le\s+temps\s+le\s+dira/i,
  /wait\s+and\s+see/i,
];

export function validerEtape11(brut) {
  const ecartees = [];
  const liste = (x, nom) => {
    const out = [].concat(x ?? []).map(String).filter((v) => !vide(v));
    if (!out.length) ecartees.push({ objet: null, raison: `${nom} : aucune entrée` });
    for (const v of out) {
      const mauvais = CLOTURES_INTERDITES.find((re) => re.test(v));
      if (mauvais) ecartees.push({ objet: v, raison: `clôture abdicative : ${mauvais.source}` });
    }
    return out.filter((v) => !CLOTURES_INTERDITES.some((re) => re.test(v)));
  };

  const invalidants = liste(brut?.invalidants, 'invalidants');
  const lacunes = liste(brut?.lacunes, 'lacunes');
  const signaux = liste(brut?.signaux, 'signaux');

  const pp = brut?.prochainPoint;
  if (vide(pp?.quand) || vide(pp?.declencheur)) {
    ecartees.push({ objet: pp, raison: 'prochain point de contrôle sans échéance ou sans déclencheur' });
  }

  return {
    sortie: {
      invalidants, lacunes, signaux,
      prochainPoint: { quand: String(pp?.quand ?? ''), declencheur: String(pp?.declencheur ?? '') },
    },
    ecartees, complet: !ecartees.length,
  };
}

export function valider(numero, brut, contexte = {}) {
  if (numero === 4) return validerEtape4(brut, contexte.idsSources);
  if (numero === 5) return validerEtape5(brut, contexte.idsSources);
  if (numero === 7) return validerEtape7(brut, contexte.idsHypotheses);
  if (numero === 8) return validerEtape8(brut, contexte.idsScenarios);
  if (numero === 9) return validerEtape9(brut, contexte.idsScenarios);
  if (numero === 10) return validerEtape10(brut);
  if (numero === 11) return validerEtape11(brut);
  throw new Error(`étape inconnue : ${numero}`);
}

export {
  REGISTRES, POINTS_CHECKLIST, ROLES_ACH, ROLES_SCENARIO, CONFIANCES,
  COUCHES, STATUTS, PROBABILITES, IMPACTS, DIMENSIONS, PRIORITES, TERMES,
  MATRICE_RISQUE,
};
