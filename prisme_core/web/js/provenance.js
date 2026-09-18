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
  badge.title = (d.genere ? 'Note produite par une machine' : 'Note écrite à la main')
    + ' — cliquer pour voir sa provenance';
}

function openProvenance(){
  if(!ACTIVE){ toast('Ouvrez un fichier d\'abord'); return; }
  var d = PROV.data;
  var lignes = [];
  var etiquettes = {id: 'Identifiant', type: 'Type', outil: 'Produite par',
                    genere_par: 'Modèle', preset: 'Preset de prompt', enregistre_le: 'Enregistrée le',
                    invalide_le: 'Retirée le', publie_le: 'Publiée le', parent: 'Dérive de',
                    valide_du: 'Valide du', valide_au: 'Valide au'};
  if(d){
    Object.keys(etiquettes).forEach(function(k){
      var v = d.meta[k] || d.meta['prisme_' + k];
      if(v && k !== 'parent') lignes.push([etiquettes[k], String(v)]);
    });
  }
  var html = '';
  if(!d || (!lignes.length && !(d.sources || []).length)){
    html = '<div class="pv-vide">Cette note n\'a pas d\'en-tête de provenance.<br>'
      + 'C\'est le cas normal d\'une note écrite à la main : PRISME ne lui pose un identifiant '
      + 'que le jour où une autre note la cite.</div>';
  } else {
    html = '<table class="pv-t">' + lignes.map(function(l){
      return '<tr><th>' + esc(l[0]) + '</th><td>' + esc(l[1]) + '</td></tr>';
    }).join('') + '</table>';
    if(d.parent){
      html += '<h4>Dérive de</h4><div class="pv-src" onclick="ouvrirSource(\'' + eu(d.parent.path) + '\')">'
        + esc(d.parent.name) + '</div>';
    }
    if((d.sources || []).length){
      html += '<h4>Sources</h4>' + d.sources.map(function(s){
        return s.path
          ? '<div class="pv-src" onclick="ouvrirSource(\'' + eu(s.path) + '\')">📄 ' + esc(s.name) + '</div>'
          : '<div class="pv-src ext">' + (/^https?:/.test(s.ref) ? '🔗 ' : '• ') + esc(s.name) + '</div>';
      }).join('');
    }
  }
  $('pv-body').innerHTML = html;
  $('mprov').classList.add('on');
}
function closeProvenance(){ $('mprov').classList.remove('on'); }

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
