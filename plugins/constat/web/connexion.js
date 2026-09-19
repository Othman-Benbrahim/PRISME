import { Dossiers } from './core/dossier.js';
let jeton='',espace='',revision=0,donnees={};
export async function requete(route,corps){
  if(!jeton){const r=await fetch('/api/token');if(!r.ok)throw Error('Session PRISME indisponible');jeton=(await r.json()).token;}
  const r=await fetch(route.startsWith('/api/')?route:'/api/plugins/constat/'+route,{
    method:corps===undefined?'GET':'POST',headers:{'X-Prisme-Token':jeton,'X-Constat-Espace':espace,'Content-Type':'application/json'},
    ...(corps===undefined?{}:{body:JSON.stringify(corps)})});
  const d=await r.json();if(!r.ok||d.error){const e=Error(d.error||`PRISME : HTTP ${r.status}`);e.status=r.status;throw e;};return d;
}
const memoire={async get(k){return structuredClone(donnees[k]??null);},async set(k,v){donnees[k]=structuredClone(v);},async remove(k){delete donnees[k];},async keys(){return Object.keys(donnees);}};
export const D=new Dossiers(memoire);
export async function charger(){const d=await requete('etat');espace=d.espace;revision=d.revision;donnees=d.donnees;}
export async function transaction(fn){const avant=structuredClone(donnees);try{const r=await fn();const rep=await requete('etat',{revision,donnees});revision=rep.revision;return r;}catch(e){donnees=avant;throw e;}}
export function sauvegarde(){return structuredClone(donnees);}
export async function importer(d){
 if(d?.format!=='constat/prisme' || d.version!==1 || !d.donnees || typeof d.donnees!=='object')throw Error('Export complet de Constat intégré attendu');
 const ids=d.donnees.dossiers;if(!Array.isArray(ids)||ids.length!==1)throw Error('Un dossier complet attendu');
 const ancien=ids[0],j=d.donnees['j:'+ancien];if(!Array.isArray(j)||!j.some(e=>e.t==='dossier'))throw Error('Journal absent');
 const neuf='d-'+crypto.randomUUID();
 // Une restauration est un nouveau dossier ; les références historiques restent explicitement historiques.
 donnees.dossiers=[...(donnees.dossiers||[]),neuf];
 donnees['j:'+neuf]=j.map(e=>({...e,...(e.t==='dossier'?{id:neuf}:{}),...(e.dossier?{dossier:neuf}:{})}));
 for(const e of j)if(e.t==='source'&&e.texteHash){const k='txt:'+e.texteHash;if(typeof d.donnees[k]!=='string')throw Error('Texte absent du dossier exporté');donnees[k]=d.donnees[k];}
 return neuf;
}
