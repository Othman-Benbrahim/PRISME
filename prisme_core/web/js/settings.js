// ══════════════════════════════════════════════════
//  PARAMÈTRES
// ══════════════════════════════════════════════════
async function openCfg(){
  var c=await fetch('/api/config').then(function(r){return r.json();});
  $('ckey').value='';
  $('ckey').placeholder=c.has_key?'(clé définie — laisser vide pour garder)':'votre clé API';
  cfgFillProviders(c);
  $('kinfo').textContent=c.has_key?'✓ Clé API configurée':'⚠ Aucune clé — IA désactivée';
  $('kinfo').style.color=c.has_key?'var(--grn)':'var(--yel)';
  $('cmod').value=c.model||'';$('cws').value=c.workspace||'';$('curl').value=c.base_url||'';
  $('mcfg').classList.add('on');
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

