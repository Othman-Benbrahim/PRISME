import {el} from './rendu.js';
const champ=(nom,n)=>{const l=el('label',{text:nom});l.append(n);return l;};
const option=(v,t)=>el('option',{value:v,text:t});
export function rendrePreuves({journal,sources,etape,factuelle,modifiable,corriger}){
 const cont=el('section');cont.append(el('h2',{text:'Passages sources et contradictions'}));
 if(factuelle?.sortie?.factuelle){const d=el('details');d.append(el('summary',{text:'Passages de la lecture factuelle (étape 4)'}));for(const p of factuelle.sortie.factuelle){d.append(el('p',{text:p.texte}));for(const a of p.passages||[])d.append(el('p',{text:`${a.source} · positions ${a.debut}–${a.fin}`}),el('blockquote',{text:a.extrait}));if(!p.passages?.length)d.append(el('p',{text:'Aucun passage exact relié.'}));}cont.append(d);}
 if(etape){
  const preuves=etape.sortie?.preuves||[];
  for(const p of preuves){const article=el('article');article.append(el('h3',{text:p.id+' — '+p.enonce}));
   if(!p.passages?.length)article.append(el('p',{text:'Aucun passage exact relié. La référence de source seule ne suffit pas à vérifier cette affirmation.'}));
   for(const a of p.passages||[])article.append(el('p',{text:`${a.source} · positions ${a.debut}–${a.fin} · SHA-256 ${a.texteHash}`}),el('blockquote',{text:a.extrait}));
   cont.append(article);
  }
  for(const c of etape.sortie?.contradictions||[])cont.append(el('p',{class:'tension',text:`Contradiction déclarée ${c.a} ↔ ${c.b} : ${c.motif}`}));
  if(!etape.sortie?.contradictions?.length)cont.append(el('p',{text:'Aucune contradiction déclarée entre les preuves ; cela ne prouve pas leur absence.'}));
  if(modifiable&&preuves.length){
   const detail=el('details'),f=el('form'),p=el('select',{'aria-label':'Preuve à documenter'}),s=el('select',{'aria-label':'Source du passage'}),texte=el('textarea',{rows:'6',readonly:'','aria-label':'Texte conservé de la source'}),extrait=el('textarea',{required:'',rows:'3','aria-label':'Extrait exact'}),debut=el('input',{type:'number',min:'0',step:'1','aria-label':'Position du passage'}),motif=el('input',{required:'','aria-label':'Motif du passage'});
   p.append(...preuves.map(p=>option(p.id,p.id+' — '+p.enonce)));s.append(...sources.map(s=>option(s.id,s.id+' — '+s.titre)));
   const changer=()=>{texte.value=sources.find(x=>x.id===s.value)?.texte||'';};s.addEventListener('change',changer);changer();
   detail.append(el('summary',{text:'Relier une preuve à un passage exact'}));
   f.append(champ('Preuve',p),champ('Source',s),champ('Texte conservé (copiez un passage ci-dessous)',texte),champ('Extrait exact',extrait),champ('Position de début si le passage se répète (facultatif, à partir de 0)',debut),champ('Pourquoi cet ajout ou cette correction ?',motif),el('button',{text:'Ajouter le passage et créer une révision'}));
   f.addEventListener('submit',ev=>{ev.preventDefault();const v=structuredClone(etape.sortie),cible=v.preuves.find(x=>x.id===p.value);if(!cible)return;cible.sources=[...new Set([...cible.sources,s.value])];cible.passages=[...(cible.passages||[]),{source:s.value,extrait:extrait.value,...(debut.value!==''?{debut:Number(debut.value)}:{})}];corriger(etape,JSON.stringify(v),motif.value);});detail.append(f);cont.append(detail);
   const d=el('details'),g=el('form'),a=el('select',{'aria-label':'Première preuve'}),b=el('select',{'aria-label':'Deuxième preuve'}),raison=el('input',{required:'','aria-label':'Motif de contradiction'});
   for(const x of [a,b])x.append(...preuves.map(p=>option(p.id,p.id+' — '+p.enonce)));if(preuves.length>1)b.value=preuves[1].id;
   d.append(el('summary',{text:'Signaler une contradiction entre deux preuves'}));g.append(champ('Première preuve',a),champ('Deuxième preuve',b),champ('Expliquez la contradiction',raison),el('button',{text:'Signaler et créer une révision'}));g.addEventListener('submit',ev=>{ev.preventDefault();const v=structuredClone(etape.sortie);v.contradictions=[...(v.contradictions||[]),{a:a.value,b:b.value,motif:raison.value}];corriger(etape,JSON.stringify(v),raison.value);});d.append(g);cont.append(d);
  }
 }else cont.append(el('p',{text:'Les preuves de l’ACH actuelle apparaîtront ici. Les analyses historiques restent consultables ci-dessous.'}));
 const historique=el('details');historique.append(el('summary',{text:'Historique complet des analyses, corrections et validations'}));
 for(const e of journal.filter(e=>e.t==='etape')){const d=el('details');d.append(el('summary',{text:`Étape ${e.numero} · ${e.validee?'validée le '+e.valideeLe:e.revisionDe?'corrigée le '+e.ts:'proposée le '+e.ts}`}),el('p',{text:e.motifCorrection||e.fournisseur||'Origine non renseignée'}),el('p',{text:e.revisionDe?'Révision précédente : '+e.revisionDe:'Première analyse ou nouvelle exécution'}),el('pre',{text:JSON.stringify(e,null,2)}));historique.append(d);}
 cont.append(historique);return cont;
}
