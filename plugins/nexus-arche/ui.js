// NEXUS-ARCHÊ — écran Catalogue et vérification de signature.
// Toutes les déclarations globales sont préfixées `arche`.
var ARCHE = {cartes: [], onglet: 'analyse'};

function archeFermer(){ $('m-nexus-arche').classList.remove('on'); }

function archeOnglet(nom){
  ARCHE.onglet = nom;
  ['analyse','catalogue'].forEach(function(n){
    $('arche-p-' + n).hidden = (n !== nom);
    $('arche-t-' + n).classList.toggle('arche-t-actif', n === nom);
  });
}

async function archeOuvrir(){
  $('m-nexus-arche').classList.add('on');
  archeOnglet(ARCHE.onglet);
  try{
    var e = await fetch('/api/plugins/nexus-arche/etat').then(function(r){ return r.json(); });
    $('arche-ia').textContent = e.ia_indisponible
      ? '⚠ ' + e.ia_indisponible + ' — le tirage et le catalogue restent utilisables ; '
        + 'l\'ancrage est alors à votre charge.'
      : '';
  }catch(err){ /* l'état est indicatif : son absence ne bloque rien */ }
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


// ══════════════════════════════════════════════════
//  Lecture assistée
// ══════════════════════════════════════════════════
function archeMessage(t, erreur){
  var e = $('arche-etat');
  e.textContent = t || '';
  e.classList.toggle('erreur', !!erreur);
}

async function archeLire(){
  var situation = ($('arche-situation').value || '').trim();
  var mode = parseInt($('arche-mode').value, 10);
  if(situation.length < 40){ archeMessage('Décrivez la situation en quelques phrases.', true); return; }
  $('arche-lire').disabled = true;
  $('arche-lecture').innerHTML = '';
  try{
    var imposees = null, entete = '';
    if(mode > 0){
      archeMessage('Tirage…');
      var t = await post('/api/plugins/nexus-arche/tirage', {mode: mode});
      if(t.error) throw new Error(t.error);
      imposees = t.cartes.map(function(c){ return c.id; });
      entete = '<p class="arche-avert"><strong>' + esc(t.nom_mode) + '</strong> — '
        + t.cartes.map(function(c){
            return esc(c.glyphe) + ' ' + esc(c.nom) + (c.position ? ' <em>(' + esc(c.position) + ')</em>' : '');
          }).join(' · ') + '<br>' + esc(t.question) + '</p>';
    }
    archeMessage('Recherche des ancrages…');
    var d = await post('/api/plugins/nexus-arche/lire', {situation: situation, imposees: imposees});
    if(d.error) throw new Error(d.error);
    archeMessage('');
    $('arche-lecture').innerHTML = entete + archeRendreLecture(d);
  }catch(e){ archeMessage(e.message, true); }
  finally{ $('arche-lire').disabled = false; }
}

function archeRendreLecture(d){
  var html = (d.retenues || []).map(function(c){
    return '<div class="arche-lue"><h4><span class="arche-glyphe">' + esc(c.glyphe) + '</span>'
      + esc(c.nom) + '</h4><dl>'
      + '<dt>Ancrage — citation de votre texte</dt>'
      + '<dd class="arche-ancrage">« ' + esc(c.ancrage) + ' »</dd>'
      + (c.anti_resonance ? '<dt>Anti-résonance — ce qui contredit</dt><dd>' + esc(c.anti_resonance) + '</dd>' : '')
      + '<dt>Question IRIS</dt><dd>' + esc(c.question_iris) + '</dd>'
      + '</dl></div>';
  }).join('');

  html += (d.ecartees || []).map(function(c){
    return '<div class="arche-lue ecartee"><h4>' + esc(c.nom) + ' — <span class="arche-motif">'
      + esc(c.motif) + '</span></h4>'
      + (c.ancrage_refuse ? '<dd class="arche-ancrage">« ' + esc(c.ancrage_refuse) + ' »</dd>' : '')
      + '</div>';
  }).join('');

  if((d.distinctions || []).length){
    html += '<div class="arche-questions"><strong>À trancher vous-même :</strong><ul>'
      + d.distinctions.map(function(q){ return '<li>' + esc(q.critere) + '</li>'; }).join('')
      + '</ul></div>';
  }
  if(d.avertissement) html += '<p class="arche-avert">' + esc(d.avertissement) + '</p>';
  if(!html) html = '<p class="arche-avert">Aucune carte proposée.</p>';
  return html;
}
