// NEXUS-ARCHÊ — écran Catalogue et vérification de signature.
// Toutes les déclarations globales sont préfixées `arche`.
var ARCHE = {cartes: []};

function archeFermer(){ $('m-nexus-arche').classList.remove('on'); }

async function archeOuvrir(){
  $('m-nexus-arche').classList.add('on');
  if(!ARCHE.cartes.length){
    try{
      var d = await fetch('/api/plugins/nexus-arche/catalogue').then(function(r){ return r.json(); });
      if(d.error) throw new Error(d.error);
      ARCHE.cartes = d.cartes || [];
    }catch(e){ toast('⚠ Catalogue indisponible : ' + e.message); return; }
  }
  archeRendre();
}

// Les noms de cartes sont accentués (RÉSEAU, ÉMERGENCE, PÉRIODICITÉ) et personne ne
// tape les accents dans un champ de filtre. L'index du dépôt les ignore déjà
// (`remove_diacritics`) : le filtre fait pareil, sinon « reseau » ne trouve rien.
function archePlat(t){
  return (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function archeRendre(){
  var q = archePlat($('arche-filtre').value.trim());
  var vues = ARCHE.cartes.filter(function(c){
    return !q || archePlat(c.nom + ' ' + c.mot + ' ' + c.branche_math + ' '
                           + c.registre_rationnel + ' ' + c.registre_symbolique).indexOf(q) >= 0;
  });
  $('arche-compte').textContent = vues.length + ' / ' + ARCHE.cartes.length + ' cartes';
  $('arche-cartes').innerHTML = vues.map(archeCarte).join('') ||
    '<div class="bl-empty">Aucune carte ne correspond.</div>';
}

function archeCarte(c){
  var dist = (c.distinctions || []).map(function(d){
    return '<div class="arche-distinction">— <strong>' + esc(d.autre_nom) + '</strong> : '
      + esc(d.explication) + '<br><span class="arche-critere">' + esc(d.critere) + '</span></div>';
  }).join('');
  return '<div class="arche-carte">'
    + '<div class="arche-titre" onclick="this.nextElementSibling.hidden=!this.nextElementSibling.hidden">'
    +   '<span class="arche-glyphe">' + esc(c.glyphe) + '</span>'
    +   '<span class="arche-nom">' + esc(c.nom) + '</span>'
    +   '<span class="arche-mot">' + esc(c.mot) + '</span>'
    +   '<span class="arche-branche">' + esc(c.branche_math.split('—')[0].trim()) + '</span>'
    + '</div>'
    + '<dl class="arche-corps" hidden>'
    +   '<dt>Rationnel</dt><dd>' + esc(c.registre_rationnel) + '</dd>'
    +   '<dt>Symbolique</dt><dd>' + esc(c.registre_symbolique) + '</dd>'
    +   '<dt>Branche mathématique</dt><dd>' + esc(c.branche_math) + '</dd>'
    +   '<dt>Question IRIS</dt><dd class="arche-iris">' + esc(c.question_iris) + '</dd>'
    +   '<dt>À ne pas confondre avec</dt><dd>' + dist + '</dd>'
    + '</dl></div>';
}

async function archeValider(){
  var chaine = ($('arche-chaine').value || '').trim();
  var e = $('arche-verdict');
  if(!chaine){ e.className = ''; e.textContent = ''; return; }
  try{
    var d = await post('/api/plugins/nexus-arche/valider_signature', {chaine: chaine});
    e.className = d.ok ? 'ok' : 'refus';
    e.textContent = d.ok ? '✓ ' + d.transcription + (d.statut ? ' — ' + d.statut : '')
                         : '✗ ' + d.raison;
  }catch(err){ e.className = 'refus'; e.textContent = '✗ ' + err.message; }
}
