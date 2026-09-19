import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseHTML} from 'linkedom';
import {Dossiers,stockageMemoire} from '../web/core/dossier.js';
import {produire} from '../web/core/releve.js';
import {preparer,regrouper} from '../web/core/cluster.js';
import {empreinteCorpus,etapesCourantes,pageTexte,jsonModele} from '../web/metier.js';
import {demonstration} from '../web/demo.js';
import {preparerPrediction} from '../web/core/prediction.js';
import {rendreEtapes} from '../web/vue/etapes.js';

async function demo(){const D=new Dossiers(stockageMemoire());let id;await demonstration(D,async()=>{const sources=await D.corpus(id);const r=await produire({sources,grappes:regrouper(await preparer(sources)),dossier:id,outil:{nom:'Essai',version:'1'}});r.empreinteCorpus=await empreinteCorpus(D,id);await D.ajouter(id,r);},()=>id,n=>id=n);return {D,id};}
test('démonstration réelle des calculs : trois sources, ACH complète non validée',async()=>{
 const {D,id}=await demo(),j=await D.journal(id),r=(await D.relevés(id)).at(-1),e=etapesCourantes(j,r)[5];
 assert.equal(r.corroboration.sources,3);assert.equal(e.complet,true);assert.equal(e.validee,false);assert.equal(e.modele,'aucun');
 assert.throws(()=>preparerPrediction({dossier:{id},etape:e,hypotheseId:'H1',saisie:{}}),/validée/);
});
test('empreinte change après contenu ou cotation, même avec les mêmes identifiants',async()=>{
 const {D,id}=await demo();const avant=await empreinteCorpus(D,id);await D.ajouter(id,{t:'cotation',source:'s-001',fiabilite:'B',credibilite:'2',motif:'Essai'});
 assert.notEqual(await empreinteCorpus(D,id),avant);
 const s=(await D.corpus(id))[0];await D.verser(id,{...s,texte:s.texte+' Texte corrigé.'});assert.notEqual(await empreinteCorpus(D,id),avant);
});
test('la dernière révision non validée invalide ses descendants',()=>{
 const releve={empreinteCorpus:'r'},j=[{t:'etape',numero:5,releveRef:'r',ts:'a',validee:true},{t:'etape',numero:7,releveRef:'r',ts:'b',validee:true,parents:{5:'a'}}];
 assert.ok(etapesCourantes(j,releve)[7]);j.push({t:'etape',numero:5,releveRef:'r',ts:'c',validee:false});assert.ok(!etapesCourantes(j,releve)[7]);
});
test('pas de bouton de versement avant validation, trois boutons après',async()=>{
 const {document}=parseHTML('<html><body></body></html>');globalThis.document=document;
 const {D,id}=await demo(),r=(await D.relevés(id)).at(-1),e=etapesCourantes(await D.journal(id),r)[5];
 const compter=n=>[...n.querySelectorAll('button')].filter(b=>b.textContent.startsWith('Verser')).length;
 assert.equal(compter(rendreEtapes([e],()=>{},()=>{})),0);assert.equal(compter(rendreEtapes([{...e,validee:true}],()=>{},()=>{})),3);
});
test('texte sans métadonnées : pas de date ni d’éditeur inventés ; URL exécutable refusée',()=>{
 const p=pageTexte({titre:'Essai',texte:'Un texte'});assert.equal(p.datePubliee,null);assert.equal(p.editeur,'inconnu');
 assert.throws(()=>pageTexte({texte:'X',url:'javascript:alert(1)'}));assert.throws(()=>jsonModele('Ce n’est pas du JSON'));
});

test('espace complet : démonstration → validation ACH → proposition, sans extension',async()=>{
 const {document,window}=parseHTML(readFileSync('index.html','utf8'));globalThis.document=document;
 window.HTMLElement.prototype.scrollIntoView=function(){};
 Object.defineProperty(window.HTMLSelectElement.prototype,'value',{configurable:true,get(){return [...this.options].find(o=>o.selected)?.value||this.options[0]?.value||'';},set(v){for(const o of this.options)o.selected=o.value===v;}});
 const $=id=>document.getElementById(id);
 for(const f of document.querySelectorAll('form')){Object.defineProperty(f,'elements',{get:()=>Object.fromEntries([...f.querySelectorAll('[name]')].map(n=>[n.name,n]))});f.reset=()=>{for(const n of f.querySelectorAll('input,textarea'))n.value='';};}
 globalThis.FormData=class{constructor(f){this.d=[...f.querySelectorAll('[name]')].map(n=>[n.name,n.value]);} [Symbol.iterator](){return this.d[Symbol.iterator]();}};
 let stockage={},revision=0,propositions=[],objets=[],copies=[],calActive=true;
 globalThis.fetch=async(route,options={})=>{
  const d=options.body?JSON.parse(options.body):null;let r;
  if(route==='/api/token')r={token:'session-test'};
  else if(route.endsWith('/etat')){if(d){assert.equal(d.revision,revision);stockage=structuredClone(d.donnees);r={revision:++revision};}else r={espace:'vault-test',revision,donnees:stockage};}
  else if(route.endsWith('/configuration'))r={modele:'',service:'',indisponible:'Aucun modèle configuré'};
  else if(route.endsWith('/notes'))r={notes:[]};
  else if(route.endsWith('/exporter')){assert.match(d.contenu,/Pièces de la prédiction/);assert.match(d.contenu,/SHA-256/);r={chemin:'Rapports/pieces.md'};}
  else if(route==='/api/objets/file')r={entrees:objets.length?[]:propositions.map(p=>({...p,cle:'prediction:essai'}))};
  else if(route==='/api/objets/registre?type=prediction')r={objets};
  else if(route==='/api/plugins/calibration/predictions'&&!calActive)return {ok:false,status:404,json:async()=>({error:'Plugin absent'})};
  else if(route==='/api/plugins/calibration/predictions')r={objets:objets.map(o=>({...o,version:'v',inscrite:copies.length>0,horloge:{},pieces:{texte:'Preuves conservées',sha256:'preuve-v1'}}))};
  else if(route==='/api/objets/file/accepter'){assert.equal(d.attendue.cle,'prediction:essai');objets=[{...propositions[0],id:'pred-1',chemin:'Objets/Predictions/test.md',cle:'prediction:essai'}];r={objet:objets[0]};}
  else if(route==='/api/plugins/calibration/inscrire'){assert.equal(d.version_pieces,'preuve-v1');assert.equal(d.horloge.prisme_valide_du_etat,'inconnue');assert.equal(d.horloge.prisme_valide_au_etat,'inconnue');copies.push(d);r={copie:'Objets/Calibration/test.md'};}
  else if(route==='/api/objets/proposer'){assert.equal(options.headers['X-Prisme-Token'],'session-test');assert.ok(!options.headers['X-Prisme-Cle']);propositions.push(d);r={acceptee:true,entree:{cle:'prediction:essai',type:'prediction'}};}
  else throw Error('Route inattendue : '+route);
  return {ok:true,json:async()=>r};
 };
 await import('../web/app.js');
 const attendre=async()=>{for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,2));if(!document.body.hasAttribute('aria-busy'))return;}throw Error('Interface bloquée : '+$('etat').textContent);};
 $('exemple').click();await attendre();assert.match($('question').textContent,/DÉMONSTRATION/,$('etat').textContent);assert.ok(!$('etat').classList.contains('erreur'),$('etat').textContent);
 let b=[...$('etapes').querySelectorAll('button')].find(b=>b.textContent==='Valider l’étape 5');assert.ok(b,$('etat').textContent+' '+$('etapes').textContent);b.click();await attendre();
 b=[...$('etapes').querySelectorAll('button')].find(b=>b.textContent.startsWith('Verser'));assert.ok(b,$('etat').textContent+' '+$('etapes').textContent);b.click();await attendre();
 const f=$('prediction');assert.equal(f.hidden,false);for(const k of ['probabilite','echeance','critere_resolution'])assert.equal(f.elements[k].value,'');
 for(const [k,v]of Object.entries({probabilite:'0.8',echeance:'2099-01-01',critere_resolution:'Une réponse HTTP 200 dans le scénario fictif'}))f.elements[k].value=v;
 const ev=()=>new window.Event('submit',{cancelable:true});f.dispatchEvent(ev());f.dispatchEvent(ev());await attendre();
 assert.equal(propositions.length,1,$('etat').textContent);assert.equal(propositions[0].champs.probabilite,.8);assert.equal(propositions[0].note,'Rapports/pieces.md');
 assert.match($('etat').textContent,/Calibration/);assert.ok(Object.values(stockage).some(v=>Array.isArray(v)&&v.some(e=>e.t==='prisme-proposition')));
 $('charger-transferts').click();await attendre();
 const accepter=[...$('transferts').querySelectorAll('button')].find(b=>b.textContent.includes('accepter cette prédiction'));assert.ok(accepter,$('etat').textContent);accepter.click();await attendre();assert.equal(objets.length,1);assert.equal(copies.length,0);
 const copie=$('transferts').querySelector('form');assert.ok(copie,$('etat').textContent);copie.dispatchEvent(ev());copie.dispatchEvent(ev());await attendre();assert.equal(copies.length,1);assert.match($('transferts').textContent,/Copie de référence présente/);
 calActive=false;$('charger-transferts').click();await attendre();assert.match($('transferts').textContent,/absent ou désactivé/);assert.equal($('transferts').querySelector('form'),null);

});
