import {enrichirPreuves} from './preuves.js';
import { empreinteExacte } from './core/empreinte.js';
import { ETAPES, valider } from './core/etapes.js';
import { extraireCitations } from './core/extraction.js';
export async function empreinteCorpus(D,id){
 const sources=await D.corpus(id);const cotations=(await D.journal(id)).filter(e=>e.t==='cotation');
 return (await empreinteExacte(JSON.stringify({sources,cotations}))).slice(0,24);
}
export function etapesCourantes(journal,releve){
 const dernier={};for(const e of journal)if(e.t==='etape'&&e.releveRef===releve?.empreinteCorpus)dernier[e.numero]=e;
 const out={};for(const n of Object.keys(ETAPES)){
  const e=dernier[n];if(!e)continue;
  if(ETAPES[n].requiert.some(p=>!out[p]?.validee||e.parents?.[p]!==out[p].ts))continue;
  out[n]=e;
 }
 return out;
}
export function verifierSortie(numero,brut,sources,courantes){
 const resultat=valider(numero,brut,{idsSources:sources.map(s=>s.id),idsHypotheses:courantes[5]?.sortie.hypotheses.map(h=>h.id)||[],idsScenarios:courantes[7]?.sortie.scenarios.map(s=>s.id)||[]});
 return enrichirPreuves(numero,brut,resultat,sources);
}
export function jsonModele(texte){
 const s=texte.trim().replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');
 return JSON.parse(s);
}
export function urlSource(brute){
 if(!brute)return 'https://source-inconnue.invalid/'+crypto.randomUUID();
 const u=new URL(brute);if(!['http:','https:'].includes(u.protocol)||u.username||u.password)throw Error('URL HTTP(S) sans identifiants attendue');return u.href;
}
export function pageTexte({titre,texte,url,editeur,date,origine='texte saisi'}){
 if(!texte?.trim())throw Error('Texte vide');if(texte.length>2_000_000)throw Error('Texte trop volumineux');
 if(date&&!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('Date invalide');
 const adresse=urlSource(url);
 return {url:adresse,canonical:adresse,titre,texte,editeur:editeur||'inconnu',datePubliee:date||null,liens:[],citations:extraireCitations(texte),
 diagnostic:{origineContenu:origine,caracteres:texte.length,metadonnees:'Liens et balisage absents ; les absences constatées portent sur le texte importé.'}};
}
