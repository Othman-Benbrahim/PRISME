// ══════════════════════════════════════════════════
//  OBJETS — SOURCES CITÉES ET FILE DE VALIDATION
// ══════════════════════════════════════════════════
// Une référence reconnaissable (URL, DOI, arXiv, ISBN) entre directement dans le
// vault, non relue, sous un identifiant de lot annulable. Ce que l'IA croit
// reconnaître sans forme vérifiable attend dans la file : rien n'entre sans accord.
var OBJ = {onglet: 0, sources: [], lots: [], file: [], rejets: {}, fusion: null};

async function openObjets(){
  $('mobjets').classList.add('on');
  objOnglet(OBJ.onglet);
}
function closeObjets(){ $('mobjets').classList.remove('on'); OBJ.fusion = null; }

function objOnglet(i){
  OBJ.onglet = i;
  for(var k = 0; k < 3; k++){
    $('obt' + k).classList.toggle('on', k === i);
    $('obp' + k).style.display = k === i ? '' : 'none';
  }
  if(i === 0) objCharger();
  else objChargerFile();
}

// ── Onglet 1 : les objets Source ────────────────────────────────────────
async function objCharger(){
  var q = [];
  var st = $('obj-statut').value; if(st) q.push('statut=' + st);
  var rl = $('obj-relu').value;   if(rl) q.push('relu=' + rl);
  var d = await fetch('/api/objets/sources' + (q.length ? '?' + q.join('&') : ''))
            .then(function(r){ return r.json(); });
  OBJ.sources = d.sources || [];
  OBJ.lots = d.lots || [];
  $('obj-compte').textContent = OBJ.sources.length + ' objet(s) · dossier ' + (d.dossier || '')
    + ' · ' + (d.en_file || 0) + ' en file · ' + (d.rejets || 0) + ' rejet(s) mémorisé(s)';
  $('obj-lots').innerHTML = OBJ.lots.length ? OBJ.lots.map(function(l){
    return '<span class="obj-lot">' + esc(l.lot) + ' — ' + l.total + ' objet(s), ' + l.non_relus
      + ' non relu(s)'
      + (l.non_relus ? ' <button class="btn bs" onclick="objAnnulerLot(\'' + esc(l.lot)
          + '\')">Annuler ce lot</button>' : '') + '</span>';
  }).join('') : '';
  $('obj-liste').innerHTML = OBJ.sources.length ? OBJ.sources.map(objCarte).join('')
    : '<div class="pv-muted">Aucun objet Source. Lancez un balayage pour recenser les '
      + 'références citées dans vos notes.</div>';
}

function objCarte(o){
  var cites = (o.cite_par || []).map(function(c){
    return '<span class="obj-cite" onclick="objOuvrir(\'' + eu(c) + '\')">' + esc(c) + '</span>';
  }).join('');
  return '<div class="obj-c' + (o.relu ? '' : ' nonrelu') + ' s-' + esc(o.statut) + '">'
    + '<div class="obj-h">'
    + '<strong>' + esc(o.titre) + '</strong>'
    + '<span class="obj-statut">' + esc(o.statut_libelle) + '</span>'
    + (o.relu ? '' : '<span class="obj-marq" title="Entré automatiquement, pas encore relu">non relu</span>')
    + '</div>'
    + '<div class="obj-ref"><code>' + esc(o.reference) + '</code> · ' + esc(o.genre) + '</div>'
    + (o.note_liee ? '<div class="pv-muted">Ingérée : ' + esc(o.note_liee.split(/[/\\]/).pop()) + '</div>' : '')
    + (o.alias && o.alias.length ? '<div class="pv-muted">Fusionnée avec : ' + esc(o.alias.join(', ')) + '</div>' : '')
    + (cites ? '<div class="obj-cites">Citée dans ' + cites + '</div>' : '')
    + '<div class="obj-a">'
    + '<button class="btn bs" onclick="objOuvrir(\'' + eu(o.chemin) + '\')">Ouvrir</button>'
    + (o.relu ? '<button class="btn bs" onclick="objRelu(\'' + eu(o.reference) + '\',false)">Marquer non relu</button>'
              : '<button class="btn bp" onclick="objRelu(\'' + eu(o.reference) + '\',true)">✓ Relu</button>')
    + '<button class="btn bs" onclick="objFusion(\'' + eu(o.reference) + '\')">Fusionner…</button>'
    + '<button class="btn bs" onclick="objSupprimer(\'' + eu(o.reference) + '\')">Retirer</button>'
    + '</div></div>';
}

async function objBalayer(){
  $('obj-rapport').innerHTML = '<span class="sp"></span> Balayage des notes…';
  var corps = {};
  var dos = $('obj-dossier').value.trim(); if(dos) corps.dossier = dos;
  var d = await post('/api/objets/balayer', corps);
  if(d.error){ $('obj-rapport').innerHTML = '<div class="eng-err">⚠ ' + esc(d.error) + '</div>'; return; }
  $('obj-rapport').innerHTML = '<div class="eng-ok">✓ ' + d.notes_lues + ' note(s) lue(s) · '
    + d.references + ' référence(s) · ' + (d.crees || []).length + ' objet(s) créé(s), '
    + (d.completes || []).length + ' complété(s)'
    + ((d.ignores || []).length ? ' · ' + d.ignores.length + ' ignoré(s) (rejet mémorisé)' : '')
    + '</div><div class="pv-muted">Lot ' + esc(d.lot) + ' — annulable tant que rien n\'est relu.</div>';
  objCharger();
  loadDir(CUR_DIR);
}

async function objProposerIA(){
  $('obj-rapport').innerHTML = '<span class="sp"></span> Lecture par l\'IA… (les propositions vont en file)';
  var corps = {};
  var dos = $('obj-dossier').value.trim(); if(dos) corps.dossier = dos;
  var d = await post('/api/objets/ia', corps);
  if(d.error){ $('obj-rapport').innerHTML = '<div class="eng-err">⚠ ' + esc(d.error) + '</div>'; return; }
  $('obj-rapport').innerHTML = '<div class="eng-ok">✓ ' + d.notes_examinees + ' note(s) examinée(s) · '
    + (d.deposees || []).length + ' proposition(s) en file'
    + (d.ecartees ? ' · ' + d.ecartees + ' écartée(s), extrait introuvable dans la note' : '')
    + '</div>';
  if((d.deposees || []).length) toast('Voir l\'onglet « File de validation »');
}

async function objStatuts(){
  var d = await post('/api/objets/statuts', {});
  toast(d.mis_a_jour ? d.mis_a_jour + ' source(s) passée(s) à « ingérée »' : 'Aucun changement');
  objCharger();
}

async function objRelu(encoded, relu){
  var d = await post('/api/objets/relu', {cle: decodeURIComponent(encoded), relu: relu});
  if(d.error){ toast('⚠ ' + d.error); return; }
  objCharger();
}

async function objSupprimer(encoded){
  var cle = decodeURIComponent(encoded);
  var raison = await demanderTexte({titre: 'Retirer cet objet', label: 'Raison (facultative)',
    placeholder: 'pourquoi cette référence ne vous intéresse pas', ok: 'Retirer', libre: true});
  if(raison === null) return;                    // annulé : on ne retire rien
  var d = await post('/api/objets/supprimer', {cle: cle, raison: raison || ''});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('Objet en corbeille, rejet mémorisé');
  objCharger();
}

async function objAnnulerLot(lot){
  if(!await confirmer({titre: 'Annuler un lot', ok: 'Annuler le lot', danger: true,
      message: 'Retirer les objets de ce lot qui n\'ont pas encore été relus ? '
        + 'Ceux que vous avez relus sont conservés. Les notes partent à la corbeille.'})) return;
  var d = await post('/api/objets/lot/annuler', {lot: lot});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast((d.retires || []).length + ' objet(s) retiré(s), ' + (d.conserves || []).length + ' conservé(s)');
  objCharger();
}

function objFusion(encoded){
  OBJ.fusion = decodeURIComponent(encoded);
  $('obj-fusion').style.display = '';
  $('obj-fusion-garde').textContent = OBJ.fusion;
  $('obj-fusion-sel').innerHTML = OBJ.sources.filter(function(o){ return o.reference !== OBJ.fusion; })
    .map(function(o){ return '<option value="' + esc(o.reference) + '">' + esc(o.titre) + '</option>'; }).join('');
}
async function objFusionner(){
  var absorbe = $('obj-fusion-sel').value;
  if(!absorbe || !OBJ.fusion) return;
  var d = await post('/api/objets/file/fusionner',
    {garde: OBJ.fusion, absorbe: absorbe, raison: $('obj-fusion-raison').value.trim()});
  if(d.error){ toast('⚠ ' + d.error); return; }
  $('obj-fusion').style.display = 'none';
  $('obj-fusion-raison').value = '';
  toast('Fusionné — réversible depuis la note de l\'objet');
  objCharger();
}

async function objOuvrir(encoded){
  var path = decodeURIComponent(encoded);
  var d = await fetch('/api/files/read?path=' + eu(path)).then(function(r){ return r.json(); });
  if(d.error){ toast('⚠ ' + d.error); return; }
  closeObjets();
  openFileTab(path, d.content);
}

// ── Onglets 2 et 3 : file de validation et rejets ───────────────────────
async function objChargerFile(){
  var d = await fetch('/api/objets/file').then(function(r){ return r.json(); });
  OBJ.file = d.entrees || [];
  OBJ.rejets = d.rejets || {};
  $('obj-file').innerHTML = OBJ.file.length ? OBJ.file.map(objCarteFile).join('')
    : '<div class="pv-muted">La file est vide. L\'IA y dépose les références qu\'elle croit '
      + 'reconnaître sans URL, DOI ni ISBN : rien n\'entre dans le vault sans votre accord.</div>';
  var cles = Object.keys(OBJ.rejets);
  $('obj-rejets').innerHTML = cles.length ? cles.map(function(c){
    var r = OBJ.rejets[c];
    return '<div class="obj-c"><div class="obj-h"><strong>' + esc(r.titre || c) + '</strong>'
      + '<span class="pv-muted">' + esc((r.rejete_le || '').replace('T', ' ')) + '</span></div>'
      + '<div class="obj-ref"><code>' + esc(c) + '</code></div>'
      + (r.raison ? '<div class="obj-raison">« ' + esc(r.raison) + ' »</div>' : '')
      + '<div class="obj-a"><button class="btn bs" onclick="objOublierRejet(\'' + eu(c)
      + '\')">Oublier ce refus</button></div></div>';
  }).join('') : '<div class="pv-muted">Aucun refus mémorisé. Un refus évite que la même '
      + 'proposition revienne, et sa raison est relue par l\'IA avant d\'en faire d\'autres.</div>';
}

function objCarteFile(e){
  var id = 'f-' + btoa(unescape(encodeURIComponent(e.cle))).replace(/[^A-Za-z0-9]/g, '');
  return '<div class="obj-c file">'
    + '<div class="obj-h"><strong>' + esc(e.titre) + '</strong>'
    + '<span class="obj-statut">' + esc(e.origine) + '</span></div>'
    + (e.motif ? '<div class="pv-muted">' + esc(e.motif) + '</div>' : '')
    + (e.indice ? '<div class="obj-indice">« ' + esc(e.indice) + ' »</div>' : '')
    + (e.note ? '<div class="obj-cites">Dans <span class="obj-cite" onclick="objOuvrir(\''
        + eu(e.note) + '\')">' + esc(e.note) + '</span></div>' : '')
    + '<div class="obj-f-form">'
    + '<input id="' + id + '-t" type="text" value="' + esc(e.titre) + '" placeholder="titre">'
    + '<input id="' + id + '-r" type="text" placeholder="URL, DOI, arXiv ou ISBN (rend la référence vérifiable)">'
    + '<input id="' + id + '-w" type="text" placeholder="raison (facultative, conservée)">'
    + '</div>'
    + '<div class="obj-a">'
    + '<button class="btn bp" onclick="objAccepter(\'' + eu(e.cle) + '\',\'' + id + '\')">✓ Accepter</button>'
    + '<button class="btn bs" onclick="objRejeter(\'' + eu(e.cle) + '\',\'' + id + '\')">Rejeter</button>'
    + '</div></div>';
}

async function objAccepter(encoded, id){
  var d = await post('/api/objets/file/accepter', {
    cle: decodeURIComponent(encoded),
    titre: $(id + '-t').value.trim(),
    reference: $(id + '-r').value.trim(),
    raison: $(id + '-w').value.trim()});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('Objet créé');
  objChargerFile();
}

async function objRejeter(encoded, id){
  var d = await post('/api/objets/file/rejeter',
    {cle: decodeURIComponent(encoded), raison: $(id + '-w').value.trim()});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('Rejet mémorisé');
  objChargerFile();
}

async function objOublierRejet(encoded){
  var d = await post('/api/objets/rejets/oublier', {cle: decodeURIComponent(encoded)});
  if(d.error){ toast('⚠ ' + d.error); return; }
  objChargerFile();
}

// ── Analyser la note ouverte, et elle seule ─────────────────────────────
// « Demander à l'IA » dans la fenêtre balaie un dossier entier — douze appels au
// modèle quand on en voulait un. Ce bouton-ci n'analyse que la note sous les yeux.
async function objSourcesDeLaNote(){
  if(!ACTIVE){ toast('Ouvrez une note d\'abord'); return; }
  var btn = $('ed-src-ia');
  btn.disabled = true;
  var avant = btn.textContent;
  btn.textContent = '🔖 …';
  try{
    var d = await post('/api/objets/ia', {note: ACTIVE});
    if(d.error){ toast('⚠ ' + d.error, 5000); return; }
    var n = (d.deposees || []).length;
    if(!n){
      toast(d.ecartees
        ? 'Aucune source retenue — ' + d.ecartees + ' proposition(s) écartée(s), extrait introuvable dans la note'
        : 'Aucune source citée en clair trouvée dans cette note', 4500);
      return;
    }
    toast(n + ' source(s) en attente de validation', 4000);
    OBJ.onglet = 1;
    openObjets();
  } finally {
    btn.disabled = false;
    btn.textContent = avant;
  }
}

// ── Marqueur dans l'éditeur ─────────────────────────────────────────────
// Décision 0021 : une note qui cite un objet non relu l'affiche avec un marqueur.
var OBJ_NOTE = {path: null};

async function loadObjetsDeLaNote(path){
  OBJ_NOTE.path = path;
  var badge = $('ed-objets');
  if(!badge) return;
  badge.style.display = 'none';
  if(!path) return;
  var d = await fetch('/api/objets/note?path=' + eu(path)).then(function(r){ return r.json(); });
  if(d.error || OBJ_NOTE.path !== path) return;
  var liste = d.objets || [];
  if(!liste.length) return;
  var nonRelus = liste.filter(function(o){ return o.non_relu; }).length;
  badge.style.display = 'inline-flex';
  badge.textContent = '🔖 ' + liste.length + (nonRelus ? ' ⚠' : '');
  badge.classList.toggle('nonrelu', nonRelus > 0);
  badge.title = liste.length + ' source(s) citée(s)'
    + (nonRelus ? ', dont ' + nonRelus + ' pas encore relue(s)' : '') + ' — cliquer pour les voir';
}

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && $('mobjets').classList.contains('on')) closeObjets();
});
