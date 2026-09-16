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
  var d=await fetch('/api/search?q='+eu(q)+'&dir='+eu(CUR_DIR)).then(function(r){return r.json();});
  var res=d.results||[];
  if(!res.length){$('sresults').innerHTML='<div class="s-empty">Aucun résultat pour « '+esc(q)+' »</div>';return;}
  var re=new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');
  $('sresults').innerHTML=res.map(function(r){
    var matches=r.matches.map(function(m){
      return '<div class="sr-match">'+esc(m.text).replace(re,function(s){return '<mark>'+s+'</mark>';})+'</div>';
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

