// ══════════════════════════════════════════════════
//  NUMÉROS DE LIGNE + POSITION DU CURSEUR
// ══════════════════════════════════════════════════
// La gouttière reproduit le texte, invisible, avec le même retour à la ligne :
// chaque numéro reste donc aligné même sur une ligne qui s'enroule.
var GUTTER_MAX_LINES = 6000;     // au-delà, on renonce plutôt que de figer l'éditeur
var gutterTimer = null, GUTTER_TOPS = [];

function gutterSchedule(){ clearTimeout(gutterTimer); gutterTimer = setTimeout(gutterRender, 80); }

function gutterRender(){
  var ed = $('md-editor'), inner = $('md-gutter-inner'), box = $('md-gutter');
  if(!ed || !inner) return;
  if(ed.style.display === 'none' || !ACTIVE){ box.style.display='none'; return; }
  var lines = ed.value.split('\n');
  if(lines.length > GUTTER_MAX_LINES){
    box.style.display = 'none';
    inner.innerHTML = '';
    GUTTER_TOPS = [];
    return;
  }
  box.style.display = 'block';
  var style = getComputedStyle(ed);
  inner.style.width = (ed.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)) + 'px';
  inner.style.paddingTop = style.paddingTop;
  inner.style.font = style.font;
  inner.style.lineHeight = style.lineHeight;
  inner.innerHTML = lines.map(function(l, i){
    return '<div class="gl"><span class="gn">' + (i + 1) + '</span>' + esc(l || ' ') + '</div>';
  }).join('');
  GUTTER_TOPS = Array.prototype.map.call(inner.children, function(el){ return el.offsetTop; });
  gutterSync();
  gutterPosition();
}

function gutterSync(){
  var inner = $('md-gutter-inner');
  if(inner) inner.style.transform = 'translateY(' + (-$('md-editor').scrollTop) + 'px)';
}

// Ligne / colonne, façon Notepad++
function gutterPosition(){
  var ed = $('md-editor'), el = $('ed-pos');
  if(!ed || !el) return;
  if(!ACTIVE){ el.textContent = ''; return; }
  var before = ed.value.slice(0, ed.selectionStart);
  var line = before.split('\n').length;
  var col = before.length - before.lastIndexOf('\n');
  var total = ed.value.split('\n').length;
  var sel = ed.selectionEnd - ed.selectionStart;
  el.textContent = 'Ligne ' + line + ', col ' + col + ' · ' + total + ' ligne(s)'
    + (sel ? ' · ' + sel + ' caractère(s) sélectionné(s)' : '');
  var cur = $('md-gutter-inner') ? $('md-gutter-inner').children[line - 1] : null;
  Array.prototype.forEach.call($('md-gutter-inner').children, function(c){ c.classList.remove('cur'); });
  if(cur) cur.classList.add('cur');
}

// Fait défiler l'éditeur jusqu'à une position dans le texte
function scrollEditorTo(charIndex){
  var ed = $('md-editor');
  var line = ed.value.slice(0, charIndex).split('\n').length - 1;
  var top = GUTTER_TOPS.length > line ? GUTTER_TOPS[line]
    : ed.scrollHeight * (line / Math.max(1, ed.value.split('\n').length));
  ed.scrollTop = Math.max(0, top - ed.clientHeight / 3);
  gutterSync();
}

(function initGutter(){
  var ed = $('md-editor');
  ed.addEventListener('scroll', gutterSync);
  ed.addEventListener('input', gutterSchedule);
  ['click', 'keyup', 'select'].forEach(function(ev){ ed.addEventListener(ev, gutterPosition); });
  window.addEventListener('resize', gutterSchedule);
})();
