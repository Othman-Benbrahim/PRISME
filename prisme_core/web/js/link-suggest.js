// ══════════════════════════════════════════════════
//  SUGGESTIONS DE LIENS (onglet « Liens » du panneau droit)
// ══════════════════════════════════════════════════
// L'IA propose, l'utilisateur insère ou ignore chaque lien. Les propositions
// vers une note inexistante ou sur un passage introuvable sont écartées.
var LINKS = {path: null, items: [], busy: false};

function linksOnSwitch(path){
  if(LINKS.path && LINKS.path !== path){
    LINKS = {path: null, items: [], busy: false};
    $('lk-list').innerHTML = '<div class="bl-empty">Cliquez sur « Analyser » pour cette note.</div>';
    linksStatus('');
  }
  $('lk-title').textContent = path ? 'Liens pour ' + path.split(/[/\\]/).pop() : 'Liens suggérés';
}

function linksStatus(msg){
  var el = $('lk-status');
  el.textContent = msg || '';
  el.classList.toggle('on', !!msg);
}

function linksShowPanel(){
  if(!MM_VISIBLE) toggleMM();
  switchMMTab(2);
}

// Position du passage dans le texte, hors des [[wikilinks]] existants
function linksFind(text, passage){
  var from = 0, idx;
  while((idx = text.indexOf(passage, from)) !== -1){
    var open = text.lastIndexOf('[[', idx), close = text.lastIndexOf(']]', idx);
    var insideLink = open !== -1 && open > close && text.indexOf(']]', idx) !== -1;
    if(!insideLink) return idx;
    from = idx + passage.length;
  }
  return -1;
}

function linksValidate(raw, names, text, current){
  var byLower = {};
  names.forEach(function(n){ byLower[n.toLowerCase()] = n; });
  var kept = [], seen = {}, rejected = 0;
  (raw || []).forEach(function(s){
    var passage = String(s.passage || '').trim();
    var link = String(s.link || '').replace(/^\[\[|\]\]$/g, '').replace(/\.md$/i, '').trim();
    var target = byLower[link.toLowerCase()];
    var ok = target && target.toLowerCase() !== current.toLowerCase()
      && passage.length >= 3 && passage.indexOf('\n') === -1
      && passage.indexOf('[[') === -1 && passage.indexOf(']]') === -1
      && !seen[passage] && linksFind(text, passage) !== -1;
    if(!ok){ rejected++; return; }
    seen[passage] = true;
    kept.push({passage: passage, link: target, reason: String(s.reason || ''), done: false});
  });
  return {kept: kept, rejected: rejected};
}

async function suggestLinks(){
  if(!ACTIVE){ toast('Ouvrez un fichier d\'abord'); return; }
  linksShowPanel();
  if(LINKS.busy) return;
  var path = ACTIVE;
  var content = $('md-editor').value;
  var name = path.split(/[/\\]/).pop().replace(/\.md$/i, '');
  LINKS = {path: path, items: [], busy: true};
  $('lk-run').disabled = true;
  $('lk-list').innerHTML = '<div class="bl-empty"><span class="sp"></span>Analyse en cours…</div>';
  linksStatus('');
  try{
    var graph = await fetch('/api/files/graph').then(function(r){ return r.json(); });
    var names = (graph.nodes || []).map(function(n){ return n.name; })
      .filter(function(n){ return n.toLowerCase() !== name.toLowerCase(); });
    if(!names.length){
      $('lk-list').innerHTML = '<div class="bl-empty">Aucune autre note dans le vault : rien à relier.</div>';
      return;
    }
    var r = await post('/api/ai', {nostream: true, messages: [
      {role: 'system', content: 'Tu es expert en gestion de connaissances personnelles. '
        + 'Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour.'},
      {role: 'user', content: 'Note actuelle : "' + name + '"\n'
        + 'Notes existantes (seules cibles autorisées) : ' + names.slice(0, 150).join(' | ') + '\n\n'
        + 'Contenu de la note actuelle :\n' + content.slice(0, 6000) + '\n\n'
        + 'Propose au plus 5 liens [[wikilink]] entre un passage de la note actuelle et une note existante.\n'
        + 'Règles :\n'
        + '- "passage" : 2 à 8 mots copiés EXACTEMENT depuis la note, sur une seule ligne, hors de tout [[lien]] existant.\n'
        + '- "link" : un nom pris tel quel dans la liste des notes existantes.\n'
        + '- Ne propose un lien que si le rapport de sens est réel. Une liste vide est une bonne réponse.\n'
        + 'Format : {"suggestions":[{"passage":"…","link":"…","reason":"…"}]}'}
    ]});
    if(LINKS.path !== path) return;                        // l'utilisateur a changé de note
    if(r.error){ $('lk-list').innerHTML = ''; linksStatus('⚠ ' + r.error); return; }
    var parsed;
    try{
      var jt = r.response || '', jm = jt.match(/\{[\s\S]*\}/);
      parsed = JSON.parse(jm ? jm[0] : jt);
    }catch(e){
      $('lk-list').innerHTML = '';
      linksStatus('⚠ Réponse illisible du modèle : ' + String(r.response || '').slice(0, 120));
      return;
    }
    var v = linksValidate(parsed.suggestions, names, $('md-editor').value, name);
    LINKS.items = v.kept;
    linksStatus(v.rejected ? v.rejected + ' proposition(s) écartée(s) : note inexistante, passage introuvable ou déjà lié.' : '');
    linksRender();
  } finally {
    if(LINKS.path === path) LINKS.busy = false;
    $('lk-run').disabled = false;
  }
}

function linksRender(){
  if(!LINKS.items.length){
    $('lk-list').innerHTML = '<div class="bl-empty">Aucun lien pertinent proposé pour cette note.</div>';
    return;
  }
  $('lk-list').innerHTML = LINKS.items.map(function(s, i){
    return '<div class="lk-item' + (s.done ? ' done' : '') + '">'
      + '<div class="lk-target">[[' + esc(s.link) + ']]</div>'
      + '<div class="lk-passage">« ' + esc(s.passage) + ' »</div>'
      + (s.reason ? '<div class="lk-reason">' + esc(s.reason) + '</div>' : '')
      + (s.done ? '<div class="lk-reason">' + esc(s.done) + '</div>'
        : '<div class="lk-actions">'
          + '<button class="lk-insert" onclick="linksInsert(' + i + ')">Insérer</button>'
          + '<button onclick="linksLocate(' + i + ')">Voir</button>'
          + '<button onclick="linksDismiss(' + i + ')">Ignorer</button>'
          + '</div>')
      + '</div>';
  }).join('');
}

function linksCheckFile(){
  if(ACTIVE !== LINKS.path){ toast('Cette suggestion concerne une autre note'); return false; }
  if(EDITOR_MODE === 'preview') setMode('edit');
  return true;
}

function linksLocate(i){
  var s = LINKS.items[i]; if(!s || !linksCheckFile()) return;
  var ed = $('md-editor'), idx = linksFind(ed.value, s.passage);
  if(idx === -1){ toast('Passage introuvable : la note a changé'); return; }
  ed.focus(); ed.setSelectionRange(idx, idx + s.passage.length);
}

function linksInsert(i){
  var s = LINKS.items[i]; if(!s || !linksCheckFile()) return;
  var ed = $('md-editor'), text = ed.value, idx = linksFind(text, s.passage);
  if(idx === -1){ toast('Passage introuvable : la note a changé'); return; }
  // Texte simple : le passage devient l'alias du lien. Sinon, le lien est ajouté après.
  var plain = !/[\[\]`*_#|<>]/.test(s.passage);
  var repl = plain ? '[[' + s.link + '|' + s.passage + ']]' : s.passage + ' [[' + s.link + ']]';
  histSnapshot();
  ed.value = text.slice(0, idx) + repl + text.slice(idx + s.passage.length);
  ed.focus(); ed.setSelectionRange(idx, idx + repl.length);
  onEditorInput();
  histSnapshot();
  s.done = 'Inséré — Ctrl+S pour enregistrer';
  linksRender();
}

function linksDismiss(i){
  var s = LINKS.items[i]; if(!s) return;
  s.done = 'Ignoré';
  linksRender();
}
