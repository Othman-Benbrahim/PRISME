// ══════════════════════════════════════════════════
//  ENGRAM — IMPORT DE SOURCES
// ══════════════════════════════════════════════════
// Le fichier reste sur votre machine : on donne son chemin, PRISME le lit.
// Pas d'envoi par le navigateur, donc pas de limite de taille.
var ENG = {inspection: null, formats: [], dossier: ''};

async function openEngram(){
  $('mengram').classList.add('on');
  $('eng-rapport').innerHTML = '';
  var d = await fetch('/api/engram/formats').then(function(r){ return r.json(); });
  ENG.formats = d.formats || [];
  ENG.dossier = d.dossier_notes || '';
  $('eng-formats').textContent = 'Formats lus : ' + ENG.formats.join(', ')
    + ' · au-delà de ' + Math.round((d.seuil_partie || 0) / 1000) + ' 000 caractères, la source est répartie en parties';
  $('eng-dossier').placeholder = ENG.dossier;
  chargerSources();
}
function closeEngram(){ $('mengram').classList.remove('on'); }

async function engInspecter(){
  var chemin = $('eng-chemin').value.trim();
  if(!chemin){ toast('Indiquez le chemin du fichier à importer'); return; }
  $('eng-inspection').innerHTML = '<span class="sp"></span> Vérification…';
  var d = await post('/api/engram/inspect', {chemin: chemin});
  if(d.error){ ENG.inspection = null; $('eng-inspection').innerHTML = '<div class="eng-err">⚠ ' + esc(d.error) + '</div>'; return; }
  ENG.inspection = d;
  var etats = {nouvelle: 'Source nouvelle', modifiee: 'Source déjà importée, et modifiée depuis',
               inchangee: 'Source déjà importée, inchangée'};
  $('eng-inspection').innerHTML =
    '<table class="pv-t">'
    + '<tr><th>Fichier</th><td>' + esc(d.nom) + '</td></tr>'
    + '<tr><th>Taille</th><td>' + (d.taille / 1e6).toFixed(2) + ' Mo</td></tr>'
    + '<tr><th>Extracteur</th><td>' + esc(d.extracteur || 'aucun — format non lu') + '</td></tr>'
    + '<tr><th>Empreinte</th><td>' + esc(d.sha256.slice(0, 24)) + '…</td></tr>'
    + '<tr><th>État</th><td>' + esc(etats[d.etat] || d.etat) + '</td></tr>'
    + '</table>';
  $('eng-importer').disabled = !d.extracteur;
}

async function engImporter(forcer){
  if(!ENG.inspection){ toast('Vérifiez d\'abord le fichier'); return; }
  var corps = {chemin: ENG.inspection.chemin, mode: $('eng-mode').value, forcer: !!forcer};
  var dossier = $('eng-dossier').value.trim();
  if(dossier) corps.dossier = dossier;
  $('eng-rapport').innerHTML = '<span class="sp"></span> Import en cours…';
  var d = await post('/api/engram/import', corps);
  if(d.error){ $('eng-rapport').innerHTML = '<div class="eng-err">⚠ ' + esc(d.error) + '</div>'; return; }
  if(d.etat === 'inchangee'){
    $('eng-rapport').innerHTML = '<div class="eng-ok">' + esc(d.message) + '</div>'
      + '<button class="btn bs" onclick="engImporter(true)">Réimporter quand même</button>'
      + engListeNotes(d.notes);
    return;
  }
  var c = d.comptes || {};
  $('eng-rapport').innerHTML = '<div class="eng-ok">✓ ' + esc(d.titre || '') + ' — '
    + (d.etat === 'nouvelle' ? 'importée' : 'mise à jour') + '</div>'
    + '<div class="eng-comptes">'
    + engPuce('nouveaux', c.nouveau) + engPuce('inchangés', c.inchange) + engPuce('déplacés', c.deplace)
    + engPuce('modifiés', c.modifie) + engPuce('retirés', c.retire, true) + '</div>'
    + (c.retire ? '<div class="eng-note">Les passages retirés sont conservés en fin de note, dans un encadré rouge.</div>' : '')
    + engListeNotes(d.notes);
  loadDir(CUR_DIR);
  chargerSources();
}

function engPuce(label, n, alerte){
  if(!n) return '';
  return '<span class="eng-puce' + (alerte ? ' alerte' : '') + '">' + n + ' ' + label + '</span>';
}
function engListeNotes(liste){
  return '<h4>Notes</h4>' + (liste || []).map(function(f){
    return '<div class="pv-src" onclick="engOuvrir(\'' + eu(f) + '\')">📄 ' + esc(f.split(/[/\\]/).pop()) + '</div>';
  }).join('');
}
async function engOuvrir(encoded){
  var path = decodeURIComponent(encoded);
  var d = await fetch('/api/files/read?path=' + eu(path)).then(function(r){ return r.json(); });
  if(d.error){ toast('⚠ ' + d.error); return; }
  closeEngram();
  openFileTab(path, d.content);
}

async function chargerSources(){
  var d = await fetch('/api/engram/sources').then(function(r){ return r.json(); });
  var liste = d.sources || [];
  $('eng-sources').innerHTML = liste.length ? liste.map(function(s){
    var classe = s.etat === 'intacte' ? '' : (s.etat === 'disparue' ? ' disparue' : ' modifiee');
    return '<div class="eng-src' + classe + '">'
      + '<div class="eng-src-h"><strong>' + esc(s.titre || s.chemin.split(/[/\\]/).pop()) + '</strong>'
      + '<span class="eng-etat">' + esc(s.etat) + '</span></div>'
      + '<div class="pv-muted">' + esc(s.chemin) + '</div>'
      + '<div class="pv-muted">' + esc(s.extracteur) + ' · ' + s.passages + ' passage(s) · '
      + esc((s.importee_le || '').replace('T', ' ')) + ' · ' + esc(s.mode) + '</div>'
      + '<div class="eng-src-a">'
      + '<button class="btn bs" onclick="engReimporter(\'' + eu(s.chemin) + '\',\'' + esc(s.mode) + '\')">Réimporter</button>'
      + '<button class="btn bs" onclick="engOublier(\'' + esc(s.cle) + '\')">Oublier</button>'
      + '</div></div>';
  }).join('') : '<div class="pv-muted">Aucune source importée pour l\'instant.</div>';
}

async function engReimporter(encoded, mode){
  $('eng-chemin').value = decodeURIComponent(encoded);
  $('eng-mode').value = mode || 'reference';
  await engInspecter();
  await engImporter(true);
}

async function engOublier(cle){
  if(!await confirmer({titre:'Oublier une source', ok:'Oublier',
      message:'Retirer cette source du registre ? Les notes déjà créées restent dans le vault, '
        + 'mais un réimport ne saura plus les mettre à jour.'})) return;
  var d = await post('/api/engram/oublier', {cle: cle});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('Source oubliée');
  chargerSources();
}

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && $('mengram').classList.contains('on')) closeEngram();
});
