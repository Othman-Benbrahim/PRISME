// ══════════════════════════════════════════════════
//  RACINES DU VAULT (décision 0028)
// ══════════════════════════════════════════════════
// Plusieurs dossiers déclarés, dans lesquels tout fonctionne : voir, ouvrir, éditer,
// indexer, chercher. Hors de ces racines, rien ne change — dossiers seulement.
// La garde n'est pas levée : elle porte sur une liste au lieu d'un seul chemin.
var RAC = {liste: []};

async function racCharger(){
  var d = await fetch('/api/racines').then(function(r){ return r.json(); });
  RAC.liste = d.racines || [];
  $('rac-liste').innerHTML = RAC.liste.map(function(r){
    return '<div class="rac-l' + (r.existe ? '' : ' absente') + '">'
      + '<div class="rac-h"><strong>' + esc(r.nom || r.chemin) + '</strong>'
      + (r.principale ? '<span class="rac-badge">principale</span>' : '')
      + (r.existe ? '<span class="rac-n">' + r.notes + ' note(s) à la racine</span>'
                  : '<span class="rac-n ko">dossier introuvable</span>') + '</div>'
      + '<code>' + esc(r.chemin) + '</code>'
      + '<div class="rac-a">'
      + (r.principale ? ''
         : '<button class="btn bs" onclick="racPrincipale(\'' + eu(r.chemin) + '\')">En faire la principale</button>'
           + '<button class="btn bs" onclick="racRetirer(\'' + eu(r.chemin) + '\')">Retirer</button>')
      + '<button class="btn bs" onclick="racReconstruire(\'' + eu(r.chemin) + '\')">↻ Réindexer</button>'
      + '</div></div>';
  }).join('');
  $('rac-compte').textContent = RAC.liste.length + ' / ' + (d.plafond || 8) + ' racine(s)';
}

async function racAjouter(){
  var chemin = $('rac-chemin').value.trim();
  if(!chemin){ toast('Indiquez un dossier'); return; }
  var d = await post('/api/racines', {chemin: chemin});
  if(d.error){ toast('⚠ ' + d.error, 5000); return; }
  $('rac-chemin').value = '';
  toast('✓ Racine ajoutée — son index se construit en arrière-plan');
  racCharger(); loadDir(CUR_DIR);
}

async function racRetirer(encoded){
  var chemin = decodeURIComponent(encoded);
  if(!await confirmer({titre: 'Retirer une racine', ok: 'Retirer',
      message: 'PRISME cessera de regarder ce dossier. À part ça, rien n\'est touché : '
        + 'aucun fichier n\'est déplacé ni supprimé.'})) return;
  var d = await post('/api/racines/retirer', {chemin: chemin});
  if(d.error){ toast('⚠ ' + d.error); return; }
  racCharger(); loadDir('');
}

async function racPrincipale(encoded){
  var d = await post('/api/racines/principale', {chemin: decodeURIComponent(encoded)});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('✓ Racine principale changée');
  racCharger(); loadDir('');
}

async function racReconstruire(encoded){
  var d = await post('/api/index/rebuild', {racine: decodeURIComponent(encoded)});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast(d.started ? '↻ Reconstruction lancée' : 'Une mise à jour est déjà en cours');
  setTimeout(loadIndexStatus, 300);
}
