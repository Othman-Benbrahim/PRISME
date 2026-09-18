// ══════════════════════════════════════════════════
//  MODE ÉDITEUR
// ══════════════════════════════════════════════════
function setMode(m){
  EDITOR_MODE=m;
  ['edit','preview','split'].forEach(function(n){ $('btn-mode-'+n).classList.toggle('on',n===m); });
  if(!ACTIVE) return;
  var ed=$('ed-edit-pane'),pv=$('md-preview'),sd=$('split-div');
  if(m==='edit'){ed.style.display='flex';pv.style.display='none';sd.style.display='none';ed.style.flex='1';}
  else if(m==='preview'){ed.style.display='none';pv.style.display='block';sd.style.display='none';pv.style.flex='1';updatePreview();}
  else{ed.style.display='flex';sd.style.display='block';pv.style.display='block';ed.style.flex='1';pv.style.flex='1';updatePreview();}
  gutterRender();
}
function updatePreview(){
  if(typeof marked==='undefined') return;
  var raw=($('md-editor').value||'');
  // 1. [[wikilinks]] AVANT marked (sinon marked les confond)
  raw=raw.replace(/\[\[([^\]|\n]+?)(?:\|([^\]\n]*))?\]\]/g,function(m,lnk,alias){
    var d=alias||lnk;
    var safe=lnk.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
    return '<span class="wl" onclick="openWikilink(\''+safe+'\')" title="Ouvrir [['+lnk+']]">[['+d+']]</span>';
  });
  var html=marked.parse(raw);
  // 2. Intercepter les <a href="*.md"> générés par marked (liens Markdown standard)
  html=html.replace(/<a href="([^"]+?\.md)"([^>]*)>([^<]*)<\/a>/g,function(m,href,attrs,label){
    if(/^https?:\/\//i.test(href)) return m;  // garder les URLs externes intactes
    var safe=href.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
    return '<span class="wl" onclick="openWikilink(\''+safe+'\')" title="Ouvrir '+href+'">'+(label||href)+'</span>';
  });
  $('md-preview').innerHTML=html;
  if(typeof FIND!=='undefined' && FIND.hits.length && $('find-bar').classList.contains('on')) findMarkPreview();
}
async function openWikilink(name){
  var fromParam = ACTIVE ? '&from='+eu(ACTIVE) : '';
  var d=await fetch('/api/files/find?name='+eu(name)+'&dir='+eu(CUR_DIR)+fromParam).then(function(r){return r.json();});
  if(d.error){toast('⚠ Fichier introuvable : '+name);return;}
  openFileTab(d.path,d.content);
}

// ══════════════════════════════════════════════════
//  SAUVEGARDER / NOUVEAU
// ══════════════════════════════════════════════════
async function saveFile(){
  if(!ACTIVE){toast('Aucun fichier ouvert');return;}
  var c=$('md-editor').value;
  var r=await post('/api/files/save',{path:ACTIVE,content:c});
  if(r.error){toast('⚠ '+r.error);return;}
  TABS[ACTIVE].saved=c; TABS[ACTIVE].modified=false; renderTabBar(); toast('✓ Sauvegardé'); reportHooks(r);
}
// La saisie se fait directement dans la liste des fichiers (voir explorer.js).
function newFilePrompt(){ startNewFile(); }

