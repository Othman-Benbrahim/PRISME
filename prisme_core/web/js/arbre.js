// ══════════════════════════════════════════════════
//  RECHERCHE EN ARBRE  (E13, décision 0029)
//
//  Deux temps, jamais un seul : on construit l'arbre et on le MONTRE, l'auteur
//  élague, et seulement ensuite le modèle parle. C'est la règle de 0017 appliquée
//  au contexte — l'IA propose ce qu'elle veut lire, l'auteur valide.
// ══════════════════════════════════════════════════
var ARB = null;            // dernier arbre construit
var ARB_CHOISIS = null;    // Set des chemins cochés

function openArbre(question){
  $('marbre').classList.add('on');
  if(question) $('arb-q').value = question;
  else if(!$('arb-q').value && ACTIVE) $('arb-depart').checked = true;
  arbMajDepart();
  setTimeout(function(){ $('arb-q').focus(); }, 50);
}
function closeArbre(){ $('marbre').classList.remove('on'); }

// La case « partir de la note ouverte » n'a de sens que s'il y en a une.
function arbMajDepart(){
  var c = $('arb-depart'), l = $('arb-depart-l');
  if(!c) return;
  if(ACTIVE){ l.style.display=''; l.title = ACTIVE; }
  else { c.checked = false; l.style.display = 'none'; }
}

function arbNombre(id, defaut){
  var v = parseInt($(id).value, 10);
  return (isNaN(v) || v <= 0) ? defaut : v;
}

async function arbConstruire(){
  var q = $('arb-q').value.trim();
  var depart = ($('arb-depart') && $('arb-depart').checked && ACTIVE) ? ACTIVE : '';
  if(!q && !depart){ toast('Donnez une question, ou partez de la note ouverte'); return; }
  $('arb-liste').innerHTML = '<div class="s-empty"><span class="sp"></span>Propagation…</div>';
  $('arb-reponse').style.display = 'none';
  $('arb-mesure').style.display = 'none';
  var d = await post('/api/arbre/construire', {
    question: q, depart: depart,
    profondeur: arbNombre('arb-prof', 2),
    budget: arbNombre('arb-budget-max', 40000),
    comparer: !!(q && $('arb-mesurer').checked)
  });
  if(d.error){ $('arb-liste').innerHTML = '<div class="s-empty">⚠ '+esc(d.error)+'</div>'; return; }
  ARB = d;
  // La sélection initiale est celle du budget ; décocher ne change QUE l'affichage
  // et l'envoi, jamais l'arbre lui-même — on doit pouvoir recocher.
  ARB_CHOISIS = {};
  (d.retenus || []).forEach(function(c){ ARB_CHOISIS[c] = true; });
  arbRendre();
  arbRendreMesure(d.comparaison);
}

function arbRendre(){
  if(!ARB){ return; }
  var n = ARB.noeuds || [];
  if(!n.length){
    $('arb-liste').innerHTML = '<div class="s-empty">Rien trouvé : ni pertinence, ni lien.</div>';
    $('arb-budget').style.display = 'none';
    return;
  }
  $('arb-liste').innerHTML = n.map(function(x, i){
    var coche = ARB_CHOISIS[x.chemin] ? ' checked' : '';
    var cout = Math.min(x.taille, 6000);
    // Le motif porte la flèche telle que le serveur l'a écrite : « → Methode » veut
    // dire « ce nœud est cité par Methode », pas l'inverse. On ne la reformule pas ici.
    return '<div class="arb-n'+(coche?'':' off')+'" id="arbn'+i+'">'
      + '<input type="checkbox" onchange="arbBasculer('+i+')"'+coche+'>'
      + '<span class="arb-niv">n'+x.niveau+'</span>'
      + '<div class="arb-corps">'
      +   '<div class="arb-nom" onclick="arbOuvrir(\''+eu(x.chemin)+'\')">'+esc(x.nom)+'</div>'
      // Une amorce a pour motif « pertinence » : y ajouter « · pertinence 0.50 »
      // écrivait le mot deux fois. Le chiffre seul suffit.
      +   '<div class="arb-motif"><span class="lien">'+esc(x.motif)+'</span>'
      +     (x.pertinence > 0 ? ' · '+x.pertinence.toFixed(2) : '')
      +   '</div>'
      + '</div>'
      + '<span class="arb-cout">'+arbK(cout)+'</span>'
      + '</div>';
  }).join('');
  arbMajBudget();
}

function arbK(n){ return n >= 1000 ? (n/1000).toFixed(1)+' k' : n+' c'; }

function arbBasculer(i){
  var x = ARB.noeuds[i];
  if(ARB_CHOISIS[x.chemin]) delete ARB_CHOISIS[x.chemin];
  else ARB_CHOISIS[x.chemin] = true;
  var e = $('arbn'+i);
  if(e) e.classList.toggle('off', !ARB_CHOISIS[x.chemin]);
  arbMajBudget();
}

// Le compteur doit bouger à chaque case : sans retour immédiat, l'élagage se fait
// à l'aveugle et on ne sait jamais ce qu'on vient d'économiser.
function arbMajBudget(){
  var total = 0, nb = 0;
  (ARB.noeuds || []).forEach(function(x){
    if(ARB_CHOISIS[x.chemin]){ total += Math.min(x.taille, 6000); nb++; }
  });
  var max = ARB.budget || 40000;
  var pc = Math.min(100, Math.round(total * 100 / max));
  $('arb-budget').style.display = 'flex';
  $('arb-jauge').classList.toggle('plein', total > max);
  $('arb-jauge').firstChild.style.width = pc + '%';
  $('arb-cpt').textContent = nb + ' note' + (nb>1?'s':'') + ' · ' + arbK(total)
    + ' / ' + arbK(max) + (total > max ? ' — dépassement' : '');
  $('arb-repondre').disabled = (nb === 0);
}

function arbToutCocher(v){
  ARB_CHOISIS = {};
  if(v) (ARB.noeuds || []).forEach(function(x){ ARB_CHOISIS[x.chemin] = true; });
  arbRendre();
}

async function arbOuvrir(encoded){
  var path = decodeURIComponent(encoded);
  var d = await fetch('/api/files/read?path='+eu(path)).then(function(r){ return r.json(); });
  if(d.error){ toast('⚠ '+d.error); return; }
  openFileTab(path, d.content);
  closeArbre();
}

// La mesure est affichée telle quelle, y compris quand elle dessert l'arbre : c'est
// l'exigence de la décision 0029 (« à mesurer, pas à supposer »).
function arbRendreMesure(c){
  var e = $('arb-mesure');
  if(!c){ e.style.display = 'none'; return; }
  var signe = c.gain_a_budget_egal >= 0 ? '−' : '+';
  e.style.display = 'block';
  e.innerHTML =
      'Recherche plate : <b>'+c.plat_notes+'</b> notes, '+arbK(c.plat_caracteres)+'. '
    + 'Tronquée au même budget : <b>'+c.plat_tronque_notes+'</b> notes, '
    + arbK(c.plat_tronque_caracteres)+'. Arbre : <b>'+c.arbre_notes+'</b> notes, '
    + arbK(c.arbre_caracteres)+'.<br>'
    + 'À budget égal l\'arbre coûte <b>'+signe+arbK(Math.abs(c.gain_a_budget_egal))+'</b> '
    + '(dont '+arbK(c.carte_caracteres)+' de carte). Ce qu\'il apporte : <b>'+c.apport_liens+'</b> '
    + 'note'+(c.apport_liens>1?'s':'')+' qu\'aucun score n\'avait remontée'
    + (c.apport_liens>1?'s':'')+', atteinte'+(c.apport_liens>1?'s':'')+' par les liens.';
}

async function arbRepondre(){
  var q = $('arb-q').value.trim();
  if(!q){ toast('La réponse a besoin d\'une question'); return; }
  var retenus = Object.keys(ARB_CHOISIS);
  if(!retenus.length){ toast('Cochez au moins une note'); return; }
  $('arb-repondre').disabled = true;
  $('arb-reponse').style.display = 'block';
  $('arb-reponse').innerHTML = '<div class="s-empty"><span class="sp"></span>Lecture des '
    + retenus.length + ' notes retenues…</div>';
  var d = await post('/api/arbre/repondre', {question: q, arbre: ARB, retenus: retenus});
  $('arb-repondre').disabled = false;
  if(d.error){ $('arb-reponse').innerHTML = '<div class="s-empty">⚠ '+esc(d.error)+'</div>'; return; }
  var rendu = (window.marked && marked.parse) ? marked.parse(d.reponse || '') : esc(d.reponse || '');
  $('arb-reponse').innerHTML = '<div class="rep">'+rendu+'</div>'
    + '<div id="arb-envoye">'+arbK(d.caracteres_envoyes)+' envoyés, '
    + (d.notes||[]).length+' notes — '
    + (d.notes||[]).map(function(n){ return esc(n.nom); }).join(', ') + '</div>';
}
