// ══════════════════════════════════════════════════
//  ANNULER / RÉTABLIR (par onglet)
// ══════════════════════════════════════════════════
// L'historique du navigateur est perdu dès qu'on change d'onglet ou de mode :
// PRISME tient le sien, propre à chaque fichier ouvert.
var HIST = {};                  // chemin -> {stack:[{v,s,e}], pos}
var HIST_MAX = 200, HIST_DELAY = 450;
var histTimer = null, histApplying = false;

function histFor(path){
  if(!HIST[path]) HIST[path] = {stack: [], pos: -1};
  return HIST[path];
}

function histBaseline(path, value){
  var h = histFor(path);
  if(!h.stack.length) histPush(path, value, value.length, value.length);
}

function histPush(path, value, selStart, selEnd){
  var h = histFor(path);
  var top = h.stack[h.pos];
  if(top && top.v === value) return;
  h.stack = h.stack.slice(0, h.pos + 1);
  h.stack.push({v: value, s: selStart, e: selEnd});
  if(h.stack.length > HIST_MAX) h.stack.shift();
  h.pos = h.stack.length - 1;
  histButtons();
}

// Saisie au fil de l'eau : on regroupe, sinon chaque lettre ferait un pas
function histOnInput(){
  if(histApplying || !ACTIVE) return;
  var ed = $('md-editor');
  clearTimeout(histTimer);
  histTimer = setTimeout(function(){ histPush(ACTIVE, ed.value, ed.selectionStart, ed.selectionEnd); }, HIST_DELAY);
  histButtons();
}

// Insertion d'un bloc (IA, lien suggéré, collage) : un pas à part entière
function histSnapshot(){
  if(!ACTIVE) return;
  clearTimeout(histTimer);
  var ed = $('md-editor');
  histPush(ACTIVE, ed.value, ed.selectionStart, ed.selectionEnd);
}

function histApply(entry){
  var ed = $('md-editor');
  histApplying = true;
  clearTimeout(histTimer);
  ed.value = entry.v;
  ed.setSelectionRange(entry.s, entry.e);
  onEditorInput();
  gutterRender();
  scrollEditorTo(entry.s);
  ed.focus();
  histApplying = false;
  histButtons();
}

function histUndo(){
  if(!ACTIVE) return;
  var ed = $('md-editor'), h = histFor(ACTIVE);
  clearTimeout(histTimer);
  if(h.pos >= 0 && h.stack[h.pos].v !== ed.value) histPush(ACTIVE, ed.value, ed.selectionStart, ed.selectionEnd);
  if(h.pos <= 0){ toast('Rien à annuler'); return; }
  h.pos--;
  histApply(h.stack[h.pos]);
}

function histRedo(){
  if(!ACTIVE) return;
  var h = histFor(ACTIVE);
  if(h.pos >= h.stack.length - 1){ toast('Rien à rétablir'); return; }
  h.pos++;
  histApply(h.stack[h.pos]);
}

function histButtons(){
  var h = ACTIVE ? histFor(ACTIVE) : {stack: [], pos: -1};
  var pending = ACTIVE && h.stack[h.pos] && h.stack[h.pos].v !== $('md-editor').value;
  $('btn-undo').disabled = !(h.pos > 0 || pending);
  $('btn-redo').disabled = !(h.pos >= 0 && h.pos < h.stack.length - 1);
}

function histForget(path){ delete HIST[path]; }

(function initHistory(){
  var ed = $('md-editor');
  ed.addEventListener('input', histOnInput);
  ed.addEventListener('keydown', function(e){
    if(!(e.ctrlKey || e.metaKey)) return;
    var k = e.key.toLowerCase();
    if(k === 'z' && !e.shiftKey){ e.preventDefault(); histUndo(); }
    else if(k === 'y' || (k === 'z' && e.shiftKey)){ e.preventDefault(); histRedo(); }
  });
})();
