// ══════════════════════════════════════════════════
//  ONGLETS
// ══════════════════════════════════════════════════
function openFileTab(path,content){
  if(!TABS[path]) TABS[path]={content:content,saved:content,modified:false};
  switchTab(path);
}
function switchTab(path){
  if(ACTIVE&&TABS[ACTIVE]) TABS[ACTIVE].content=$('md-editor').value;
  ACTIVE=path;
  renderTabBar();
  if(!path){showNoFile();return;}
  var t=TABS[path];
  $('no-file').style.display='none';
  $('md-editor').style.display=EDITOR_MODE==='preview'?'none':'flex';
  $('md-preview').style.display=EDITOR_MODE==='edit'?'none':'block';
  $('split-div').style.display=EDITOR_MODE==='split'?'block':'none';
  $('md-editor').value=t.content;
  $('ed-fname').textContent=path.split(/[/\\]/).pop();
  $('ed-fname').title=path;
  if(EDITOR_MODE!=='edit') updatePreview();
  updateMindmap(t.content,path.split(/[/\\]/).pop());
  if(ACTIVE_MM_TAB===1) loadBacklinks(path);
  highlightFile(path);
}
function closeTab(path){
  if(TABS[path]&&TABS[path].modified)
    if(!confirm('Fermer sans sauvegarder ?')) return;
  delete TABS[path];
  var keys=Object.keys(TABS);
  ACTIVE=keys.length?keys[keys.length-1]:null;
  renderTabBar(); if(ACTIVE) switchTab(ACTIVE); else showNoFile();
}
function renderTabBar(){
  var h=Object.keys(TABS).map(function(p){
    var t=TABS[p],nm=p.split(/[/\\]/).pop();
    return '<div class="ftab'+(ACTIVE===p?' act':'')+(t.modified?' modified':'')+'" data-p="'+eu(p)+'">'
      +'<span class="tmod"></span><span class="tnm">'+esc(nm)+'</span>'
      +'<button class="tcls" data-cp="'+eu(p)+'">×</button></div>';
  }).join('');
  h+='<button id="tab-new" onclick="newFilePrompt()" title="Nouveau">＋</button>';
  $('tab-bar').innerHTML=h;
}
$('tab-bar').addEventListener('click',function(e){
  var cls=e.target.closest('.tcls');
  if(cls){closeTab(decodeURIComponent(cls.dataset.cp));return;}
  var tab=e.target.closest('.ftab');
  if(tab) switchTab(decodeURIComponent(tab.dataset.p));
});
function showNoFile(){
  $('no-file').style.display='flex'; $('md-editor').style.display='none';
  $('md-preview').style.display='none'; $('split-div').style.display='none';
  $('ed-fname').textContent='Aucun fichier';
}
function highlightFile(path){
  document.querySelectorAll('.fi').forEach(function(f){
    f.classList.toggle('act',f._path&&f._path===path);
  });
}
function onEditorInput(){
  if(!ACTIVE||!TABS[ACTIVE]) return;
  var v=$('md-editor').value;
  TABS[ACTIVE].content=v;
  TABS[ACTIVE].modified=v!==TABS[ACTIVE].saved;
  renderTabBar();
  if(EDITOR_MODE!=='edit') updatePreview();
  debounceMM();
}
var mmTimer;
function debounceMM(){ clearTimeout(mmTimer); mmTimer=setTimeout(function(){ if(ACTIVE) updateMindmap($('md-editor').value,ACTIVE.split(/[/\\]/).pop()); },600); }

