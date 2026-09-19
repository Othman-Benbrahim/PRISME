// ══════════════════════════════════════════════════
//  EMBEDDINGS LOCAUX (ONNX)
// ══════════════════════════════════════════════════
// Le modèle tourne sur la machine : ce panneau sert à le poser, le vérifier et
// l'essayer. Il ne décide de rien — c'est Paramètres → Recherche sémantique qui
// choisit le fournisseur.
var EMBLOC = {etat: null, timer: null};
var EMBLOC_API = '/api/plugins/embeddings-locaux';

// Un modèle de 4 Ko affiché « 0 Mo » donne l'impression que rien n'est là.
function emblocTaille(octets){
  if(octets >= 1e6) return Math.round(octets / 1e6) + ' Mo';
  if(octets >= 1e3) return Math.round(octets / 1e3) + ' Ko';
  return octets + ' o';
}

function emblocOuvrir(){
  $('membloc').classList.add('on');
  emblocCharger();
}
function emblocFermer(){
  clearTimeout(EMBLOC.timer);
  $('membloc').classList.remove('on');
}

async function emblocCharger(){
  clearTimeout(EMBLOC.timer);
  var d = await fetch(EMBLOC_API + '/etat').then(function(r){ return r.json(); });
  EMBLOC.etat = d;

  var deps = $('embloc-deps');
  deps.className = 'embloc-etat ' + (d.dependances_ok ? 'ok' : 'ko');
  deps.innerHTML = d.dependances_ok
    ? '● onnxruntime et tokenizers sont installés.'
    : '⚠ ' + esc(d.dependances);

  var m = d.modele || {};
  var e = $('embloc-modele');
  if(m.present){
    e.className = 'embloc-etat ok';
    e.innerHTML = '● Modèle en place — ' + emblocTaille(m.taille || 0)
      + (m.dimension_annoncee ? ' · ' + m.dimension_annoncee + ' dimensions' : '')
      + (m.architecture ? ' · ' + esc(m.architecture) : '')
      + '<br><code>' + esc(m.dossier) + '</code>'
      + '<br>empreinte <code>' + esc((m.sha256 || '').slice(0, 24)) + '…</code>';
  } else {
    e.className = 'embloc-etat ko';
    e.innerHTML = '○ Modèle incomplet — manquant(s) : ' + esc((m.manquants || []).join(', '))
      + '<br><code>' + esc(m.dossier || '') + '</code>';
  }

  var r = d.reglages || {};
  $('embloc-dossier').value = r.dossier || '';
  $('embloc-prefixes').checked = r.prefixes !== false;
  $('embloc-fils').value = r.fils || '';
  var cat = d.catalogue || {};
  var noms = Object.keys(cat);
  $('embloc-catalogue').innerHTML = noms.map(function(k){
    return '<option value="' + esc(k) + '">' + esc(cat[k].libelle) + '</option>';
  }).join('');
  if(noms.length) $('embloc-catalogue').value = noms[0];   // le plus léger par défaut

  emblocProgres(d.telechargement || {});
  if((d.telechargement || {}).en_cours) EMBLOC.timer = setTimeout(emblocCharger, 700);
}

function emblocProgres(t){
  var p = $('embloc-progres');
  if(t.en_cours){
    p.style.display = '';
    p.className = 'embloc-etat neutre';
    var pct = t.total ? Math.round(t.faits * 100 / t.total) : 0;
    p.textContent = '⏳ ' + (t.fichier || '') + ' — ' + Math.round(t.faits / 1e6) + ' Mo'
      + (t.total ? ' / ' + Math.round(t.total / 1e6) + ' Mo (' + pct + ' %)' : '');
    $('embloc-installer').disabled = true;
    return;
  }
  $('embloc-installer').disabled = false;
  if(t.erreur){
    p.style.display = ''; p.className = 'embloc-etat ko';
    p.textContent = '⚠ ' + t.erreur;
  } else if(t.fini){
    p.style.display = ''; p.className = 'embloc-etat ok';
    p.textContent = '✓ Téléchargement terminé le ' + t.fini.replace('T', ' ');
  } else {
    p.style.display = 'none';
  }
}

async function emblocEnregistrer(){
  var d = await post(EMBLOC_API + '/reglages', {
    dossier: $('embloc-dossier').value.trim(),
    prefixes: $('embloc-prefixes').checked,
    fils: $('embloc-fils').value || 0});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('✓ Réglages enregistrés');
  emblocCharger();
}

async function emblocInstaller(){
  var nom = $('embloc-catalogue').value;
  if(!await confirmer({titre: 'Télécharger un modèle', ok: 'Télécharger',
      message: 'PRISME va télécharger « ' + nom + ' » depuis un dépôt public, soit plusieurs '
        + 'dizaines de mégaoctets. PRISME ne vérifie pas cette adresse : l\'empreinte du '
        + 'fichier obtenu sera affichée, et vous pourrez l\'épingler. Continuer ?'})) return;
  var d = await post(EMBLOC_API + '/installer', {nom: nom});
  if(d.error){ toast('⚠ ' + d.error, 5000); return; }
  toast('Téléchargement lancé');
  emblocCharger();
}

async function emblocEpingler(){
  var d = await post(EMBLOC_API + '/epingler', {});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('Empreinte épinglée : ' + d.sha256.slice(0, 16) + '…', 4000);
}

async function emblocEssai(){
  var e = $('embloc-essai');
  e.style.display = ''; e.className = 'embloc-etat neutre';
  e.innerHTML = '<span class="sp"></span> Chargement du modèle et essai…';
  var d = await post(EMBLOC_API + '/essai', {});
  if(d.error){ e.className = 'embloc-etat ko'; e.textContent = '⚠ ' + d.error; return; }
  var bon = d.proche > d.lointain + 0.05;
  e.className = 'embloc-etat ' + (bon ? 'ok' : 'ko');
  e.innerHTML = (bon ? '● ' : '⚠ ') + esc(d.verdict)
    + '<br>' + d.dimension + ' dimensions · ' + d.duree_s + ' s'
    + '<br>deux phrases proches : <strong>' + d.proche + '</strong>'
    + ' · deux phrases sans rapport : <strong>' + d.lointain + '</strong>';
}

document.addEventListener('keydown', function(ev){
  if(ev.key === 'Escape' && $('membloc').classList.contains('on')) emblocFermer();
});
