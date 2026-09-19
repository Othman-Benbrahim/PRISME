// Passages exacts, contradictions déclarées et historique. Aucun jugement automatique de vérité.
export function ancrer(passage,sources){
 const s=sources.find(s=>s.id===passage?.source);
 if(!s||typeof s.texte!=='string')throw Error('Source de passage inconnue');
 const extrait=passage.extrait;
 if(typeof extrait!=='string'||!extrait.trim())throw Error('Extrait exact requis');
 let debut=passage.debut;
 if(debut===undefined){debut=s.texte.indexOf(extrait);if(debut!==s.texte.lastIndexOf(extrait))throw Error('Extrait répété : précisez sa position de début');}
 if(!Number.isInteger(debut)||debut<0||s.texte.slice(debut,debut+extrait.length)!==extrait)throw Error('Extrait absent à cette position dans la source');
 if(passage.texteHash&&passage.texteHash!==s.texteHash)throw Error('La version de la source a changé');
 return {source:s.id,texteHash:s.texteHash,debut,fin:debut+extrait.length,extrait};
}
export function enrichirPreuves(numero,brut,resultat,sources){
 if(![4,5].includes(numero))return resultat;
 const champ=numero===5?'preuves':'factuelle',originaux=brut?.[champ]||[];
 for(const item of resultat.sortie[champ]){
  const original=originaux.find(p=>numero===5?p.id===item.id:p.texte===item.texte);
  item.passages=[];
  try{
   if(original?.passages!==undefined&&!Array.isArray(original.passages))throw Error('Liste de passages attendue');
   for(const p of original?.passages||[]){if(!item.sources.includes(p.source))throw Error('Passage hors des sources de cette affirmation');item.passages.push(ancrer(p,sources));}
   if(item.sources.some(id=>!sources.some(s=>s.id===id)))throw Error('Source citée inconnue');
  }catch(e){resultat.ecartees.push({objet:original,raison:e.message});}
 }
 if(numero===5){
  resultat.sortie.contradictions=[];
  try{
   if(brut.contradictions!==undefined&&!Array.isArray(brut.contradictions))throw Error('Liste de contradictions attendue');
   const ids=resultat.sortie.preuves.map(p=>p.id);
   if(new Set(ids).size!==ids.length)throw Error('Identifiants de preuves dupliqués');
   const hyp=resultat.sortie.hypotheses.map(h=>h.id);
   if(new Set(hyp).size!==hyp.length)throw Error('Identifiants d’hypothèses dupliqués');
   for(const c of brut.contradictions||[]){
    if(!ids.includes(c.a)||!ids.includes(c.b)||c.a===c.b||typeof c.motif!=='string'||!c.motif.trim())throw Error('Contradiction : deux preuves distinctes connues et un motif requis');
    resultat.sortie.contradictions.push({a:c.a,b:c.b,motif:c.motif.trim()});
   }
  }catch(e){resultat.ecartees.push({objet:null,raison:e.message});}
 }
 resultat.complet=resultat.complet&&!resultat.ecartees.length;
 return resultat;
}
export const CONSIGNE_PREUVES='Pour chaque preuve ACH (preuves) et affirmation factuelle (factuelle), ajoute passages:[{source:"s-001",extrait:"citation exacte du texte fourni"}]. Ne reformule pas les extraits. Si un extrait se répète, indique debut, position UTF-16 à partir de zéro. Sépare ce que dit le document de ton inférence. Pour l’ACH, ajoute contradictions:[{a:"P1",b:"P2",motif:"raison de la tension entre ces observations"}] ; [] si aucune contradiction repérée. Ne confonds pas une contradiction entre preuves et une preuve incompatible avec une hypothèse.';
const ligne=v=>String(v??'').replace(/\r?\n/g,' ');
const citation=v=>String(v).split(/\r?\n/).map(l=>'> '+l).join('\n');
export function historiqueMarkdown(journal){
 const lignes=['## Historique des analyses et validations',''];
 for(const e of journal.filter(e=>e.t==='etape'))lignes.push(`- Étape ${e.numero} · ${e.ts} · ${e.validee?'validation humaine le '+e.valideeLe:e.revisionDe?'correction humaine de '+e.revisionDe:'analyse proposée'} · ${ligne(e.motifCorrection||e.fournisseur||'origine non renseignée')}`);
 return lignes.join('\n');
}
export function dossierPreuves({meta,sources,journal},etape,hypotheseId){
 const h=etape.sortie.hypotheses.find(h=>h.id===hypotheseId);
 if(!h||!etape.validee||!etape.complet)throw Error('Hypothèse ACH validée requise');
 const l=['# Pièces de la prédiction Constat','',`Dossier : ${meta.id}`,`Question : ${ligne(meta.question)}`,`ACH : ${etape.ts} · validée le ${etape.valideeLe}`,`Corpus : ${etape.releveRef}`,'',`## ${h.id} — ${ligne(h.enonce)}`,'',`Confirmerait : ${ligne(h.confirmerait)}`,`Réfuterait : ${ligne(h.demolirait)}`,'','Les citations attestent le contenu des documents, pas la vérité des affirmations. Le classement ACH n’est pas une probabilité.',''];
 for(const p of etape.sortie.preuves){
  l.push(`### ${p.id} — ${ligne(p.enonce)}`,`Relation ACH : ${etape.sortie.matrice[p.id]?.[h.id]} (C compatible, I incompatible, N neutre)`,'');
  for(const id of p.sources){const s=sources.find(s=>s.id===id);if(s)l.push(`Source ${id} : ${ligne(s.titre)} · ${ligne(s.url)} · SHA-256 ${s.texteHash}`);}
  if(!p.passages?.length)l.push('**Aucun passage exact relié : preuve à documenter.**');
  for(const psg of p.passages||[]){const a=ancrer(psg,sources);l.push(`Passage ${a.source} · positions UTF-16 ${a.debut}–${a.fin} · SHA-256 ${a.texteHash}`,citation(a.extrait),'');}
 }
 l.push('## Contradictions déclarées','');
 for(const c of etape.sortie.contradictions||[])l.push(`- ${c.a} ↔ ${c.b} : ${ligne(c.motif)}`);
 if(!etape.sortie.contradictions?.length)l.push('Aucune déclarée ; cela ne prouve pas leur absence.');
 l.push('',historiqueMarkdown(journal),'');const contenu=l.join('\n');
 if(new TextEncoder().encode(contenu).length>200000)throw Error('Pièces trop volumineuses (200 ko) : réduisez explicitement les extraits avant de transférer');
 return contenu;
}

export function extraitsMarkdown(etapes){
 const l=['## Passages reliés aux analyses',''];
 for(const e of etapes){
  const items=e.sortie?.preuves||e.sortie?.factuelle;if(!items)continue;
  l.push(`### Étape ${e.numero} · ${e.ts} · ${e.validee?'validée':'non validée'}`,'');
  for(const p of items){l.push(ligne(p.enonce||p.texte));if(!p.passages?.length)l.push('Aucun passage exact relié.');for(const a of p.passages||[])l.push(`Source ${a.source} · SHA-256 ${a.texteHash} · positions UTF-16 ${a.debut}–${a.fin}`,citation(a.extrait),'');}
  for(const c of e.sortie.contradictions||[])l.push(`Contradiction déclarée ${c.a} ↔ ${c.b} : ${ligne(c.motif)}`);
 }
 return l.join('\n');
}
