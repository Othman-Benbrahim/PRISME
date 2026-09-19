var CAL = {selection: null};
function calEl(tag, texte){var n=document.createElement(tag);if(texte!==undefined)n.textContent=texte;return n;}
function calMessage(t, erreur){$('cal-etat').textContent=t;$('cal-etat').classList.toggle('erreur',!!erreur);}
function calFermer(){$('m-calibration').classList.remove('on');}
async function calOuvrir(){$('m-calibration').classList.add('on');await calCharger();}
function calN(v){return v===null ? 'Non calculé' : v==='infini' ? '∞' : typeof v==='number' ? v.toFixed(4) : String(v);}
async function calCharger(){
  try{
    var d=await fetch('/api/plugins/calibration/predictions').then(r=>r.json());
    if(d.error)throw new Error(d.error);
    var cont=$('cal-predictions');cont.replaceChildren();
    (d.objets||[]).forEach(o=>{
      var ligne=calEl('article');ligne.append(calEl('strong',o.titre),calEl('p','p = '+o.champs.probabilite+' · échéance '+o.champs.echeance+' · '+o.champs.statut));
      if(o.inscrite)ligne.append(calEl('span','Copie de référence présente'));
      else if(o.champs.statut==='ouverte'){
        var b=calEl('button','Préparer la copie');b.className='btn bs';b.type='button';b.onclick=()=>calPreparer(o);ligne.append(b);
      }else ligne.append(calEl('span','Non inscrit avant résolution : exclu des scores'));
      cont.append(ligne);
    });
    if(!d.objets?.length)cont.append(calEl('p','Aucune prédiction E11 valide et relue.'));
    if(d.erreurs?.length)cont.append(calEl('p',d.erreurs.length+' fiche(s) invalide(s) : voir les exclusions.'));
    await calRapport();
  }catch(e){calMessage(e.message,true);}
}
function calPreparer(o){
  CAL.selection=o;$('cal-titre').textContent=o.titre;
  ['du','au'].forEach(s=>{var etat=o.horloge['prisme_valide_'+s+'_etat']||'inconnue';$('cal-'+s+'-etat').value=etat;$('cal-'+s).value=o.horloge['prisme_valide_'+s]||'';calBorne(s);});
  $('cal-form').hidden=false;$('cal-form').scrollIntoView({block:'nearest'});
}
function calBorne(s){var date=$('cal-'+s+'-etat').value==='date';$('cal-'+s).disabled=!date;$('cal-'+s).required=date;}
async function calInscrire(e){
  e.preventDefault();var b=e.submitter;b.disabled=true;
  try{
    var h={};['du','au'].forEach(s=>{var et=$('cal-'+s+'-etat').value;h['prisme_valide_'+s+'_etat']=et;h['prisme_valide_'+s]=et==='date'?$('cal-'+s).value:null;});
    var d=await post('/api/plugins/calibration/inscrire',{chemin:CAL.selection.chemin,version:CAL.selection.version,horloge:h});
    if(d.error)throw new Error(d.error);
    $('cal-form').hidden=true;await calCharger();calMessage('Pari copié le '+d.capture_le);loadDir(CUR_DIR);
  }catch(err){calMessage(err.message,true);}finally{b.disabled=false;}
}
function calTable(titre, entetes, lignes){
  var div=calEl('div');div.className='cal-table';div.append(calEl('h3',titre));
  var t=calEl('table'),h=calEl('tr');entetes.forEach(x=>h.append(calEl('th',x)));t.append(h);
  lignes.forEach(l=>{var tr=calEl('tr');l.forEach(v=>tr.append(calEl('td',v)));t.append(tr);});div.append(t);return div;
}
function calCourbe(classes){
  var ns='http://www.w3.org/2000/svg',s=document.createElementNS(ns,'svg');s.setAttribute('viewBox','0 0 360 310');s.setAttribute('role','img');s.setAttribute('aria-label','Calibration : probabilité prévue horizontalement, fréquence observée verticalement. La diagonale représente une calibration parfaite.');
  function el(n,attrs,text){var x=document.createElementNS(ns,n);Object.keys(attrs).forEach(k=>x.setAttribute(k,attrs[k]));if(text)x.textContent=text;s.append(x);}
  el('path',{d:'M45 20V270H330',stroke:'currentColor',fill:'none'});el('path',{d:'M45 270L295 20',stroke:'gray','stroke-dasharray':'5 4',fill:'none'});
  [0,0.5,1].forEach(v=>{el('text',{x:45+v*250,y:288,fill:'currentColor','font-size':11},String(v));el('text',{x:12,y:274-v*250,fill:'currentColor','font-size':11},String(v));});
  el('text',{x:70,y:306,fill:'currentColor','font-size':11},'Probabilité prévue → (vertical : fréquence)');
  classes.filter(c=>c.n).forEach(c=>{el('circle',{cx:45+c.probabilite*250,cy:270-c.frequence*250,r:5,fill:'#60a5fa'});});return s;
}
async function calRapport(){
  try{
    var d=await fetch('/api/plugins/calibration/rapport?jour='+encodeURIComponent($('cal-jour').value)).then(r=>r.json());if(d.error)throw new Error(d.error);
    var cont=$('cal-resultats');cont.replaceChildren();var g=d.global_;
    cont.append(calEl('h3',g.n+' prédiction(s) scorée(s)'),calEl('p','Brier : '+calN(g.brier)+' · Log loss : '+calN(g.log_loss)+' · Biais moyen p − résultat : '+calN(g.biais)));
    cont.append(calEl('p','Statistiques descriptives, pas une preuve de biais systématique. Plus bas est meilleur pour Brier et log loss. Une certitude fausse donne une log loss infinie.'));
    if(g.n){cont.append(calCourbe(g.classes));cont.append(calTable('Classes de calibration',['Intervalle','n','p moyen','Fréquence observée'],g.classes.map((c,i)=>['['+c.de+' ; '+c.a+(i===9?']':'['),c.n,calN(c.probabilite),calN(c.frequence)])));}
    [['Par domaine',d.domaines],['Par horizon à la copie',d.horizons]].forEach(pair=>cont.append(calTable(pair[0],['Groupe','n','Brier','Log loss','Biais'],Object.entries(pair[1]).map(([k,v])=>[k,v.n,calN(v.brier),calN(v.log_loss),calN(v.biais)]))));
    cont.append(calTable('Exclusions',['Note','Raison'],d.exclus.map(x=>[x.chemin,x.raison])));calMessage('Rapport actualisé : '+d.exclus.length+' exclusion(s).');
  }catch(e){calMessage(e.message,true);}
}
async function calExporter(){try{var d=await post('/api/plugins/calibration/exporter',{jour:$('cal-jour').value||null});if(d.error)throw new Error(d.error);calMessage('Rapport enregistré : '+d.chemin);loadDir(CUR_DIR);}catch(e){calMessage(e.message,true);}}
$('cal-form').addEventListener('submit',calInscrire);
['du','au'].forEach(s=>$('cal-'+s+'-etat').addEventListener('change',()=>calBorne(s)));
document.addEventListener('keydown',e=>{if(e.key==='Escape')calFermer();});
