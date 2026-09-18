// ══════════════════════════════════════════════════
//  RECHERCHE
// ══════════════════════════════════════════════════
function openSearch(){
  $('msearch').classList.add('on');
  setTimeout(function(){ $('sq').focus(); $('sq').select(); },50);
}
function closeSearch(){ $('msearch').classList.remove('on'); }
var searchTimer;
function debouncedSearch(){ clearTimeout(searchTimer); searchTimer=setTimeout(doSearch,300); }
async function doSearch(){
  var q=$('sq').value.trim(); if(q.length<2){$('sresults').innerHTML='<div class="s-empty">Tapez au moins 2 caractères</div>';return;}
  $('sresults').innerHTML='<div class="s-empty"><span class="sp"></span>Recherche…</div>';
  var d=await fetch('/api/search?q='+eu(q)).then(function(r){return r.json();});
  if(d.error){$('sresults').innerHTML='<div class="s-empty">⚠ '+esc(d.error)+'</div>';return;}
  var res=d.results||[];
  var building=d.index&&d.index.state==='construction'
    ?'<div class="s-empty">Index en construction ('+d.index.progress.done+' / '+d.index.progress.total+') : résultats partiels.</div>':'';
  if(!res.length){$('sresults').innerHTML=building+'<div class="s-empty">Aucun résultat pour « '+esc(q)+' »</div>';return;}
  $('sresults').innerHTML=building+res.map(function(r){
    var matches=r.matches.map(function(m){
      // le serveur encadre les termes trouvés par \x01 … \x02 (insensible aux accents)
      var mark=function(t){ return esc(t).replace(/\x01/g,'<mark>').replace(/\x02/g,'</mark>'); };
      var text=mark(m.text);
      var head=m.heading?'<span class="sr-head">'+mark(m.heading)+'</span> ':'';
      return '<div class="sr-match">'+head+text+'</div>';
    }).join('');
    return '<div class="sr-item" onclick="openResult(\''+eu(r.path)+'\')">'
      +'<div class="sr-name">📄 '+esc(r.name)+'</div>'
      +'<div class="sr-rel">'+esc(r.rel)+'</div>'
      +matches+'</div>';
  }).join('');
}
async function openResult(encoded){
  var path=decodeURIComponent(encoded);
  var d=await fetch('/api/files/read?path='+eu(path)).then(function(r){return r.json();});
  if(d.error){toast('⚠ '+d.error);return;}
  openFileTab(path,d.content); closeSearch();
}

