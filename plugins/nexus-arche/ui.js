// NEXUS-ARCHÊ — écran Catalogue et vérification de signature.
// Toutes les déclarations globales sont préfixées `arche`.
var ARCHE = {cartes: [], onglet: 'analyse', derniere: null};

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
  $('arche-archive').hidden = true;
  ARCHE.derniere = null;
  // Le tirage est affiché dès qu'il est fait, avant l'appel au modèle. S'il échoue,
  // les cartes restent à l'écran : elles ne devaient rien à personne, et le protocole
  // d'origine voulait que l'ancrage soit à la charge de l'auteur.
  var entete = '';
  try{
    var imposees = null, positions = {}, nomMode = '';
    if(mode > 0){
      archeMessage('Tirage…');
      var t = await post('/api/plugins/nexus-arche/tirage', {mode: mode});
      if(t.error) throw new Error(t.error);
      imposees = t.cartes.map(function(c){ return c.id; });
      nomMode = t.nom_mode;
      t.cartes.forEach(function(c){ if(c.position) positions[c.id] = c.position; });
      entete = '<p class="arche-avert"><strong>' + esc(t.nom_mode) + '</strong> — '
        + t.cartes.map(function(c){
            return esc(c.glyphe) + ' ' + esc(c.nom) + (c.position ? ' <em>(' + esc(c.position) + ')</em>' : '');
          }).join(' · ') + '<br>' + esc(t.question) + '</p>';
      $('arche-lecture').innerHTML = entete;
    }
    archeMessage('Recherche des ancrages…');
    var d = await post('/api/plugins/nexus-arche/lire',
                       {situation: situation, imposees: imposees, positions: positions});
    if(d.error) throw new Error(d.error);
    archeMessage('');
    $('arche-lecture').innerHTML = entete + archeRendreLecture(d);
    ARCHE.derniere = {situation: situation, mode_nom: nomMode,
                      retenues: d.retenues || [], ecartees: d.ecartees || []};
    $('arche-archive').hidden = !(d.retenues || []).length;
  }catch(e){
    archeMessage(e.message, true);
    if(entete){
      $('arche-lecture').innerHTML = entete + '<p class="arche-avert">Les cartes sont '
        + 'tirées : la lecture assistée a échoué, l\'ancrage vous revient. Cherchez dans '
        + 'la situation un fait que chaque carte nomme — sinon la carte est inactive.</p>';
    }
  }
  finally{ $('arche-lire').disabled = false; }
}

// Le signal est une hypothèse. L'afficher comme un verdict serait exactement ce que le
// protocole interdit — d'où la question affichée avec, et non à la place.
function archeConfigurations(d){
  var html = (d.configurations || []).map(function(s){
    var corps = '<h4>Configuration ' + s.numero + ' — ' + esc(s.nom) + '</h4>'
      + '<p>' + esc(s.signal) + '</p>';
    if(s.fondement) corps += '<p class="arche-fondement">' + esc(s.fondement)
      + (s.statut ? ' <em>(' + esc(s.statut) + ')</em>' : '') + '</p>';
    (s.paires || []).forEach(function(p){
      corps += '<p class="arche-fondement">' + esc(p.cartes.join(' ↮ ')) + ' — ' + esc(p.fondement) + '</p>';
    });
    if(s.fragile) corps += '<p class="arche-avert">' + esc(s.fragile) + '</p>';
    corps += '<p class="arche-avert">' + esc(s.lecture) + '</p>'
      + '<p class="arche-question"><strong>À trancher :</strong> ' + esc(s.question) + '</p>';
    return '<div class="arche-config">' + corps + '</div>';
  }).join('');
  if((d.positions_inactives || []).length){
    html += '<p class="arche-avert">Position sans carte active : '
      + esc(d.positions_inactives.join(', '))
      + ' — aucune configuration ne peut être prononcée dessus.</p>';
  }
  return html;
}

async function archeArchiver(){
  if(!ARCHE.derniere){ archeMessage('Aucune lecture à archiver.', true); return; }
  $('arche-ecrire').disabled = true;
  try{
    var charge = Object.assign({}, ARCHE.derniere, {
      format: $('arche-format').value,
      statut: $('arche-statut').value,
      signature: ($('arche-signature').value || '').trim()});
    var d = await post('/api/plugins/nexus-arche/fiche', charge);
    if(d.error) throw new Error(d.error);
    archeMessage('Fiche écrite : ' + d.chemin);
    if(typeof loadDir === 'function' && typeof CUR_DIR !== 'undefined') loadDir(CUR_DIR);
  }catch(e){ archeMessage(e.message, true); }
  finally{ $('arche-ecrire').disabled = false; }
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

  html += archeConfigurations(d);

  if((d.distinctions || []).length){
    html += '<div class="arche-questions"><strong>À trancher vous-même :</strong><ul>'
      + d.distinctions.map(function(q){ return '<li>' + esc(q.critere) + '</li>'; }).join('')
      + '</ul></div>';
  }
  if(d.avertissement) html += '<p class="arche-avert">' + esc(d.avertissement) + '</p>';
  if(!html) html = '<p class="arche-avert">Aucune carte proposée.</p>';
  return html;
}
