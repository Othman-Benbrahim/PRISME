// ══════════════════════════════════════════════════
//  IA — FICHIER ENTIER
// ══════════════════════════════════════════════════
var SYS='Tu es expert en organisation des connaissances et écriture Markdown. Réponds en français. Quand un fichier t\'est fourni après un séparateur, son contenu est intégralement accessible et tu dois l\'utiliser comme matière de travail.';
var FPRMS={
  improve  :function(c,n){return 'Améliore la qualité rédactionnelle du fichier "'+n+'" ci-dessous (clarté, fluidité, structure). Réponds UNIQUEMENT avec le Markdown amélioré complet, sans préambule.\n\n=== DÉBUT DU FICHIER "'+n+'" ===\n'+c+'\n=== FIN DU FICHIER ===';},
  structure:function(c,n){return 'Restructure le fichier "'+n+'" ci-dessous avec une hiérarchie de titres # ## ### claire et logique. Réponds UNIQUEMENT avec le Markdown restructuré complet.\n\n=== DÉBUT DU FICHIER "'+n+'" ===\n'+c+'\n=== FIN DU FICHIER ===';},
  summarize:function(c,n){return 'Crée un résumé exécutif en Markdown du fichier "'+n+'" ci-dessous (max 200 mots, structuré avec titres et listes). Réponds UNIQUEMENT avec le résumé.\n\n=== DÉBUT DU FICHIER "'+n+'" ===\n'+c+'\n=== FIN DU FICHIER ===';},
  expand   :function(c,n){return 'Enrichis le fichier "'+n+'" ci-dessous en ajoutant détails, exemples et liens conceptuels. Réponds UNIQUEMENT avec le Markdown enrichi complet.\n\n=== DÉBUT DU FICHIER "'+n+'" ===\n'+c+'\n=== FIN DU FICHIER ===';}
};
function toggleFileAI(){
  var el=$('file-ai'),tg=$('fai-toggle');
  el.classList.toggle('open'); tg.classList.toggle('open');
}
async function fileAI(a){
  if(!ACTIVE){toast('Ouvrez un fichier d\'abord');return;}
  var c=$('md-editor').value,n=ACTIVE.split(/[/\\]/).pop();
  await callFileAI([{role:'system',content:SYS},{role:'user',content:FPRMS[a](c,n)}]);
}
async function fileAICustom(){
  var p=$('fap').value.trim(); if(!p){toast('Instruction vide');return;}
  var ctx='';
  if(ACTIVE){
    var fname=ACTIVE.split(/[/\\]/).pop();
    var full=$('md-editor').value;
    var truncated=full.length>12000;
    var shown=full.slice(0,12000);
    ctx='\n\n=== DÉBUT DU FICHIER "'+fname+'"'+(truncated?' (tronqué à 12000 caractères sur '+full.length+')':'')+' ===\n'+shown+'\n=== FIN DU FICHIER ===';
  }
  await callFileAI([{role:'system',content:SYS},{role:'user',content:p+ctx}]);
}
async function callFileAI(msgs){
  var ld=$('fald'),rw=$('farw'),ar=$('faar');
  if(!$('file-ai').classList.contains('open')) toggleFileAI();
  ld.style.display='block'; rw.style.display='none'; ar.style.display='none'; FAIRES=null;
  try{
    var cfg=await fetch('/api/config').then(function(r){return r.json();});
    var r=await post('/api/ai',{messages:msgs,model:cfg.model});
    ld.style.display='none';
    if(r.error){rw.textContent='⚠ '+r.error;rw.style.display='block';return;}
    FAIRES=r.response; rw.textContent=r.response; rw.style.display='block'; ar.style.display='flex';
  }catch(e){ ld.style.display='none'; rw.textContent='⚠ '+e.message; rw.style.display='block'; }
}
function applyFileAI(mode){
  if(!ACTIVE||!FAIRES) return;
  var v=mode==='a'?$('md-editor').value+'\n\n'+FAIRES:FAIRES;
  histSnapshot();
  $('md-editor').value=v; TABS[ACTIVE].content=v; TABS[ACTIVE].modified=v!==TABS[ACTIVE].saved; histSnapshot(); gutterRender();
  renderTabBar(); if(EDITOR_MODE!=='edit') updatePreview();
  updateMindmap(v,ACTIVE.split(/[/\\]/).pop()); toast('✓ Appliqué — Ctrl+S pour sauvegarder');
}

