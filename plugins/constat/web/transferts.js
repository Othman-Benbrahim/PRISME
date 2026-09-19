import {el} from './vue/rendu.js';
export function installerTransferts({requete,agir,dire,lire}){
 const cont=document.getElementById('transferts');
 const executer=(fn)=>agir(fn,false);
 async function memeDossier(id){const c=await lire();if(c.id!==id||!c.ouvert)throw Error('Choisissez le même dossier actif avant de confirmer.');}
 async function charger(){
  const {id,ouvert}=await lire();if(!id)throw Error('Choisissez un dossier.');
  const file=await requete('/api/objets/file');
  const pred=await requete('/api/objets/registre?type=prediction');
  let cal=null;try{cal=await requete('/api/plugins/calibration/predictions');}catch(e){if(e.status!==404)throw e;}
  if((await lire()).id!==id)return;cont.replaceChildren();cont.dataset.dossier=id;
  if(!cal)cont.append(el('p',{text:'Calibration est absent ou désactivé. Vous pouvez accepter la prédiction ; activez ensuite le plugin pour conserver sa copie.'}));
  const appartient=o=>o.champs?.hypothese?.startsWith('constat:'+id+':');
  for(const p of file.entrees.filter(p=>p.type==='prediction'&&appartient(p))){
   const a=el('article');a.append(el('h3',{text:p.titre+' — en attente de validation'}),el('pre',{text:JSON.stringify(p.champs,null,2)}),el('p',{text:p.motif||''}),el('p',{text:'Pièces conservées : '+(p.note||'aucune (ancienne proposition)')}));
   const b=el('button',{type:'button',text:'J’ai relu : accepter cette prédiction'});b.disabled=!ouvert;
   b.onclick=()=>executer(async()=>{await memeDossier(id);await requete('/api/objets/file/accepter',{cle:p.cle,attendue:p,raison:'Hypothèse Constat relue et acceptée explicitement dans son dossier.'});dire('Prédiction acceptée. Relisez ses pièces puis confirmez séparément sa copie dans Calibration.');await charger();});a.append(b);cont.append(a);
  }
  for(const p of pred.objets.filter(appartient)){
   const o=cal?.objets.find(o=>o.id===p.id),a=el('article');a.append(el('h3',{text:p.titre}),el('p',{text:`p = ${p.champs.probabilite} · échéance ${p.champs.echeance} · ${p.champs.statut}`}),el('p',{text:'Condition de résolution : '+p.champs.critere_resolution}));
   if(o?.pieces){const d=el('details');d.append(el('summary',{text:'Relire les pièces qui accompagneront le pari'}),el('pre',{text:o.pieces.texte}));a.append(d);}
   if(o?.inscrite)a.append(el('p',{text:'Copie de référence présente dans Calibration. Renseignez ultérieurement le résultat observé et sa preuve dans l’objet Prédiction pour obtenir les scores.'}));
   else if(o&&p.champs.statut==='ouverte'){
    const f=el('form');f.append(el('p',{text:'Horloge du monde : indiquez seulement la période de validité connue de la prédiction. Une borne inconnue reste inconnue ; ce n’est pas sa date d’enregistrement.'}));
    const bornes={};
    for(const [k,nom] of [['du','Début de validité'],['au','Fin de validité']]){
     const label=el('label',{text:nom}),etat=el('select',{'aria-label':nom+' : état'}),date=el('input',{type:'date','aria-label':nom+' : date'});
     for(const [v,t] of [['inconnue','Inconnue'],['ouverte','Sans borne'],['date','Date connue']])etat.append(el('option',{value:v,text:t}));
     etat.value=o.horloge['prisme_valide_'+k+'_etat']||'inconnue';date.value=o.horloge['prisme_valide_'+k]||'';
     const changer=()=>{date.disabled=etat.value!=='date';date.required=!date.disabled;};etat.onchange=changer;changer();label.append(etat,date);f.append(label);bornes[k]={etat,date};
    }
    const b=el('button',{text:'Confirmer la copie du pari et de ses pièces dans Calibration'});b.disabled=!ouvert;f.append(b);
    f.onsubmit=ev=>{ev.preventDefault();executer(async()=>{await memeDossier(id);const horloge={};for(const [k,v]of Object.entries(bornes)){horloge['prisme_valide_'+k+'_etat']=v.etat.value;horloge['prisme_valide_'+k]=v.etat.value==='date'?v.date.value:null;}
     const r=await requete('/api/plugins/calibration/inscrire',{chemin:o.chemin,version:o.version,version_pieces:o.pieces?.sha256,horloge});
     dire('Pari et pièces copiés dans '+r.copie+'. Les scores apparaîtront après une résolution observée.');await charger();
    });};a.append(f);
   }else a.append(el('p',{text:cal?'Cette fiche n’est pas disponible pour une nouvelle copie ; consultez Calibration.':'Activez Calibration pour inscrire ce pari.'}));
   cont.append(a);
  }
  if(!file.entrees.some(p=>p.type==='prediction'&&appartient(p))&&!pred.objets.some(appartient))cont.append(el('p',{text:'Aucune prédiction de ce dossier. Validez une ACH puis utilisez « Verser » sur une hypothèse.'}));
 }
 document.getElementById('charger-transferts').onclick=()=>executer(charger);
}
