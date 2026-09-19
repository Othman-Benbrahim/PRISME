// ══════════════════════════════════════════════════
//  PARAMÈTRES
// ══════════════════════════════════════════════════
async function openCfg(){
  var c=await fetch('/api/config').then(function(r){return r.json();});
  $('ckey').value='';
  $('ckey').placeholder=c.has_key?'(clé définie — laisser vide pour garder)':'votre clé API';
  cfgFillProviders(c);
  var ks={chiffree:'✓ Clé API configurée — chiffrée sur cette machine',
          clair:'✓ Clé API configurée — stockée en clair (chiffrement indisponible)',
          illisible:'⚠ Clé illisible sur cette machine — ressaisissez-la',
          vide:'⚠ Aucune clé — IA désactivée pour les services distants'};
  $('kinfo').textContent=ks[c.key_state]||(c.has_key?'✓ Clé API configurée':ks.vide);
  $('kinfo').style.color=(c.key_state==='chiffree')?'var(--grn)':(c.has_key?'var(--yel)':'var(--yel)');
  $('cmod').value=c.model||'';$('cws').value=c.workspace||'';$('curl').value=c.base_url||'';
  $('mcfg').classList.add('on');
  loadIndexStatus();
  vecCharger();
  racCharger();
}
function closeCfg(){$('mcfg').classList.remove('on');}
// SB_SETTINGS_PATCH
function cfgFillProviders(c){
  if(typeof ONB_PROVIDERS === 'undefined') return;
  var url=(c.base_url||'').replace(/\/$/,'');
  var match='custom';
  for(var i=0;i<ONB_PROVIDERS.length;i++){
    if(ONB_PROVIDERS[i].url && ONB_PROVIDERS[i].url.replace(/\/$/,'')===url){ match=ONB_PROVIDERS[i].id; break; }
  }
  $('cprov').innerHTML=ONB_PROVIDERS.map(function(p){
    return '<option value="'+p.id+'">'+p.label+'</option>';}).join('');
  $('cprov').value=match;
  var p=ONB_PROVIDERS.filter(function(x){return x.id===match;})[0];
  if(p){ $('cprov-help').textContent=p.help; if(p.ph && !c.has_key) $('ckey').placeholder=p.ph; }
}

function cfgProv(){
  if(typeof ONB_PROVIDERS === 'undefined') return;
  var p=ONB_PROVIDERS.filter(function(x){return x.id===$('cprov').value;})[0];
  if(!p) return;
  if(p.url) $('curl').value=p.url;
  if(p.model) $('cmod').value=p.model;
  $('cprov-help').textContent=p.help;
  $('ckey').placeholder=p.key?(p.ph||'votre clé API'):'aucune clé nécessaire';
  $('cfg-models').innerHTML='';
}

async function saveCfg(){
  var model=$('cmod').value.trim();
  var url=$('curl').value.trim();
  if(!model){ toast('⚠ Indiquez un modèle — ou cliquez sur « Charger les modèles »',5000); return; }
  if(!url){ toast('⚠ Indiquez l\'URL du service',5000); return; }
  var u={model:model,workspace:$('cws').value,base_url:url};
  var k=$('ckey').value;if(k)u.api_key=k;
  await post('/api/config',u); closeCfg(); toast('✓ Paramètres sauvegardés'); loadDir(u.workspace);
}
async function loadMods(){
  var btn=$('lmobtn');btn.textContent='⏳…';btn.disabled=true;
  var d=await fetch('/api/models').then(function(r){return r.json();});
  btn.textContent='↺ Charger les modèles';btn.disabled=false;
  if(d.models&&d.models.length){
    $('cfg-models').innerHTML=d.models.slice(0,300).map(function(m){
      return '<option value="'+m+'">';}).join('');
    if(!$('cmod').value) $('cmod').value=d.models[0];
    toast('✓ '+d.models.length+' modèles — cliquez dans le champ Modèle');
  }else toast('⚠ '+(d.error||'Aucun modèle — vérifiez la clé et l\'URL'));
}


// ── Index de recherche ──
var IDX_TIMER=null;
var IDX_STATE={vide:'vide',construction:'en construction',pret:'à jour',erreur:'en erreur'};
async function loadIndexStatus(){
  clearTimeout(IDX_TIMER);
  var d=await fetch('/api/index/status').then(function(r){return r.json();});
  if(d.error && !d.state){ $('cidx').textContent='⚠ '+d.error; return; }
  var t=d.files+' note(s), '+d.segments+' segment(s), '+d.links_resolved+'/'+d.links+' lien(s) résolu(s) — '
    +(IDX_STATE[d.state]||d.state);
  if(d.state==='construction') t+=' ('+d.progress.done+' / '+d.progress.total+')';
  if(d.error) t+=' — '+d.error;
  t+=' · recherche '+(d.fulltext==='fts5'?'plein texte (FTS5)':'simple (FTS5 indisponible)');
  if(d.last_duration_s!==null) t+=' · dernière mise à jour '+d.last_duration_s+' s';
  $('cidx').textContent=t;
  $('cidx').title=d.db;
  if(d.state==='construction' && $('mcfg').classList.contains('on')) IDX_TIMER=setTimeout(loadIndexStatus,1000);
}
async function rebuildIndex(){
  var d=await post('/api/index/rebuild',{});
  toast(d.started?'↻ Reconstruction lancée — la recherche reste disponible':'Une mise à jour est déjà en cours');
  setTimeout(loadIndexStatus,300);
}
