import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {ancrer,enrichirPreuves,dossierPreuves} from '../web/preuves.js';
import {Dossiers,stockageMemoire} from '../web/core/dossier.js';
const sources=[{id:'s1',texte:'Début.\nUne panne.\nFin.',texteHash:'version-1',titre:'Note',url:'https://demo.invalid'}];
const v=()=>({sortie:{preuves:[{id:'P1',enonce:'Panne signalée',sources:['s1']}],hypotheses:[{id:'H1'}]},ecartees:[],complet:true});
test('citation exacte : version, positions et accents conservés',()=>{
 assert.deepEqual(ancrer({source:'s1',extrait:'Une panne.'},sources),{source:'s1',texteHash:'version-1',debut:7,fin:17,extrait:'Une panne.'});
 for(const p of [{source:'inconnue',extrait:'x'},{source:'s1',extrait:'panne résolue'},{source:'s1',extrait:'Une panne.',debut:0},{source:'s1',extrait:'Une panne.',texteHash:'autre'}])assert.throws(()=>ancrer(p,sources));
});
test('citation répétée : pas de choix arbitraire, position explicite',()=>{
 const s=[{id:'s',texte:'oui oui',texteHash:'x'}];assert.throws(()=>ancrer({source:'s',extrait:'oui'},s),/répété/);
 assert.equal(ancrer({source:'s',extrait:'oui',debut:4},s).debut,4);
});
test('ancienne ACH conservée, passages absents explicites',()=>{
 const r=enrichirPreuves(5,{preuves:[{id:'P1'}]},v(),sources);assert.equal(r.complet,true);assert.deepEqual(r.sortie.preuves[0].passages,[]);
});
test('citation inventée ou hors sources de la preuve empêche validation',()=>{
 for(const p of [{source:'s1',extrait:'inventé'},{source:'autre',extrait:'Une panne.'}]){
  const r=enrichirPreuves(5,{preuves:[{id:'P1',passages:[p]}]},v(),sources);assert.equal(r.complet,false);assert.ok(r.ecartees.length);
 }
});
test('contradiction doit identifier deux preuves existantes et un motif',()=>{
 const brut={preuves:[{id:'P1'}],contradictions:[{a:'P1',b:'P2',motif:'Désaccord'}]};assert.equal(enrichirPreuves(5,brut,v(),sources).complet,false);
 const r=v();r.sortie.preuves.push({id:'P2',sources:['s1']});assert.deepEqual(enrichirPreuves(5,brut,r,sources).sortie.contradictions,brut.contradictions);
});
test('copie des pièces : hypothèse, citations, contradictions, raisons et validations',()=>{
 const etape={numero:5,ts:'t2',valideeLe:'t3',validee:true,complet:true,releveRef:'corpus',sortie:{hypotheses:[{id:'H1',enonce:'Rétablissement',confirmerait:'test OK',demolirait:'test échoue'}],preuves:[{id:'P1',enonce:'Panne',sources:['s1'],passages:[ancrer({source:'s1',extrait:'Une panne.'},sources)]}],matrice:{P1:{H1:'I'}},contradictions:[]}};
 const c={meta:{id:'d',question:'Question'},sources,journal:[{t:'etape',numero:5,ts:'t2',revisionDe:'t1',motifCorrection:'Correction de lecture'}]};
 const md=dossierPreuves(c,etape,'H1');for(const x of ['> Une panne.','Relation ACH : I','Correction de lecture','validée le t3','version-1'])assert.ok(md.includes(x));
 assert.throws(()=>dossierPreuves(c,{...etape,validee:false},'H1'));
 assert.throws(()=>dossierPreuves({...c,sources:[{...sources[0],texteHash:'modifié'}]},etape,'H1'));
});
test('texte multiligne : hash du corps brut et absence de collision par normalisation',async()=>{
 const D=new Dossiers(stockageMemoire());await D.creer({id:'d',question:'q',perimetre:'p',horizon:'h',decision:'d'});
 const textes=['Un  texte\n\nÀ citer.','Un texte À citer.'];
 for(let i=0;i<2;i++)await D.verser('d',{url:'https://s'+i+'.invalid',texte:textes[i]});
 const s=await D.corpus('d');assert.notEqual(s[0].texteHash,s[1].texteHash);
 for(let i=0;i<2;i++){assert.equal(s[i].texte,textes[i]);assert.equal(s[i].texteHash,createHash('sha256').update(textes[i]).digest('hex'));}
});
