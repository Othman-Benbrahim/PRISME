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
  vecRendreModeRecherche(d.recherche);
  var building=d.index&&d.index.state==='construction'
    ?'<div class="s-empty">Index en construction ('+d.index.progress.done+' / '+d.index.progress.total+') : résultats partiels.</div>':'';
  if(!res.length){$('sresults').innerHTML=building+'<div class="s-empty">Aucun résultat pour « '+esc(q)+' »</div>';return;}
  $('sresults').innerHTML=building+res.map(function(r){
    var matches=r.matches.map(function(m){
      // le serveur encadre les termes trouvés par \x01 … \x02 (insensible aux accents)
      var mark=function(t){ return esc(t).replace(/\x01/g,'<mark>').replace(/\x02/g,'</mark>'); };
      var text=mark(m.text);
      var head=m.heading?'<span class="sr-head">'+mark(m.heading)+'</span> ':'';
      // Un passage trouvé par le sens seul ne doit pas passer pour une correspondance de mots.
      // Le badge vient AVANT l'extrait : place en fin de ligne, il disparaissait
      // sous la coupure des extraits longs.
      var org=m.origine&&m.origine!=='mots'
        ?'<span class="sr-origine '+(m.origine==='sens'?'sens':'les-deux')+'">'
          +(m.origine==='sens'?'sens':'mots + sens')+'</span> ':'';
      return '<div class="sr-match">'+org+head+text+'</div>';
    }).join('');
    return '<div class="sr-item" onclick="openResult(\''+eu(r.path)+'\',\''+eu(q)+'\')">'
      +'<div class="sr-name">📄 '+esc(r.name)+'</div>'
      +'<div class="sr-rel">'+esc(r.rel)+'</div>'
      +matches+'</div>';
  }).join('');
}
async function openResult(encoded,encodedQuery){
  var path=decodeURIComponent(encoded);
  var query=encodedQuery?decodeURIComponent(encodedQuery):'';
  var d=await fetch('/api/files/read?path='+eu(path)).then(function(r){return r.json();});
  if(d.error){toast('⚠ '+d.error);return;}
  openFileTab(path,d.content); closeSearch();
  if(query) setTimeout(function(){ openFind(query); },120);
}

// Le mode réellement utilisé est affiché à chaque recherche : si les vecteurs manquent
// ou que le service est en panne, on cherche quand même, mais on le dit (décision 0019).
function vecRendreModeRecherche(info){
  var e=$('sr-mode'); if(!e) return;
  if(!info){ e.innerHTML=''; return; }
  if(info.semantique){ e.innerHTML='Recherche par les mots et par le sens'; return; }
  e.innerHTML='Recherche par les mots'
    +(info.repli?' <span class="repli">— sens indisponible : '+esc(info.repli)+'</span>':'');
}
