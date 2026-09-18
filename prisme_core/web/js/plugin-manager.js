// ══════════════════════════════════════════════════
//  GESTIONNAIRE DE PLUGINS
// ══════════════════════════════════════════════════
var PM = {list: [], encryption: false, pending: null};
var PM_STATUS = {actif:'Actif', desactive:'Désactivé', erreur:'Erreur', incompatible:'Incompatible', redemarrage:'Redémarrage requis'};
var PM_SECRET = {chiffree:'défini (chiffré)', clair:'défini (en clair)', illisible:'illisible sur cette machine', vide:'non défini'};

async function openPlugins(){
  $('mplugins').classList.add('on');
  pmShowList();
  await pmLoad();
}
function closePlugins(){ $('mplugins').classList.remove('on'); }

async function pmLoad(){
  var r = await fetch('/api/plugin-manager/list').then(function(x){return x.json();});
  if(r.error){ toast('⚠ '+r.error); return; }
  PM.list = r.plugins; PM.encryption = r.encryption;
  pmRender();
}

function pmShowList(){
  $('pm-list-view').style.display='block';
  $('pm-confirm-view').style.display='none';
  PM.pending = null;
}

function pmRender(){
  var h = PM.list.map(function(p){
    var perms = p.permissions.length
      ? p.permissions.map(function(x){return '<span class="pm-perm" title="'+esc(x.id)+'">'+esc(x.label)+'</span>';}).join('')
      : '<span class="pm-muted">aucune permission particulière</span>';
    var secrets = p.secrets.map(function(s){
      return '<div class="pm-secret"><label>'+esc(s.label)+(s.optional?' <em>(facultatif)</em>':'')+'</label>'
        +'<div class="pm-secret-row"><input type="password" autocomplete="off" id="pm-sec-'+esc(p.id)+'-'+esc(s.name)+'" placeholder="'+esc(PM_SECRET[s.state]||s.state)+'">'
        +'<button class="btn bs" onclick="pmSaveSecret(\''+esc(p.id)+'\',\''+esc(s.name)+'\')">Enregistrer</button>'
        +'<button class="btn bs" onclick="pmClearSecret(\''+esc(p.id)+'\',\''+esc(s.name)+'\')" title="Effacer">✕</button></div></div>';
    }).join('');
    var canToggle = p.status==='actif' || p.status==='desactive' || p.status==='erreur';
    return '<div class="pm-item pm-'+esc(p.status)+'">'
      +'<div class="pm-head"><strong>'+esc(p.name)+'</strong> <span class="pm-muted">'+esc(p.id)+' · v'+esc(p.version)+'</span>'
      +'<span class="pm-status">'+esc(PM_STATUS[p.status]||p.status)+'</span>'
      +(canToggle?'<label class="pm-toggle"><input type="checkbox" '+(p.status==='actif'?'checked':'')+' onchange="pmToggle(\''+esc(p.id)+'\',this.checked)"> activé</label>':'')
      +'</div>'
      +(p.description?'<div class="pm-desc">'+esc(p.description)+'</div>':'')
      +(p.error?'<div class="pm-error">'+esc(p.error)+'</div>':'')
      +(p.modified?'<div class="pm-error">Contenu modifié depuis son installation.</div>':'')
      +'<div class="pm-perms">'+perms+'</div>'
      +secrets
      +'<div class="pm-foot"><span class="pm-muted">Source : '+esc(p.source)+'</span>'
      +'<button class="btn bs pm-del" onclick="pmUninstall(\''+esc(p.id)+'\')">Désinstaller</button></div>'
      +'</div>';
  }).join('');
  $('pm-list').innerHTML = h || '<div class="pm-muted">Aucun plugin installé.</div>';
  $('pm-encryption').textContent = PM.encryption
    ? 'Les secrets sont chiffrés pour votre session Windows.'
    : 'Chiffrement indisponible sur ce système : les secrets sont stockés en clair.';
}

async function pmToggle(id, enabled){
  var r = await post('/api/plugin-manager/toggle', {id:id, enabled:enabled});
  if(r.error){ toast('⚠ '+r.error); }
  else if(r.status==='erreur'){ toast('⚠ '+r.error, 5000); }
  else { toast(enabled?'✓ Plugin activé — rechargez la page (Ctrl+R) pour son interface':'✓ Plugin désactivé', 4500); }
  pmLoad();
}

async function pmUninstall(id){
  if(!await confirmer({titre:'Désinstaller un plugin', danger:true, ok:'Désinstaller',
      message:'Désinstaller « '+id+' » ? Son dossier part dans la corbeille des plugins et ses secrets sont effacés.'})) return;
  var r = await post('/api/plugin-manager/uninstall', {id:id});
  if(r.error){ toast('⚠ '+r.error); return; }
  toast('✓ Désinstallé'+(r.restart_advised?' — redémarrez PRISME pour le décharger complètement':''), 5000);
  pmLoad();
}

async function pmSaveSecret(id, name){
  var el = $('pm-sec-'+id+'-'+name); var v = el.value.trim();
  if(!v){ toast('Saisissez une valeur, ou utilisez ✕ pour effacer'); return; }
  var r = await post('/api/plugin-manager/secret', {id:id, name:name, value:v});
  el.value='';
  if(r.error){ toast('⚠ '+r.error); return; }
  toast('✓ Secret enregistré'+(r.encryption?' (chiffré)':' (en clair)'));
  pmLoad();
}
async function pmClearSecret(id, name){
  var r = await post('/api/plugin-manager/secret', {id:id, name:name, value:''});
  if(r.error){ toast('⚠ '+r.error); return; }
  toast('Secret effacé'); pmLoad();
}

async function pmInspectFile(input){
  var f = input.files && input.files[0]; input.value='';
  if(!f) return;
  var fd = new FormData(); fd.append('file', f);
  var r = await fetch('/api/plugin-manager/inspect', {method:'POST', body:fd}).then(function(x){return x.json();});
  pmConfirm(r);
}
async function pmInspectUrl(){
  var url = $('pm-url').value.trim();
  if(!url){ toast('Indiquez une adresse https://'); return; }
  $('pm-url-btn').disabled = true;
  try{ pmConfirm(await post('/api/plugin-manager/inspect', {url:url})); }
  finally{ $('pm-url-btn').disabled = false; }
}

function pmConfirm(r){
  if(r.error){ toast('⚠ '+r.error, 6000); return; }
  PM.pending = r;
  var perms = r.permissions.length
    ? '<ul>'+r.permissions.map(function(p){return '<li>'+esc(p.label)+'</li>';}).join('')+'</ul>'
    : '<p class="pm-muted">Aucune permission particulière déclarée.</p>';
  $('pm-confirm-body').innerHTML =
    '<div class="pm-head"><strong>'+esc(r.name)+'</strong> <span class="pm-muted">'+esc(r.id)+' · v'+esc(r.version)+'</span></div>'
    +(r.author?'<div class="pm-muted">Auteur déclaré : '+esc(r.author)+'</div>':'')
    +(r.description?'<div class="pm-desc">'+esc(r.description)+'</div>':'')
    +(r.exists?'<div class="pm-error">Un plugin « '+esc(r.id)+' » est déjà installé (v'+esc(r.installed_version||'?')+'). L\'installer le remplacera ; un redémarrage sera nécessaire.</div>':'')
    +'<h4>Permissions déclarées</h4>'+perms
    +'<p class="pm-warn">Ces permissions vous informent : elles n\'empêchent pas le code du plugin d\'agir avec les mêmes droits que PRISME. N\'installez que des plugins dont vous faites confiance à la source.</p>'
    +'<h4>Provenance</h4><div class="pm-muted">'+esc(r.source)+'</div>'
    +'<div class="pm-mono">SHA-256 : '+esc(r.sha256)+'</div>'
    +'<div class="pm-muted">'+r.file_count+' fichier(s), '+Math.round(r.unpacked/1024)+' Ko décompressés</div>'
    +'<details><summary>Fichiers</summary><pre class="pm-files">'+esc(r.files.join('\n'))+'</pre></details>';
  $('pm-list-view').style.display='none';
  $('pm-confirm-view').style.display='block';
}

async function pmInstall(){
  if(!PM.pending) return;
  var r = await post('/api/plugin-manager/install', {token:PM.pending.token, replace:PM.pending.exists});
  if(r.error){ toast('⚠ '+r.error, 6000); return; }
  if(r.status==='redemarrage') toast('✓ Mise à jour installée — redémarrez PRISME', 6000);
  else if(r.status==='actif') toast('✓ Plugin installé — rechargez la page (Ctrl+R) pour son interface', 6000);
  else toast('⚠ Installé mais non actif : '+(r.error||r.status), 6000);
  pmShowList(); pmLoad();
}

document.addEventListener('keydown', function(e){
  if(e.key==='Escape' && $('mplugins').classList.contains('on')) closePlugins();
});
