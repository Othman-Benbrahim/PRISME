// ══════════════════════════════════════════════════
//  RECHERCHE DANS LA NOTE OUVERTE (Ctrl+F)
// ══════════════════════════════════════════════════
// Insensible aux accents et à la casse, comme la recherche globale : ouvrir un
// résultat de recherche surligne donc le passage dans le texte lui-même.
var FIND = {query: '', hits: [], cur: 0};

function findNormalize(text){
  // Renvoie [texte normalisé, table de correspondance vers les positions d'origine]
  var out = '', map = [];
  for(var i = 0; i < text.length; i++){
    var n = text[i].normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    for(var j = 0; j < n.length; j++){ out += n[j]; map.push(i); }
  }
  map.push(text.length);
  return [out, map];
}

function findAll(text, query){
  var q = query.trim();
  if(q.length < 2) return [];
  var norm = findNormalize(text), needle = findNormalize(q)[0];
  var hits = [], from = 0, idx;
  while((idx = norm[0].indexOf(needle, from)) !== -1 && hits.length < 500){
    hits.push({start: norm[1][idx], end: norm[1][idx + needle.length]});
    from = idx + needle.length;
  }
  return hits;
}

function openFind(query){
  if(!ACTIVE){ toast('Ouvrez un fichier d\'abord'); return; }
  $('find-bar').classList.add('on');
  if(query !== undefined) $('find-q').value = query;
  $('find-q').focus();
  $('find-q').select();
  findRun();
}

function closeFind(){
  $('find-bar').classList.remove('on');
  FIND = {query: '', hits: [], cur: 0};
  findClearPreview();
  $('md-editor').focus();
}

function findRun(reset){
  var q = $('find-q').value;
  FIND.query = q;
  FIND.hits = findAll($('md-editor').value, q);
  if(reset !== false) FIND.cur = 0;
  $('find-count').textContent = q.length < 2 ? '' : (FIND.hits.length ? (FIND.cur + 1) + ' / ' + FIND.hits.length : 'aucun');
  if(FIND.hits.length) findGo(0, true); else findClearPreview();
}

function findGo(delta, absolute){
  if(!FIND.hits.length) return;
  FIND.cur = absolute ? FIND.cur : (FIND.cur + delta + FIND.hits.length) % FIND.hits.length;
  $('find-count').textContent = (FIND.cur + 1) + ' / ' + FIND.hits.length;
  var hit = FIND.hits[FIND.cur];
  if(EDITOR_MODE !== 'preview'){
    var ed = $('md-editor');
    ed.focus();
    ed.setSelectionRange(hit.start, hit.end);
    scrollEditorTo(hit.start);
    gutterPosition();
  }
  if(EDITOR_MODE !== 'edit') findMarkPreview();
}

// Aperçu : on surligne dans le HTML rendu, sans toucher au Markdown source
function findClearPreview(){
  var pv = $('md-preview');
  if(!pv) return;
  pv.querySelectorAll('mark.fh').forEach(function(m){
    var parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
}

function findMarkPreview(){
  findClearPreview();
  var q = FIND.query;
  if(q.trim().length < 2) return;
  var pv = $('md-preview'), needle = findNormalize(q)[0], n = 0, current = null;
  var walker = document.createTreeWalker(pv, NodeFilter.SHOW_TEXT);
  var targets = [];
  while(walker.nextNode()){
    var node = walker.currentNode;
    if(node.nodeValue.trim()) targets.push(node);
  }
  targets.forEach(function(node){
    var norm = findNormalize(node.nodeValue), from = 0, idx, pieces = [];
    var last = 0;
    while((idx = norm[0].indexOf(needle, from)) !== -1){
      var s = norm[1][idx], e = norm[1][idx + needle.length];
      pieces.push(document.createTextNode(node.nodeValue.slice(last, s)));
      var mark = document.createElement('mark');
      mark.className = 'fh';
      mark.textContent = node.nodeValue.slice(s, e);
      if(n === FIND.cur){ mark.classList.add('cur'); current = mark; }
      n++;
      pieces.push(mark);
      last = e;
      from = idx + needle.length;
    }
    if(pieces.length){
      pieces.push(document.createTextNode(node.nodeValue.slice(last)));
      var frag = document.createDocumentFragment();
      pieces.forEach(function(p){ frag.appendChild(p); });
      node.parentNode.replaceChild(frag, node);
    }
  });
  if(current) current.scrollIntoView({block: 'center'});
}

document.addEventListener('keydown', function(e){
  if((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f' && !e.shiftKey){
    e.preventDefault();
    var ed = $('md-editor');
    var sel = ed.value.slice(ed.selectionStart, ed.selectionEnd);
    openFind(sel && sel.length < 60 ? sel : undefined);
  } else if(e.key === 'Escape' && $('find-bar').classList.contains('on')){
    closeFind();
  } else if(e.key === 'F3'){
    e.preventDefault();
    findGo(e.shiftKey ? -1 : 1);
  }
});
