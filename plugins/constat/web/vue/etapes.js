import { el, listeCourte, ligne } from './rendu.js';
const NOTE_ACH = 'Classement calculé à partir de la matrice, sur le nombre de preuves '
  + 'INCOMPATIBLES. L’hypothèse en tête n’est pas la mieux étayée : c’est celle que le '
  + 'corpus réfute le moins.';

function rendreACH(sortie, surPredire) {
  const d = el('div');
  d.append(el('p', { class: 'provenance', text: NOTE_ACH }));

  const t = el('table', { class: 'matrice' });
  const entete = el('tr', {}, [el('th', { text: 'Preuve' })]);
  for (const h of sortie.hypotheses) entete.append(el('th', { text: h.id }));
  t.append(entete);
  for (const p of sortie.preuves) {
    const tr = el('tr', {}, [el('td', { text: `${p.id} — ${p.enonce}`, title: (p.sources || []).join(', ') })]);
    for (const h of sortie.hypotheses) {
      const v = sortie.matrice[p.id]?.[h.id];
      tr.append(el('td', { class: `case ${v || 'manquante'}`, text: v || '·' }));
    }
    t.append(tr);
  }
  d.append(t);

  d.append(listeCourte(sortie.classement.map((c, i) => `${i + 1}. ${c.id} (${c.role}) — `
    + `${c.incompatibles} incompatible(s), ${c.compatibles} compatible(s)`), 7));
  for (const h of sortie.hypotheses) {
    const bloc = el('div', { class: 'bloc-lecture' });
    bloc.append(el('p', { text: `${h.id} ${h.enonce} — confirmerait : ${h.confirmerait} — démolirait : ${h.demolirait}` }));
    if (surPredire) {
      const b = el('button', { type:'button', text:'Verser comme prédiction dans PRISME' });
      b.addEventListener('click', () => surPredire(h.id));
      bloc.append(b);
    }
    d.append(bloc);
  }
  return d;
}

function rendreScenarios(sortie) {
  const d = el('div');
  for (const s of sortie.scenarios) {
    d.append(el('div', { class: 'bloc-lecture' }, [
      el('div', { class: 'titre', text: `${s.role} — ${s.titre} (confiance ${s.confiance})` }),
      el('p', { class: 'enonce', text: s.impact }),
      el('div', { class: 'provenance', text: 'Indicateurs de bascule' }),
      listeCourte(s.indicateursBascule, 6),
    ]));
  }
  return d;
}

function rendreBiais(sortie) {
  const d = el('div');
  d.append(listeCourte(sortie.checklist.map((c) => `${c.point} : ${c.reponse} — ${c.justification}`), 7));
  d.append(el('div', { class: 'provenance', text: 'Ce qu’une équipe rouge opposerait' }));
  d.append(el('p', { class: 'enonce', text: sortie.demolition }));
  d.append(el('div', { class: 'provenance', text: 'Lacunes déclarées' }));
  d.append(listeCourte(sortie.lacunes, 8));
  return d;
}

function rendreTriple(sortie) {
  const d = el('div');
  for (const [cle, titre] of [['factuelle', 'Lecture factuelle'],
    ['signaux', 'Signaux faibles'], ['symbolique', 'Lecture symbolique']]) {
    d.append(el('div', { class: 'titre', text: titre }));
    d.append(listeCourte((sortie[cle] || []).map((i) => i.texte
      + (i.appui ? ` — appui : ${i.appui}` : '')
      + (i.pourquoiNeglige ? ` — négligé car : ${i.pourquoiNeglige}` : '')), 8));
  }
  if (sortie.convergence) {
    d.append(el('p', {
      class: 'provenance',
      text: sortie.convergence.statut === 'convergent'
        ? 'Les trois lectures convergent.'
        : `Lectures ${sortie.convergence.statut}es — ce que la dissonance révèle : ${sortie.convergence.revele}`,
    }));
  }
  return d;
}

const NIVEAUX = { 'tres-faible': 'très faible', faible: 'faible', modere: 'modéré',
  eleve: 'élevé', critique: 'critique' };

function rendreRisque(sortie) {
  const d = el('div');
  d.append(el('p', {
    class: 'provenance',
    text: 'Niveau croisé par l’outil à partir de la probabilité et de l’impact. '
      + 'Le modèle donne les deux ; il ne conclut pas.',
  }));
  for (const e of sortie.evaluations) {
    d.append(el('div', { class: 'bloc-lecture' }, [
      el('div', { class: 'titre', text: `${e.scenario} — risque ${NIVEAUX[e.niveau] || e.niveau} `
        + `(probabilité ${e.probabilite} × impact ${e.impact})` }),
      el('p', { class: 'enonce', text: e.justification }),
      el('div', { class: 'provenance', text: `Ne tient que si : ${e.conditions.join(' ; ')}` }),
      el('div', { class: 'provenance', text: `Dimensions : ${e.dimensions.join(', ') || '—'} · `
        + `confiance ${e.confiance}` }),
    ]));
  }
  return d;
}

function rendreRecommandations(sortie) {
  const d = el('div');
  for (const r of sortie.recommandations) {
    d.append(el('div', { class: 'bloc-lecture' }, [
      el('div', { class: 'titre', text: `${r.id} — priorité ${r.priorite}, terme ${r.terme}`
        + (r.reversible ? ', réversible' : ', NON réversible') }),
      el('p', { class: 'enonce', text: r.action }),
      el('div', { class: 'provenance', text: `Ressources : ${r.ressources}` }),
      el('div', { class: 'provenance', text: `Risque d’inaction : ${r.risqueInaction}` }),
    ]));
  }
  return d;
}

function rendreRetroaction(sortie) {
  const d = el('div');
  for (const [cle, titre] of [['invalidants', 'Ce qui invaliderait l’analyse'],
    ['lacunes', 'Lacunes d’information'], ['signaux', 'Signaux à surveiller']]) {
    d.append(el('div', { class: 'titre', text: titre }));
    d.append(listeCourte(sortie[cle] || [], 8));
  }
  d.append(el('p', {
    class: 'provenance',
    text: `Prochain point de contrôle : ${sortie.prochainPoint.quand} — `
      + `déclencheur : ${sortie.prochainPoint.declencheur}`,
  }));
  return d;
}

export function rendreEtapes(etapes, surValider, surPredire) {
  const sec = el('section', { class: 'lecture etapes' });
  sec.append(el('h3', { text: 'Pipeline OSINT' }));

  for (const e of etapes) {
    const bloc = el('div', { class: `bras etape${e.validee ? ' validee' : ''}` });
    bloc.append(el('h3', { text: `Étape ${e.numero} — ${e.nom}` }));
    bloc.append(el('p', {
      class: 'provenance',
      text: `${e.fournisseur} · ${e.modele} · référence ${e.reference} · `
        + `${e.ts.slice(0, 16).replace('T', ' ')}`
        + (e.validee ? ` · VALIDÉE le ${String(e.valideeLe).slice(0, 10)}` : ' · non validée'),
    }));

    if (e.numero === 4) bloc.append(rendreTriple(e.sortie));
    else if (e.numero === 5) bloc.append(rendreACH(e.sortie, e.validee && e.complet && surPredire ? (id) => surPredire(e, id) : null));
    else if (e.numero === 7) bloc.append(rendreScenarios(e.sortie));
    else if (e.numero === 8) bloc.append(rendreRisque(e.sortie));
    else if (e.numero === 9) bloc.append(rendreRecommandations(e.sortie));
    else if (e.numero === 10) bloc.append(rendreBiais(e.sortie));
    else if (e.numero === 11) bloc.append(rendreRetroaction(e.sortie));

    if (e.ecartees?.length || e.inventees?.length) {
      const x = el('div', { class: 'ecartees' });
      if (e.ecartees?.length) {
        x.append(el('div', { text: `${e.ecartees.length} rejet(s) — rien n’a été réparé :` }));
        x.append(listeCourte(e.ecartees.map((r) => r.raison), 8));
      }
      if (e.inventees?.length) {
        x.append(el('div', { text: `Sources citées absentes du corpus : ${e.inventees.join(', ')}` }));
      }
      bloc.append(x);
    }

    if (!e.validee) {
      const b = el('button', { type: 'button', text: `Valider l’étape ${e.numero}` });
      b.addEventListener('click', () => surValider(e.ts));
      bloc.append(el('p', {
        class: 'provenance',
        text: 'Relisez avant de valider : l’étape suivante recevra ceci tel quel.',
      }));
      bloc.append(b);
    }
    sec.append(bloc);
  }
  return sec;
}

/* ------------------------------------------- verdict du versement par moteur
 *
 * Affiché après chaque recherche, et volontairement au-dessus du relevé : la
 * question n'est pas « a-t-on obtenu des articles » mais « les cinq comptages
 * disent-ils encore quelque chose ». Un corpus complet dont les détecteurs
 * sont morts est pire qu'un corpus vide : il a l'air d'un résultat.
 */

const SEUILS = {
  'acteur-non-cite': 'la moitié des articles doivent porter des guillemets',
  'article-sans-source': 'la moitié doivent porter au moins un lien de corps',
  'trou-dossier': '70 % doivent être datés par leur propre balisage',
  'terme-effondre': '70 % doivent être datés par leur propre balisage',
  'grappe-origine-unique': 'la moitié doivent avoir un corps exploitable',
};

export function rendreVerdict(v) {
  const sec = el('section', { class: 'lecture verdict' });
  sec.append(el('h3', { text: `Versement par moteur — « ${v.query} »` }));
  sec.append(el('p', {
    class: 'provenance',
    text: `${v.sources} article(s) versés`
      + (v.cout !== null && v.cout !== undefined ? ` · ${v.cout} $` : '')
      + (v.echecs?.length ? ` · ${v.echecs.length} échec(s) de crawl` : ''),
  }));

  const paire = (libelle, n) => ligne(libelle, `${n} / ${v.sources}`, null, { creuse: true });
  sec.append(ligne('Pages lues à la source', `${v.pagesRecuperees ?? 0} / ${v.sources}`,
    el('div', { text: 'Le moteur découvre les URL, Constat lit les pages. Ce que renvoie le '
      + 'moteur est du contenu extrait : sans <head>, donc sans JSON-LD ni balise <time>, et '
      + 'sans les liens de corps qu’il prend pour de la navigation. Un repli sur ce contenu '
      + 'tue les détecteurs 2, 3 et 4 d’un coup.' })));
  sec.append(ligne('  repli sur le contenu du moteur', `${v.contenuMoteur ?? 0} / ${v.sources}`,
    null, { creuse: true }));
  sec.append(ligne('Avec balisage HTML', `${v.balisageRecu} / ${v.sources}`,
    el('div', { text: 'Sans balisage : ni JSON-LD, ni guillemets situables, ni liens de corps. '
      + 'Les détecteurs 1 et 4 meurent, et le corpus paraît complet alors qu’il est amputé.' })));
  sec.append(paire('Corps extrait', v.corpsExtrait));
  sec.append(paire('Avec un lien de corps', v.avecLiens));
  sec.append(paire('  dont un document source', v.avecLienSource));
  sec.append(paire('Avec citations', v.avecCitations));
  sec.append(ligne('Datés par la PAGE', `${v.datePage} / ${v.sources}`, null, { creuse: true }));
  sec.append(ligne('Datés par le MOTEUR seulement', `${v.dateFournisseurSeule} / ${v.sources}`,
    v.dateFournisseurSeule
      ? el('div', { text: 'Pour ces articles la chronologie ne repose plus sur ce que la page '
        + 'déclare mais sur ce qu’un tiers infère. Les détecteurs 2 et 3 mesurent alors le '
        + 'moteur, pas la presse.' })
      : null, { creuse: true }));

  sec.append(el('div', { class: 'titre', text: 'Détecteurs exploitables sur ce corpus' }));
  const ul = el('ul', { class: 'detecteurs' });
  for (const [code, ok] of Object.entries(v.detecteurs)) {
    ul.append(el('li', { class: ok ? 'vivant' : 'mort', text: `${ok ? '✓' : '✗'}  ${code} — ${SEUILS[code]}` }));
  }
  sec.append(ul);

  if (v.echecs?.length) {
    sec.append(el('div', { class: 'ecartees' }, [
      el('div', { text: 'Pages que le moteur n’a pas pu lire :' }),
      listeCourte(v.echecs.map((e) => `${e.url} — ${e.tag} (${e.code})`), 6),
    ]));
  }

  sec.append(el('p', {
    class: 'provenance',
    text: 'Rappel : un terme présent dans votre requête ne peut pas s’effondrer, '
      + 'puisqu’il conditionne l’appartenance au corpus. Les silences d’un corpus '
      + 'cherché sont en partie des artefacts de la recherche.',
  }));
  return sec;
}
