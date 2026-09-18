// ══════════════════════════════════════════════════
//  SYNTHÈSE DE DOSSIER
// ══════════════════════════════════════════════════
var SYN_RESULT='', SYN_DIR='';
async function folderSynthesis(dir){
  SYN_DIR=dir||CUR_DIR; if(!SYN_DIR) return;
  $('syn-title').textContent='Synthèse IA — '+SYN_DIR.split(/[/\\]/).pop();
  $('syn-ld').style.display='block'; $('syn-content').style.display='none'; $('syn-footer').style.display='none';
  $('msyn').classList.add('on');
  var cfg=await fetch('/api/config').then(function(r){return r.json();});
  var r=await post('/api/ai/folder',{dir:SYN_DIR,model:cfg.model});
  $('syn-ld').style.display='none';
  if(r.error){$('syn-content').textContent='⚠ '+r.error;$('syn-content').style.display='block';return;}
  SYN_RESULT=r.response;
  $('syn-content').textContent=r.response; $('syn-content').style.display='block'; $('syn-footer').style.display='flex';
}
function closeSyn(){ $('msyn').classList.remove('on'); }
async function saveSynAsFile(){
  if(!SYN_RESULT) return;
  var name='synthese-'+SYN_DIR.split(/[/\\]/).pop()+'.md';
  var r=await post('/api/files/new',{dir:SYN_DIR,name:name});
  if(r.error&&r.error!=='Fichier existant'){toast('⚠ '+r.error);return;}
  var path=r.path||SYN_DIR+'/'+name;
  await saveGenerated(path, '# Synthèse — '+SYN_DIR.split(/[/\\]/).pop()+'\n\n'+SYN_RESULT,
    {type:'synthese', outil:'synthese-dossier', prisme_dossier_source:SYN_DIR});
  openFileTab(path,'# Synthèse — '+SYN_DIR.split(/[/\\]/).pop()+'\n\n'+SYN_RESULT);
  loadDir(CUR_DIR); closeSyn(); toast('✓ Synthèse sauvegardée');
}

