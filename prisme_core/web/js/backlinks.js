// ══════════════════════════════════════════════════
//  BACKLINKS
// ══════════════════════════════════════════════════
function switchMMTab(i){
  [0,1].forEach(function(j){ $('mmt'+j).classList.toggle('on',j===i); });
  $('pane-struct').style.display=i===0?'flex':'none';
  $('pane-bl').style.display=i===1?'flex':'none';
  ACTIVE_MM_TAB=i;
  if(i===1&&ACTIVE) loadBacklinks(ACTIVE);
}
async function loadBacklinks(filePath){
  $('bl-list').innerHTML='<div class="bl-empty"><span class="sp"></span></div>';
  var d=await fetch('/api/files/backlinks?path='+eu(filePath)+'&dir='+eu(CUR_DIR)).then(function(r){return r.json();});
  var bl=d.backlinks||[];
  $('bl-count').textContent=bl.length?'('+bl.length+')':'';
  if(!bl.length){$('bl-list').innerHTML='<div class="bl-empty">Aucun backlink trouvé<br><small>Utilisez [[nom_de_fichier]] dans vos notes</small></div>';return;}
  $('bl-list').innerHTML=bl.map(function(b){
    return '<div class="bl-item" onclick="clickBL(\''+eu(b.path)+'\')">'
      +'<div class="bl-name">'+esc(b.name)+'</div>'
      +(b.ctx?'<div class="bl-ctx">'+esc(b.ctx)+'</div>':'')+
      '</div>';
  }).join('');
}
async function clickBL(encoded){
  var path=decodeURIComponent(encoded);
  var d=await fetch('/api/files/read?path='+eu(path)).then(function(r){return r.json();});
  if(d.error){toast('⚠ '+d.error);return;}
  openFileTab(path,d.content);
}

