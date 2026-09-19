// etapes.js — le pipeline OSINT, une étape à la fois.
//
// §7.1 du handoff : ne jamais lancer les 11 étapes en un seul appel. Le skill
// fonctionne dans une conversation parce qu'on peut contester une étape et
// reprendre. Une étape reçoit ici la sortie VALIDÉE par l'utilisateur de la
// précédente, jamais sa sortie brute.
//
// §7.2 : les références du skill sont embarquées et chargées conditionnellement.
// N'injecter que celle qui correspond à l'étape lancée est ce qui préserve la
// profondeur du skill sans faire exploser le prompt — les onze pèsent 136 Ko,
// une seule en pèse 10 à 13.
//
// Principe conservé partout : le modèle remplit, l'outil calcule. Le classement
// ACH n'est pas demandé au modèle, il est déduit de la matrice qu'il a remplie.
// Un rang produit par le modèle serait un nombre du registre B déguisé en fait.



export const ETAPES = {
  4: {
    numero: 4,
    nom: 'Analyse triple',
    references: ['signaux-faibles.md', 'lecture-symbolique-fractale.md'],
    requiert: [],
    consigne: `Tu produis trois lectures du corpus. Elles ne s'additionnent pas :
elles se répondent.

1. "factuelle"  — ce que le corpus établit. Quantitatif et qualitatif.
2. "signaux"    — ce que la lecture factuelle a laissé de côté. Anomalies,
                  répétitions faibles, ruptures de ton, absences.
3. "symbolique" — quelle structure unifie le tout. Motif, précédent,
                  reproduction d'un schéma connu à une autre échelle.

Chaque énoncé de la lecture symbolique DOIT nommer l'appui factuel qui l'étaye,
dans le champ "appui". Un archétype plaqué sans fait est de la spéculation
déguisée, et sera rejeté.

Puis dis si les trois lectures convergent. Si elles divergent, la divergence est
elle-même un signal : dis ce qu'elle révèle. Ne la lisse pas.

N'invente aucune précision chiffrée que le relevé ne contient pas.

Réponds UNIQUEMENT par un objet JSON :
{
  "factuelle":  [{"texte":"...","sources":["s-003"]}],
  "signaux":    [{"texte":"...","pourquoiNeglige":"..."}],
  "symbolique": [{"texte":"...","appui":"le fait précis qui l’étaye"}],
  "convergence": {"statut":"convergent|divergent|partiel","revele":"..."}
}`,
  },

  5: {
    numero: 5,
    nom: 'Hypothèses concurrentes (ACH)',
    references: ['ach-heuer.md'],
    requiert: [],
    consigne: `Tu appliques la méthode ACH (Heuer) au corpus décrit.

Énumère 3 à 7 hypothèses concurrentes. Trois rôles sont obligatoires :
- "dominante"  : le narratif majoritaire, celui qui semble évident.
- "dissidente" : contre-intuitive mais structurellement plausible.
- "fractale"   : interprète l'événement à une autre échelle.
Rôles facultatifs : "strategique" (manœuvre planifiée d'un acteur),
"systemique" (effet de système, l'œuvre de personne).

Liste ensuite les preuves disponibles, chacune rattachée aux identifiants de
source du corpus. Puis remplis la matrice preuves × hypothèses avec, pour
chaque case, exactement une valeur : "C" compatible, "I" incompatible,
"N" neutre.

Ne désigne AUCUNE hypothèse comme retenue. Le classement est calculé hors de
toi, à partir de ta matrice, sur le nombre de preuves incompatibles — pas sur
le nombre de preuves compatibles. Cette inversion est le cœur de la méthode.

Pour chaque hypothèse, donne ce qui la confirmerait et ce qui la démolirait.
Sans ces deux indicateurs, une hypothèse n'est pas testable.

Réponds UNIQUEMENT par un objet JSON :
{
  "hypotheses": [{"id":"H1","role":"dominante","enonce":"...",
                  "confirmerait":"...","demolirait":"..."}],
  "preuves":    [{"id":"P1","enonce":"...","sources":["s-003"]}],
  "matrice":    {"P1": {"H1":"C","H2":"I","H3":"N"}}
}`,
  },

  7: {
    numero: 7,
    nom: 'Scénarios prospectifs',
    references: ['scenarios-prospectifs.md'],
    requiert: [5],
    consigne: `Tu construis des scénarios à partir des hypothèses validées fournies.

Trois rôles obligatoires, un facultatif :
- "optimiste" : la trajectoire favorable structurellement activable — pas le
  scénario magique.
- "probable"  : la continuation des tendances, sans rupture majeure.
- "critique"  : le point de bascule plausible — pas la catastrophe fantasmée.
- "fractal"   : et si ce qui se prépare reproduisait, à cette échelle, un
  précédent identifiable ? (facultatif)

Pour chaque scénario : forces motrices, conditions d'apparition, indicateurs de
bascule concrets et OBSERVABLES, impact prévisible, niveau de confiance
("faible", "moderee" ou "elevee").

Un scénario n'engage que sa structure logique. Il ne dit pas « cela arrivera »,
il dit « cela peut arriver si ces conditions se réunissent, et voici comment le
savoir ». N'écris aucune probabilité de 0 ni de 1, aucune prophétie.

Réponds UNIQUEMENT par un objet JSON :
{
  "scenarios": [{"id":"S1","role":"probable","titre":"...",
                 "drivers":["..."],"conditions":["..."],
                 "indicateursBascule":["signal concret et observable"],
                 "impact":"...","confiance":"moderee",
                 "hypotheses":["H1"]}]
}`,
  },

  8: {
    numero: 8,
    nom: 'Évaluation du risque',
    references: ['matrice-risque.md'],
    requiert: [7],
    consigne: `Tu évalues le risque associé à chaque scénario validé fourni.

Pour chaque scénario : probabilité ("faible", "moderee" ou "elevee"), impact
("mineur", "important" ou "critique"), les dimensions touchées (humaine,
economique, politique, mediatique, operationnelle, symbolique), et ta confiance
dans l'évaluation.

Tu ne calcules AUCUN niveau de risque. Le croisement probabilité × impact est
fait hors de toi, à partir des deux niveaux que tu donnes.

CONDITIONNEMENT OBLIGATOIRE. Chaque évaluation doit préciser dans quelles
conditions elle tient — au moins une condition explicite. Sans conditionnement,
une évaluation de risque devient une prophétie, donc une faute professionnelle.
Une évaluation sans condition sera rejetée.

Ne mets pas tout au niveau critique, ni tout au niveau modéré. Les deux
travers se valent : le premier noie l'alerte, le second la supprime.

Réponds UNIQUEMENT par un objet JSON :
{
  "evaluations": [{"scenario":"S1","probabilite":"moderee","impact":"important",
                   "dimensions":["politique","economique"],
                   "conditions":["si les pourparlers échouent avant le 30 mars"],
                   "confiance":"moderee","justification":"..."}]
}`,
  },

  9: {
    numero: 9,
    nom: 'Recommandations actionnables',
    references: ['format-rapport.md'],
    requiert: [8],
    consigne: `Tu formules 2 à 4 recommandations, adressées à la personne qui
porte la décision sous-jacente du dossier — personne d'autre.

Chacune doit être :
- concrète : une action nommable, pas un principe général ;
- priorisée : "haute", "moyenne" ou "basse" ;
- datée : "court", "moyen" ou "long" terme ;
- ressourcée : qui fait, avec quoi, à partir de quoi ;
- réversible si possible : ne verrouille pas la décision.

Donne aussi, pour chacune, le risque de ne rien faire.

Sont rejetés d'office : « suivre attentivement la situation », « renforcer la
coopération », « agir avant qu'il ne soit trop tard », et toute recommandation
visant un acteur nommé plutôt que le porteur de la décision. Ce sont des
formules vides ou des consignes d'action contre un tiers ; ni l'une ni l'autre
n'a sa place ici.

Réponds UNIQUEMENT par un objet JSON :
{
  "recommandations": [{"id":"R1","priorite":"haute","terme":"court",
                       "action":"...","ressources":"...",
                       "risqueInaction":"...","reversible":true,
                       "scenarios":["S1"]}]
}`,
  },

  10: {
    numero: 10,
    nom: 'Contrôle des biais',
    references: ['biais-cognitifs.md'],
    requiert: [5, 7],
    consigne: `Tu audites l'analyse produite aux étapes précédentes. Tu ne la
réécris pas : tu cherches ce qui cloche.

Réponds à la check-list, une entrée par point, sans en omettre aucun :
  preuves_contraires · ancrage · effet_miroir · surmediatisation ·
  equipe_rouge · registres_distingues · lacunes_precisees

Pour chacun : "reponse" ("oui", "non" ou "partiel"), "justification", et
"vise" — la liste des identifiants d'hypothèses ou de scénarios concernés,
vide si aucun.

Ajoute "lacunes" : ce que le corpus ne permet pas de savoir. Rappel : une
absence dans le corpus n'est pas une absence dans le monde.

Ajoute "demolition" : le raisonnement qu'une équipe rouge opposerait en trois
minutes. S'il n'y en a pas, tu n'as pas cherché.

Réponds UNIQUEMENT par un objet JSON :
{
  "checklist": [{"point":"preuves_contraires","reponse":"partiel",
                 "justification":"...","vise":["H1"]}],
  "lacunes":   ["..."],
  "demolition":"..."
}`,
  },
};

const ETAPE_11 = {
  numero: 11,
  nom: 'Boucle de rétroaction',
  references: ['calibration-engine.md'],
  requiert: [],
  consigne: `Tu clôtures l'analyse. Une analyse livrée n'est pas un point final :
c'est un état de la question à un instant T.

Donne :
- "invalidants" : les données qui, si elles apparaissaient, forceraient à
  réviser l'analyse. Précises, observables.
- "lacunes" : ce qu'on ne sait pas encore, explicitement.
- "prochainPoint" : quand réévaluer, et sur quel déclencheur.
- "signaux" : la liste courte des indicateurs critiques à surveiller.

Sont rejetés : « l'avenir nous le dira », « tout est possible », et toute
certitude absolue. Le premier est abdicatif, le deuxième équivaut à n'avoir
rien dit, le troisième est toujours suspect en prospective.

Réponds UNIQUEMENT par un objet JSON :
{
  "invalidants": ["..."],
  "lacunes": ["..."],
  "prochainPoint": {"quand":"...","declencheur":"..."},
  "signaux": ["..."]
}`,
};

ETAPES[11] = ETAPE_11;

/* ------------------------------------------------------------- prompts */

/**
 * Construit le contenu d'un appel d'étape.
 *
 * @param {object} a
 * @param {number} a.numero        étape à lancer
 * @param {object} a.meta          question, périmètre, horizon, décision
 * @param {object} a.releve        relevé déterministe
 * @param {string|string[]} a.reference contenu du ou des fichiers references/*.md
 * @param {object} a.precedentes   { 5: sortieValidee, 7: sortieValidee }
 */
export function construirePrompt({ numero, meta, releve, reference, precedentes = {} }) {
  const e = ETAPES[numero];
  if (!e) throw new Error(`étape inconnue : ${numero}`);

  for (const n of e.requiert) {
    if (!precedentes[n]) {
      throw new Error(`l’étape ${numero} exige la sortie validée de l’étape ${n}`);
    }
  }

  const L = [];
  L.push(`# ÉTAPE ${e.numero} — ${e.nom}`, '');
  L.push('# QUESTION');
  L.push(`Question : ${meta.question}`);
  L.push(`Périmètre : ${meta.perimetre}`);
  L.push(`Horizon : ${meta.horizon}`);
  L.push(`Décision sous-jacente : ${meta.decision}`, '');

  L.push('# RELEVÉ DÉTERMINISTE');
  const co = releve.corroboration;
  L.push(`${co.sources} sources · ${co.editeurs} éditeurs · ${co.grappes} grappes · `
    + `${co.comptesRendusDistincts} comptes rendus distincts.`);
  L.push(`${releve.acteurs.citationsRelevees} citations relevées, `
    + `${releve.acteurs.citationsAttribuees} rattachées à un acteur nommé.`);
  for (const c of releve.silences.calcules) L.push(`- ${c.code} = ${c.constat}`);
  L.push('Points sur lesquels tu ne sais rien (non calculés) :');
  for (const n of releve.silences.nonCalcules) L.push(`- ${n.code} : ${n.raison}`);
  if (!releve.silences.nonCalcules.length) L.push('- aucun');
  L.push('');

  for (const n of e.requiert) {
    L.push(`# SORTIE VALIDÉE DE L’ÉTAPE ${n}`);
    L.push(JSON.stringify(precedentes[n], null, 1), '');
  }

  const refs = [].concat(reference ?? []).filter(Boolean);
  if (refs.length) {
    L.push('# RÉFÉRENCE MÉTHODOLOGIQUE', '');
    L.push(refs.join('\n\n---\n\n'), '');
  }

  return L.join('\n');
}
