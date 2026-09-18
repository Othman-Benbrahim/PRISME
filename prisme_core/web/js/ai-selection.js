// ══════════════════════════════════════════════════
//  IA SUR SÉLECTION
// ══════════════════════════════════════════════════
$('md-editor').addEventListener('mouseup',function(e){
  setTimeout(function(){
    var sel=window.getSelection();
    if(sel&&sel.toString().trim().length>4) showSelBar(e);
    else hideSelBar();
  },50);
});
function showSelBar(e){
  var bar=$('sel-bar'); bar.style.display='flex';
  var x=Math.min(e.clientX, window.innerWidth-280);
  var y=Math.max(e.clientY-52, 60);
  bar.style.left=x+'px'; bar.style.top=y+'px';
}
function hideSelBar(){ $('sel-bar').style.display='none'; }

var SEL_ACTIONS={
  improve:'Améliore ce texte, rends-le plus clair et percutant. Réponds UNIQUEMENT avec le texte amélioré.',
  shorten:'Raccourcis ce texte en gardant l\'essentiel. Réponds UNIQUEMENT avec le texte raccourci.',
  explain:'Explique ce concept en termes simples. Réponds en français, de façon concise.',
  translate:'Traduis ce texte en anglais. Réponds UNIQUEMENT avec la traduction.'
};
function safeFileName(s){ return s.replace(/[<>:"/\\|?*]/g,'-').replace(/\s+/g,' ').trim().slice(0,60); }

async function aiOnSel(action){
  hideSelBar();
  var sel=window.getSelection();
  var selected=sel?sel.toString().trim():'';
  if(!selected){toast('Sélectionnez du texte d\'abord');return;}

  var META={
    improve  :{label:'amelioration', title:'✨ Amélioration',       sys:'Tu améliores un extrait. Réponds en Markdown propre, en français.'},
    shorten  :{label:'condense',     title:'✂️ Version condensée',  sys:'Tu condenses un extrait sans en perdre l\'essence. Markdown, français.'},
    explain  :{label:'explication',  title:'💡 Explication',        sys:'Tu expliques un passage en termes clairs. Markdown structuré, français.'},
    translate:{label:'traduction',   title:'🌐 Traduction',         sys:'Tu traduis fidèlement en anglais. Markdown, conserve la structure.'}
  };
  var meta=META[action]||{label:'extrait',title:'Extrait',sys:'Tu assistes à la rédaction.'};

  toast('⏳ '+meta.label+' en cours…',6000);

  var cfg=await fetch('/api/config').then(function(r){return r.json();});
  var r=await post('/api/ai',{messages:[
    {role:'system',content:meta.sys},
    {role:'user',content:SEL_ACTIONS[action]+'\n\n=== EXTRAIT ===\n'+selected+'\n=== FIN ==='}
  ],model:cfg.model});
  if(r.error){toast('⚠ '+r.error);return;}

  // Nom du nouveau fichier
  var sourceName=ACTIVE?ACTIVE.split(/[/\\]/).pop().replace(/\.md$/i,''):'note';
  var baseName=safeFileName(meta.label+'-'+sourceName);

  // Création avec suffixe auto-incrémenté si collision
  var newPath=null;
  for(var i=1;i<30;i++){
    var tryName=i===1?baseName:baseName+'-'+i;
    var resp=await post('/api/files/new',{dir:CUR_DIR,name:tryName});
    if(resp.ok){newPath=resp.path;break;}
    if(resp.error!=='Fichier existant'){toast('⚠ '+resp.error);return;}
  }
  if(!newPath){toast('⚠ Impossible de créer le fichier');return;}

  // Construction du contenu
  var content='# '+meta.title+'\n\n';
  if(ACTIVE) content+='*Source :* [['+sourceName+']]\n\n';
  content+='---\n\n'+r.response+'\n\n';
  content+='---\n\n## Extrait original\n\n> '+selected.split('\n').join('\n> ')+'\n';

  await saveGenerated(newPath, content, {type:'reponse', outil:'ia-selection',
    preset:meta.label, sources:ACTIVE?[ACTIVE]:[]});
  openFileTab(newPath,content);
  loadDir(CUR_DIR);
  toast('✓ '+meta.title+' créée');
}

