// ══════════════════════════════════════════════════
//  PROVENANCE DES NOTES
// ══════════════════════════════════════════════════
// Toute note produite par une machine porte son origine dans son en-tête ;
// une note écrite à la main n'est touchée que si quelque chose la cite.
var PROV = {path: null, data: null};
// Contenu estampillé par le serveur, en attente d'ouverture dans un onglet :
// sans ça, l'onglet afficherait la version d'avant estampillage et la première
// sauvegarde effacerait l'en-tête de provenance.
var STAMPED = {};

// Enregistre une note produite par PRISME : le serveur pose l'en-tête.
async function saveGenerated(path, content, prov){
  var r = await post('/api/files/save', {path: path, content: content, provenance: prov || {}});
  if(r.error){ toast('⚠ ' + r.error); return r; }
  if(r.content){                          // le serveur a ajouté l'en-tête
    STAMPED[path] = r.content;
    if(TABS[path]){
      TABS[path].content = r.content; TABS[path].saved = r.content; TABS[path].modified = false;
      if(ACTIVE === path){ $('md-editor').value = r.content; gutterRender(); }
    }
  }
  return r;
}

async function loadProvenance(path){
  PROV = {path: path, data: null};
  var badge = $('ed-prov');
  if(!badge) return;
  badge.style.display = 'none';
  if(!path) return;
  var d = await fetch('/api/provenance?path=' + eu(path)).then(function(r){ return r.json(); });
  if(d.error || PROV.path !== path) return;
  PROV.data = d;
  badge.style.display = 'inline-flex';
  badge.textContent = d.genere ? '🤖' : 'ⓘ';
  badge.classList.toggle('genere', !!d.genere);
  var aUneProv = Object.keys(d.meta || {}).some(function(k){ return d.meta[k]; });
  badge.title = (d.genere ? 'Note produite par un modèle'
                          : (aUneProv ? 'Note avec une provenance renseignée' : 'Note sans provenance'))
    + ' — cliquer pour voir ou modifier';
}

var PV_EDIT = null;          // {champs:{}, sources:[{ref,path,name}]} en cours de saisie

function openProvenance(){
  if(!ACTIVE){ toast('Ouvrez un fichier d\'abord'); return; }
  PV_EDIT = null;
  pvRender();
  $('mprov').classList.add('on');
}
function closeProvenance(){ $('mprov').classList.remove('on'); PV_EDIT = null; }

var PV_LABELS = {id: 'Identifiant', type: 'Type', outil: 'Produite par', genere_par: 'Modèle',
                 preset: 'Preset de prompt', enregistre_le: 'Enregistrée le', invalide_le: 'Retirée le',
                 publie_le: 'Publiée le', valide_du: 'Valide du', valide_au: 'Valide au'};

function pvVal(cle){
  var d = PROV.data || {meta: {}};
  return d.meta[cle] || d.meta['prisme_' + cle] || '';
}

// ── Lecture ───────────────────────────────────────────────────────────
function pvRender(){
  var d = PROV.data;
  var lignes = Object.keys(PV_LABELS).map(function(k){
    var v = pvVal(k);
    return v ? [PV_LABELS[k], String(v)] : null;
  }).filter(Boolean);
  var html = '';
  if(!lignes.length && !(d && (d.sources || []).length)){
    html = '<div class="pv-vide">Cette note n\'a pas d\'en-tête de provenance.<br>'
      + 'C\'est le cas normal d\'une note écrite à la main : PRISME ne lui pose un identifiant '
      + 'que le jour où une autre note la cite. Vous pouvez en ajouter une vous-même.</div>';
  } else {
    html = '<table class="pv-t">' + lignes.map(function(l){
      return '<tr><th>' + esc(l[0]) + '</th><td>' + esc(l[1]) + '</td></tr>';
    }).join('') + '</table>';
    if(d && d.parent){
      html += '<h4>Dérive de</h4><div class="pv-src" onclick="ouvrirSource(\'' + eu(d.parent.path) + '\')">'
        + esc(d.parent.name) + '</div>';
    }
    if(d && (d.sources || []).length){
      html += '<h4>Sources</h4>' + d.sources.map(function(s){
        return s.path
          ? '<div class="pv-src" onclick="ouvrirSource(\'' + eu(s.path) + '\')">📄 ' + esc(s.name) + '</div>'
          : '<div class="pv-src ext">' + (/^https?:/.test(s.ref) ? '🔗 ' : '• ') + esc(s.name) + '</div>';
      }).join('');
    }
  }
  var aUneProvenance = !!lignes.length;
  html += '<div class="mf">'
    + (pvVal('id') ? '' : '<button class="btn bs" onclick="pvPoserId()" title="Rend la note citable sans rien ajouter d\'autre">Poser un identifiant</button>')
    + '<button class="btn bp" onclick="pvEdit()">' + (aUneProvenance ? 'Modifier' : 'Ajouter une provenance') + '</button>'
    + '</div>';
  $('pv-body').innerHTML = html;
}

// ── Saisie ────────────────────────────────────────────────────────────
function pvEdit(){
  var d = PROV.data || {meta: {}, sources: [], types: [], etats: []};
  PV_EDIT = {sources: (d.sources || []).slice()};
  var champ = function(cle, label, extra){
    return '<div class="pv-f"><label>' + esc(label) + '</label>'
      + '<input id="pv-' + cle + '" type="text" value="' + esc(pvVal(cle)) + '" ' + (extra || '') + '></div>';
  };
  var etat = function(cle){
    var v = pvVal(cle + '_etat') || (pvVal(cle) ? 'date' : 'inconnue');
    return '<select id="pv-' + cle + '_etat">' + (d.etats || ['date', 'inconnue', 'ouverte']).map(function(e){
      return '<option value="' + e + '"' + (e === v ? ' selected' : '') + '>' + e + '</option>';
    }).join('') + '</select>';
  };
  var types = (d.types || ['note']).map(function(t){ return '<option value="' + esc(t) + '">'; }).join('');
  $('pv-body').innerHTML =
    '<div class="pv-form">'
    + champ('type', 'Type', 'list="pv-types" placeholder="note, source, synthese, reponse, import"')
    + '<datalist id="pv-types">' + types + '</datalist>'
    + champ('outil', 'Produite par', 'placeholder="saisie manuelle, import, nom d\'un outil…"')
    + champ('genere_par', 'Modèle', 'placeholder="laisser vide si aucune IA"')
    + champ('preset', 'Preset de prompt')
    + champ('publie_le', 'Publiée le', 'placeholder="AAAA-MM-JJ"')
    + champ('enregistre_le', 'Enregistrée le', 'placeholder="AAAA-MM-JJ"')
    + '<div class="pv-f"><label>Valide du <span class="pv-hint">(réservé)</span></label>'
      + '<div class="pv-row"><input id="pv-valide_du" type="text" value="' + esc(pvVal('valide_du')) + '" placeholder="AAAA-MM-JJ">' + etat('valide_du') + '</div></div>'
    + '<div class="pv-f"><label>Valide au <span class="pv-hint">(réservé)</span></label>'
      + '<div class="pv-row"><input id="pv-valide_au" type="text" value="' + esc(pvVal('valide_au')) + '" placeholder="AAAA-MM-JJ">' + etat('valide_au') + '</div></div>'
    + '<div class="pv-f"><label>Sources</label><div id="pv-srclist"></div>'
      + '<div class="pv-row"><input id="pv-srcq" type="text" placeholder="chercher une note, ou coller une URL" '
      + 'oninput="pvChercherSource()" onkeydown="if(event.key===\'Enter\'){event.preventDefault();pvAjouterUrl();}">'
      + '<button class="btn bs" onclick="pvAjouterUrl()">+ URL</button></div>'
      + '<div id="pv-srcres"></div></div>'
    + '</div>'
    + '<div class="mf"><button class="btn bs" onclick="pvRender()">Annuler</button>'
    + '<button class="btn bp" onclick="pvEnregistrer()">Enregistrer</button></div>';
  pvRenderSources();
}

function pvRenderSources(){
  $('pv-srclist').innerHTML = PV_EDIT.sources.map(function(s, i){
    return '<div class="pv-src' + (s.path ? '' : ' ext') + '">'
      + (s.path ? '📄 ' : (/^https?:/.test(s.ref) ? '🔗 ' : '• ')) + esc(s.name || s.ref)
      + '<button class="pv-del" onclick="pvRetirerSource(' + i + ')" title="Retirer">✕</button></div>';
  }).join('') || '<div class="pv-muted">Aucune source</div>';
}
function pvRetirerSource(i){ PV_EDIT.sources.splice(i, 1); pvRenderSources(); }

function pvAjouterUrl(){
  var v = $('pv-srcq').value.trim();
  if(!v) return;
  PV_EDIT.sources.push({ref: v, path: null, name: v});
  $('pv-srcq').value = ''; $('pv-srcres').innerHTML = '';
  pvRenderSources();
}

var pvTimer = null;
function pvChercherSource(){
  clearTimeout(pvTimer);
  pvTimer = setTimeout(async function(){
    var q = $('pv-srcq').value.trim();
    if(q.length < 2 || /^https?:/.test(q)){ $('pv-srcres').innerHTML = ''; return; }
    var d = await fetch('/api/search?q=' + eu(q)).then(function(r){ return r.json(); });
    $('pv-srcres').innerHTML = (d.results || []).slice(0, 6).map(function(r){
      return '<div class="pv-hit" onclick="pvAjouterNote(\'' + eu(r.path) + '\',\'' + eu(r.name) + '\')">📄 '
        + esc(r.name) + ' <span class="pv-muted">' + esc(r.rel) + '</span></div>';
    }).join('') || '<div class="pv-muted">Aucune note trouvée</div>';
  }, 250);
}
function pvAjouterNote(encPath, encName){
  var path = decodeURIComponent(encPath);
  if(!PV_EDIT.sources.some(function(s){ return s.path === path; }))
    PV_EDIT.sources.push({ref: path, path: path, name: decodeURIComponent(encName)});
  $('pv-srcq').value = ''; $('pv-srcres').innerHTML = '';
  pvRenderSources();
}

async function pvEnregistrer(){
  var champs = {};
  ['type', 'outil', 'genere_par', 'preset', 'publie_le', 'enregistre_le',
   'valide_du', 'valide_au'].forEach(function(k){ champs['prisme_' + k] = $('pv-' + k).value.trim(); });
  ['valide_du', 'valide_au'].forEach(function(k){
    var date = $('pv-' + k).value.trim(), etat = $('pv-' + k + '_etat').value;
    // Une date inconnue n'est pas une date ouverte ; mais on n'écrit pas un état
    // que l'utilisateur n'a pas choisi : « inconnue » sans date reste implicite.
    champs['prisme_' + k + '_etat'] = date ? etat : (etat === 'ouverte' ? 'ouverte' : '');
  });
  var r = await post('/api/provenance', {path: ACTIVE, champs: champs,
                                         sources: PV_EDIT.sources.map(function(s){ return s.ref; })});
  if(r.error){ toast('⚠ ' + r.error, 5000); return; }
  pvAppliquerContenu(r.content);
  toast('✓ Provenance enregistrée');
  await loadProvenance(ACTIVE);
  pvRender();
}

async function pvPoserId(){
  var r = await post('/api/provenance/id', {path: ACTIVE});
  if(r.error){ toast('⚠ ' + r.error); return; }
  pvAppliquerContenu(r.content);
  toast('✓ Identifiant posé : ' + r.prisme_id);
  await loadProvenance(ACTIVE);
  pvRender();
}

// L'en-tête a changé sur le disque : l'onglet doit suivre, sinon la prochaine
// sauvegarde écraserait ce qu'on vient d'écrire.
function pvAppliquerContenu(contenu){
  if(!contenu || !TABS[ACTIVE]) return;
  var modifie = TABS[ACTIVE].modified;
  TABS[ACTIVE].content = contenu;
  TABS[ACTIVE].saved = contenu;
  TABS[ACTIVE].modified = false;
  $('md-editor').value = contenu;
  gutterRender();
  renderTabBar();
  if(modifie) toast('⚠ Vos modifications non enregistrées ont été remplacées par la version du disque', 6000);
}

async function ouvrirSource(encoded){
  var path = decodeURIComponent(encoded);
  var d = await fetch('/api/files/read?path=' + eu(path)).then(function(r){ return r.json(); });
  if(d.error){ toast('⚠ ' + d.error); return; }
  closeProvenance();
  openFileTab(path, d.content);
}

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && $('mprov').classList.contains('on')) closeProvenance();
});
