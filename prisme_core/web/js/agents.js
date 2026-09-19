// ══════════════════════════════════════════════════
//  AGENTS — CLÉS D'ACCÈS ET JOURNAL
// ══════════════════════════════════════════════════
// Une clé par agent, affichée une seule fois. PRISME n'en garde que l'empreinte :
// personne — pas même vous — ne peut la relire ensuite.
var AG = {onglet: 0, cles: [], comptes: {}, droits: [], nouvelle: null};

async function openAgents(){
  $('magents').classList.add('on');
  agOnglet(AG.onglet);
}
function closeAgents(){ $('magents').classList.remove('on'); }

function agOnglet(i){
  AG.onglet = i;
  for(var k = 0; k < 3; k++){
    $('agt' + k).classList.toggle('on', k === i);
    $('agp' + k).style.display = k === i ? '' : 'none';
  }
  if(i === 0) agCharger();
  else if(i === 1) agJournal();
  // l'onglet MCP n'a rien a charger : il ne produit qu'a la demande
}

// ══════════════════════════════════════════════════
//  MCP — connecter Claude Code (E10, decision 0032)
// ══════════════════════════════════════════════════
async function mcpGenerer(){
  var nom = $('mcp-nom').value.trim();
  if(!nom){ toast('Donnez un nom a l\'agent'); return; }
  var d = await post('/api/agents/mcp', {nom: nom});
  if(d.error){ toast('\u26a0 ' + d.error); return; }
  // Indente ici, pas cote serveur : ce bloc est lu et colle par un humain.
  $('mcp-json').textContent = JSON.stringify(d.configuration, null, 2);
  $('mcp-aide').innerHTML =
      'Dans Claude Code : <code>claude mcp add-json prisme</code>, ou collez ce bloc dans '
    + 'votre fichier de configuration MCP. L\'adaptateur est '
    + '<code>' + esc(d.adaptateur) + '</code>.<br>'
    + 'PRISME doit tourner pour que l\'agent reponde : l\'adaptateur ne fait que lui parler.';
  $('mcp-sortie').style.display = '';
  agCharger();
}

function mcpCopier(){
  navigator.clipboard.writeText($('mcp-json').textContent).then(
    function(){ toast('Configuration copiee'); },
    function(){ toast('Copie impossible \u2014 selectionnez le texte'); });
}
function mcpFermer(){ $('mcp-sortie').style.display = 'none'; $('mcp-json').textContent = ''; }

async function agCharger(){
  var d = await fetch('/api/agents/cles').then(function(r){ return r.json(); });
  AG.cles = d.cles || [];
  AG.comptes = d.comptes || {};
  AG.droits = d.droits || [];
  $('ag-liste').innerHTML = AG.cles.length ? AG.cles.map(agCarte).join('')
    : '<div class="pv-muted">Aucune clé. Créez-en une pour qu\'un agent extérieur puisse '
      + 'lire vos notes et vous proposer des sources.</div>';
}

function agCarte(c){
  var n = AG.comptes[c.id] || {appels: 0, refus: 0};
  var revoquee = !!c.revoquee_le;
  return '<div class="ag-c' + (revoquee ? ' revoquee' : '') + '">'
    + '<div class="ag-h"><strong>' + esc(c.nom) + '</strong>'
    + '<code class="ag-indice">' + esc(c.indice) + '</code>'
    + (revoquee ? '<span class="ag-etat">révoquée le ' + esc(c.revoquee_le.replace('T', ' ')) + '</span>'
                : '<span class="ag-etat ok">active</span>') + '</div>'
    + '<div class="ag-droits">' + AG.droits.map(function(d){
        var actif = (c.droits || []).indexOf(d) >= 0;
        var fige = revoquee || d === 'lecture';
        return '<label class="ag-d' + (actif ? ' on' : '') + (fige ? ' fige' : '') + '">'
          + '<input type="checkbox" ' + (actif ? 'checked' : '') + ' ' + (fige ? 'disabled' : '')
          + ' onchange="agDroits(\'' + esc(c.id) + '\')" data-cle="' + esc(c.id) + '" data-droit="' + esc(d) + '">'
          + esc(d === 'ecriture' ? 'écriture directe' : d) + '</label>';
      }).join('') + '</div>'
    + ((c.droits || []).indexOf('ecriture') >= 0 && !revoquee
        ? '<div class="ag-avert">⚠ Cet agent écrit directement dans le vault, sans passer par la file.</div>' : '')
    + '<div class="pv-muted">créée le ' + esc((c.creee_le || '').replace('T', ' '))
    + (c.derniere_utilisation ? ' · dernier appel ' + esc(c.derniere_utilisation.replace('T', ' ')) : ' · jamais utilisée')
    + ' · ' + (c.appels || 0) + ' appel(s)' + (n.refus ? ', ' + n.refus + ' refus' : '') + '</div>'
    + '<div class="ag-a">'
    + (revoquee
        ? '<button class="btn bs" onclick="agOublier(\'' + esc(c.id) + '\')">Oublier</button>'
        : '<button class="btn bs" onclick="agRevoquer(\'' + esc(c.id) + '\')">Révoquer</button>')
    + '<button class="btn bs" onclick="agJournalDe(\'' + esc(c.id) + '\')">Journal</button>'
    + '</div></div>';
}

async function agCreer(){
  var nom = $('ag-nom').value.trim();
  if(!nom){ toast('Donnez un nom à l\'agent'); return; }
  var droits = ['lecture'];
  if($('ag-proposition').checked) droits.push('proposition');
  if($('ag-ecriture').checked) droits.push('ecriture');
  var d = await post('/api/agents/cles', {nom: nom, droits: droits});
  if(d.error){ toast('⚠ ' + d.error); return; }
  AG.nouvelle = d.cle;
  $('ag-nom').value = '';
  $('ag-nouvelle').style.display = '';
  $('ag-nouvelle-cle').textContent = d.cle;
  agCharger();
}

function agCopier(){
  var t = $('ag-nouvelle-cle').textContent;
  navigator.clipboard.writeText(t).then(function(){ toast('Clé copiée'); },
                                        function(){ toast('Copie impossible — sélectionnez le texte'); });
}
function agFermerNouvelle(){ $('ag-nouvelle').style.display = 'none'; AG.nouvelle = null; }

async function agDroits(id){
  var droits = [];
  document.querySelectorAll('input[data-cle="' + id + '"]').forEach(function(i){
    if(i.checked || i.dataset.droit === 'lecture') droits.push(i.dataset.droit);
  });
  if(droits.indexOf('ecriture') >= 0){
    if(!await confirmer({titre: 'Écriture directe', ok: 'Accorder', danger: true,
        message: 'Cet agent pourra écrire des notes dans votre vault sans passer par la file '
          + 'de validation. Ses notes resteront estampillées à son nom, et une version '
          + 'précédente est conservée à chaque écrasement. Accorder ce droit ?'})){
      agCharger(); return;
    }
  }
  var d = await post('/api/agents/cles/droits', {id: id, droits: droits});
  if(d.error){ toast('⚠ ' + d.error); }
  agCharger();
}

async function agRevoquer(id){
  if(!await confirmer({titre: 'Révoquer une clé', ok: 'Révoquer', danger: true,
      message: 'L\'agent perd immédiatement tout accès. Ses appels passés restent dans le '
        + 'journal, et ce qu\'il a déposé reste dans la file de validation.'})) return;
  var d = await post('/api/agents/cles/revoquer', {id: id});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast('Clé révoquée');
  agCharger();
}

async function agOublier(id){
  if(!await confirmer({titre: 'Oublier une clé', ok: 'Oublier',
      message: 'Retirer cette clé révoquée de la liste. Le journal garde la trace de ses appels.'})) return;
  var d = await post('/api/agents/cles/oublier', {id: id});
  if(d.error){ toast('⚠ ' + d.error); return; }
  agCharger();
}

async function agJournal(cle){
  var d = await fetch('/api/agents/journal' + (cle ? '?cle=' + eu(cle) : ''))
            .then(function(r){ return r.json(); });
  var lignes = d.lignes || [];
  $('ag-filtre').innerHTML = cle
    ? 'Filtré sur <code>' + esc(cle) + '</code> <button class="btn bs" onclick="agJournal()">Tout voir</button>'
    : '';
  $('ag-journal').innerHTML = lignes.length ? '<table class="ag-t"><tr><th>Quand</th><th>Agent</th>'
      + '<th>Appel</th><th>Statut</th></tr>' + lignes.map(function(l){
      return '<tr class="' + (l.statut >= 400 ? 'refus' : '') + '">'
        + '<td>' + esc((l.le || '').replace('T', ' ')) + '</td>'
        + '<td>' + esc(l.agent) + '</td>'
        + '<td><code>' + esc(l.methode) + ' ' + esc(l.chemin) + '</code>'
        + (l.detail ? '<div class="pv-muted">' + esc(l.detail) + '</div>' : '') + '</td>'
        + '<td>' + esc(l.statut) + '</td></tr>';
    }).join('') + '</table>'
    : '<div class="pv-muted">Journal vide. Chaque appel d\'agent y laissera une ligne.</div>';
}
function agJournalDe(cle){ agOnglet(1); agJournal(cle); }

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && $('magents').classList.contains('on')) closeAgents();
});
