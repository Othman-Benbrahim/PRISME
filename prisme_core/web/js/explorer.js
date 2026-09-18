// ══════════════════════════════════════════════════
//  EXPLORATEUR DE FICHIERS
// ══════════════════════════════════════════════════
async function loadDir(path){
  var url='/api/files'+(path?'?path='+eu(path):'');
  var d=await fetch(url).then(function(r){return r.json();});
  if(d.error){toast('⚠ '+d.error);return;}
  CUR_DIR=d.path; $('fp-txt').textContent=d.path; $('fp-txt').title=d.path;
  FILE_ITEMS=[];
  if(d.path!==d.parent) FILE_ITEMS.push({path:d.parent,is_dir:true,name:'..'});
  d.items.forEach(function(i){ FILE_ITEMS.push(i); });
  renderFileList(TAG_FILTER);
  loadTags();
}
function renderFileList(tagFilter){
  var show = tagFilter && TAGS_DATA.length
    ? (TAGS_DATA.find(function(t){return t.tag===tagFilter;})||{files:[]}).files
    : null;
  var h='';
  FILE_ITEMS.forEach(function(item,idx){
    if(show && !item.is_dir && !show.includes(item.path)) return;
    var icon=item.name==='..'?'⬆️':item.is_dir?'📁':'📄';
    var cls='fi '+(item.is_dir?'dir':'md');
    h+='<div class="'+cls+'" data-idx="'+idx+'" onclick="clickFile('+idx+')"'
      +' ondblclick="dblFile('+idx+')" oncontextmenu="ctxFile(event,'+idx+')">'
      +'<span class="ic">'+icon+'</span>'
      +'<span class="nm" id="fnm-'+idx+'">'+esc(item.name)+'</span>'
      +'</div>';
  });
  $('fl').innerHTML=h||'<div style="padding:12px;color:var(--tx2);font-size:12px">Dossier vide</div>';
  // Re-bind _path for highlight
  document.querySelectorAll('.fi').forEach(function(el){
    var idx=parseInt(el.dataset.idx);
    if(!isNaN(idx)&&FILE_ITEMS[idx]) el._path=FILE_ITEMS[idx].path;
  });
  if(ACTIVE) highlightFile(ACTIVE);
}
async function clickFile(idx){
  var item=FILE_ITEMS[idx]; if(!item) return;
  if(item.is_dir){loadDir(item.path);return;}
  var d=await fetch('/api/files/read?path='+eu(item.path)).then(function(r){return r.json();});
  if(d.error){toast('⚠ '+d.error);return;}
  openFileTab(item.path,d.content);
}
function dblFile(idx){
  var item=FILE_ITEMS[idx]; if(!item||item.is_dir) return;
  startRename(idx);
}
function ctxFile(e,idx){
  e.preventDefault(); CTX_IDX=idx;
  var item=FILE_ITEMS[idx]; if(!item) return;
  var isDir=item.is_dir;
  $('ctx-open').style.display=isDir?'none':'flex';
  $('ctx-ws').style.display=isDir?'flex':'none';
  $('ctx-graph').style.display=isDir?'flex':'none';
  var m=$('ctx'); m.style.display='block';
  m.style.left=Math.min(e.clientX,window.innerWidth-200)+'px';
  m.style.top=Math.min(e.clientY,window.innerHeight-160)+'px';
}
function hideCtx(){ $('ctx').style.display='none'; }

$('ctx-open').addEventListener('click',function(){ hideCtx(); if(CTX_IDX>=0) clickFile(CTX_IDX); });
$('ctx-ws').addEventListener('click',function(){
  hideCtx(); var item=FILE_ITEMS[CTX_IDX]; if(item) setWorkspaceDir(item.path);
});
$('ctx-graph').addEventListener('click',function(){
  hideCtx(); var item=FILE_ITEMS[CTX_IDX]; if(item&&item.is_dir) openGraph(item.path);
});
$('ctx-del').addEventListener('click',async function(){
  hideCtx(); if(CTX_IDX<0) return;
  var item=FILE_ITEMS[CTX_IDX];
  if(!await confirmer({titre:'Supprimer', danger:true, ok:'Supprimer',
      message:'Supprimer « '+item.name+' » ? L\'élément part dans la corbeille .trash du vault.'})) return;
  var r=await post('/api/files/delete',{path:item.path});
  if(r.error){toast('⚠ '+r.error);return;}
  if(TABS[item.path]) closeTab(item.path);
  loadDir(CUR_DIR); toast(r.trashed?'🗑 Déplacé vers la corbeille (.trash)':'🗑 Supprimé définitivement');
});

// ── Renommage inline ──
function startRename(idx){
  var item=FILE_ITEMS[idx];
  var el=document.querySelector('[data-idx="'+idx+'"] .nm'); if(!el) return;
  var stem=item.name.replace(/\.md$/i,'');
  var inp=document.createElement('input');
  inp.type='text'; inp.value=stem;
  inp.style.cssText='background:var(--bg3);border:1px solid var(--acc);border-radius:4px;color:var(--tx);font-family:var(--font);font-size:12px;padding:1px 6px;width:100%;outline:none';
  el.replaceWith(inp); inp.focus(); inp.select();
  var done=false;
  async function confirm_rename(){
    if(done) return; done=true;
    var newName=inp.value.trim(); if(!newName||newName===stem){loadDir(CUR_DIR);return;}
    if(!newName.endsWith('.md')) newName+='.md';
    var r=await post('/api/files/rename',{old:item.path,new_name:newName});
    if(r.error){toast('⚠ '+r.error);loadDir(CUR_DIR);return;}
    if(TABS[item.path]){
      var c=TABS[item.path]; delete TABS[item.path];
      TABS[r.new_path]=c; if(ACTIVE===item.path) ACTIVE=r.new_path; renderTabBar();
    }
    loadDir(CUR_DIR); toast('✓ Renommé en '+newName);
  }
  inp.addEventListener('keydown',function(e){ if(e.key==='Enter'){e.preventDefault();confirm_rename();} if(e.key==='Escape'){done=true;loadDir(CUR_DIR);} });
  inp.addEventListener('blur',confirm_rename);
}

// ── Workspace ──
async function setWorkspace(){ if(CUR_DIR) setWorkspaceDir(CUR_DIR); }
async function setWorkspaceDir(dir){
  await post('/api/config',{workspace:dir}); loadDir(dir);
  toast('✓ Espace de travail : '+dir.split(/[/\\]/).pop());
}



// ── Création d'un fichier : une ligne de saisie en haut de la liste ──
function startNewFile(){
  if($('fl-new-row')) { $('fl-new-input').focus(); return; }
  var ligne=document.createElement('div');
  ligne.className='fi'; ligne.id='fl-new-row';
  ligne.innerHTML='<span class="ic">📄</span><input id="fl-new-input" type="text" placeholder="nom du fichier, puis Entrée">';
  var liste=$('fl');
  liste.insertBefore(ligne, liste.firstChild);
  var inp=$('fl-new-input');
  inp.style.cssText='background:var(--bg3);border:1px solid var(--acc);border-radius:4px;color:var(--tx);'
    +'font-family:var(--font);font-size:12px;padding:1px 6px;width:100%;outline:none';
  inp.focus();
  var fini=false;
  async function valider(){
    if(fini) return; fini=true;
    var nom=inp.value.trim();
    ligne.remove();
    if(!nom) return;
    var r=await post('/api/files/new',{dir:CUR_DIR,name:nom});
    if(r.error){ toast('⚠ '+r.error); return; }
    openFileTab(r.path,'# '+nom.replace(/\.md$/i,'')+'\n\n');
    loadDir(CUR_DIR);
    toast('✓ Créé dans '+CUR_DIR.split(/[/\\]/).pop());
  }
  inp.addEventListener('keydown',function(e){
    if(e.key==='Enter'){ e.preventDefault(); valider(); }
    else if(e.key==='Escape'){ fini=true; ligne.remove(); }
  });
  inp.addEventListener('blur',valider);
}
