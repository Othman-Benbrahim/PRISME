// ════════════════════════════════════════════════════════
//  Plugin OSINT Cross-Reference — frontend compatible
// ════════════════════════════════════════════════════════
var OSCX = { type: 'auto', query: '', data: null, searching: false };

function oscxEsc(s){
  return String(s == null ? '' : s).replace(/[&<>'"]/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c];
  });
}

function openOsintCx(){
  OSCX.searching = false;
  $('oscx-error').style.display = 'none';
  $('oscx-progress').style.display = 'none';
  $('oscx-results').style.display = 'none';
  $('oscx-form').style.display = 'block';
  $('moscx').classList.add('on');
  setTimeout(function(){ if($('oscx-query')) $('oscx-query').focus(); }, 80);
}

function closeOsintCx(){
  $('moscx').classList.remove('on');
}


function toggleLinkedInBox(){
  var cb = $('oscx-linkedin');
  var box = $('oscx-linkedin-box');
  if(box) box.style.display = cb && cb.checked ? 'block' : 'none';
}

function oscxVal(id){
  var el = $(id);
  return el ? el.value.trim() : '';
}

function setOsintCxType(type){
  OSCX.type = type || 'auto';
  var btns = document.querySelectorAll('.oscx-type-btn');
  for(var i=0;i<btns.length;i++){
    btns[i].classList.toggle('on', btns[i].dataset.type === OSCX.type);
  }
}

async function runOsintCxSearch(){
  if(OSCX.searching) return;
  var q = $('oscx-query').value.trim();
  if(!q){ toast('Requête vide'); return; }
  OSCX.searching = true;
  OSCX.query = q;
  OSCX.data = null;

  $('oscx-form').style.display = 'none';
  $('oscx-error').style.display = 'none';
  $('oscx-results').style.display = 'none';
  $('oscx-progress').style.display = 'block';

  try{
    var r = null;
    if(q){
      var extras = '';
      if($('oscx-score') && $('oscx-score').checked) extras += '&score=1';
      else extras += '&score=0';
      if($('oscx-github') && $('oscx-github').checked) extras += '&github=1';
      if($('oscx-wikidata') && $('oscx-wikidata').checked) extras += '&wikidata=1';
      if($('oscx-entreprise') && $('oscx-entreprise').checked) extras += '&entreprise=1';
      if($('oscx-reddit') && $('oscx-reddit').checked) extras += '&reddit=1';
      if($('oscx-x') && $('oscx-x').checked) extras += '&x=1';
      if($('oscx-linkedin') && $('oscx-linkedin').checked){
        extras += '&linkedin=1';
        var liUrl = oscxVal('oscx-li-url');
        if(liUrl) extras += '&linkedin_url=' + encodeURIComponent(liUrl);
      }
      if($('oscx-socialcli') && $('oscx-socialcli').checked) extras += '&socialcli=1';
      var url = '/api/plugins/osint-cx/crossref?q=' + encodeURIComponent(q) + '&type=' + encodeURIComponent(OSCX.type) + extras;
      r = await fetch(url).then(function(resp){ return resp.json(); });
      if(r.error || r.ok === false){ $('oscx-progress').style.display = 'none'; showOsintCxError(r.error || 'Recherche impossible'); return; }
    }
    $('oscx-progress').style.display = 'none';
    OSCX.data = r;
    renderOsintCxResults(r);
  }catch(e){
    $('oscx-progress').style.display = 'none';
    showOsintCxError('Erreur réseau : ' + e.message);
  }finally{
    OSCX.searching = false;
  }
}

function showOsintCxError(msg){
  $('oscx-error-msg').textContent = msg;
  $('oscx-error').style.display = 'block';
  $('oscx-form').style.display = 'block';
  $('oscx-results').style.display = 'none';
}

function renderOsintCxResults(data){
  $('oscx-results').style.display = 'block';
  var res = data.results || {};
  $('oscx-summary').innerHTML = '<strong>Requête :</strong> ' + oscxEsc(data.query || OSCX.query)
    + ' · <strong>Type :</strong> ' + oscxEsc(data.type || 'auto')
    + (res.count !== undefined ? ' · <strong>Résultats :</strong> ' + oscxEsc(res.count) : '');

  if(data.type === 'username') renderOsintUsername(res);
  else if(data.type === 'email') renderOsintEmail(res);
  else if(data.type === 'phone') renderOsintPhone(res);
  else if(data.type === 'ip') renderOsintIp(res);
  else if(data.type === 'domain') renderOsintDomain(res);
  else renderOsintGeneric(res);

  ['correlation','linkedin','github','wikidata','entreprise','reddit','x_profile','social_cli'].forEach(function(key){
    if(data[key]){
      var container = document.createElement('div');
      if(key === 'correlation') container.innerHTML = renderCorrelationBlock(data[key]);
      if(key === 'linkedin') container.innerHTML = renderLinkedInBlock(data[key]);
      if(key === 'github') container.innerHTML = renderGitHubBlock(data[key]);
      if(key === 'wikidata') container.innerHTML = renderWikidataBlock(data[key]);
      if(key === 'entreprise') container.innerHTML = renderEntrepriseBlock(data[key]);
      if(key === 'reddit') container.innerHTML = renderRedditBlock(data[key]);
      if(key === 'x_profile') container.innerHTML = renderXProfileBlock(data[key]);
      if(key === 'social_cli') container.innerHTML = renderSocialCliBlock(data[key]);
      if(container.firstChild) $('oscx-list').appendChild(container.firstChild);
    }
  });
}


function renderOsintUsername(res){
  var found = res.results || [];
  if(!found.length){
    $('oscx-list').innerHTML = '<div class="oscx-empty">👤 Aucun profil détecté. Cela ne prouve pas que le pseudo est absent : certains sites bloquent les requêtes automatiques.</div>';
    return;
  }
  $('oscx-list').innerHTML = '<div class="oscx-section">' + found.map(function(p){
    return '<div class="oscx-card">'
      + '<div class="oscx-card-title"><span>' + oscxEsc(p.icon || '🔗') + '</span>' + oscxEsc(p.platform || '') + '</div>'
      + '<div class="oscx-url"><a href="' + oscxEsc(p.url) + '" target="_blank" rel="noopener">' + oscxEsc(p.url) + '</a></div>'
      + '</div>';
  }).join('') + '</div>' + (res.note ? '<div class="oscx-note">' + oscxEsc(res.note) + '</div>' : '');
}

function renderOsintEmail(res){
  var html = '<div class="oscx-section">';
  html += '<div class="oscx-card"><div class="oscx-card-title">📧 Format</div>'
    + '<div class="oscx-grid"><div class="oscx-k">Email</div><div class="oscx-v">' + oscxEsc(res.query) + '</div>'
    + '<div class="oscx-k">Format valide</div><div class="oscx-v">' + (res.valid_format ? 'oui' : 'non') + '</div></div></div>';
  if(res.gravatar){
    html += '<div class="oscx-card"><div class="oscx-card-title">👤 Gravatar public</div>'
      + '<div style="display:flex;gap:12px;align-items:flex-start"><img class="oscx-avatar" src="' + oscxEsc(res.gravatar.avatar_url) + '" alt="Gravatar">'
      + '<div><div class="oscx-url"><a href="' + oscxEsc(res.gravatar.profile_url) + '" target="_blank" rel="noopener">' + oscxEsc(res.gravatar.profile_url) + '</a></div></div></div></div>';
  }
  if(res.domain) html += domainCardHtml(res.domain, '🌐 Domaine email');
  if(res.notes && res.notes.length) html += '<div class="oscx-note">' + res.notes.map(oscxEsc).join('<br>') + '</div>';
  $('oscx-list').innerHTML = html + '</div>';
}

function renderOsintPhone(res){
  var countries = (res.country_codes || []).map(function(c){ return oscxEsc(c.code + ' — ' + c.country); }).join('<br>') || 'non reconnu';
  $('oscx-list').innerHTML = '<div class="oscx-section"><div class="oscx-card"><div class="oscx-card-title">📞 Téléphone</div>'
    + '<div class="oscx-grid"><div class="oscx-k">Entrée</div><div class="oscx-v">' + oscxEsc(res.query) + '</div>'
    + '<div class="oscx-k">Nettoyé</div><div class="oscx-v">' + oscxEsc(res.cleaned) + '</div>'
    + '<div class="oscx-k">Format valide</div><div class="oscx-v">' + (res.valid_format ? 'oui' : 'non') + '</div>'
    + '<div class="oscx-k">Indicatif</div><div class="oscx-v">' + countries + '</div></div></div>'
    + (res.notes && res.notes.length ? '<div class="oscx-note">' + res.notes.map(oscxEsc).join('<br>') + '</div>' : '') + '</div>';
}

function renderOsintIp(res){
  var geo = res.geo || {};
  var html = '<div class="oscx-section"><div class="oscx-card"><div class="oscx-card-title">🌐 Adresse IP</div>'
    + '<div class="oscx-grid"><div class="oscx-k">IP</div><div class="oscx-v">' + oscxEsc(res.query) + '</div>'
    + '<div class="oscx-k">Version</div><div class="oscx-v">IPv' + oscxEsc(res.version) + '</div>'
    + '<div class="oscx-k">Privée</div><div class="oscx-v">' + (res.is_private ? 'oui' : 'non') + '</div>'
    + '<div class="oscx-k">Globale</div><div class="oscx-v">' + (res.is_global ? 'oui' : 'non') + '</div></div></div>';
  if(res.geo){
    html += '<div class="oscx-card"><div class="oscx-card-title">📍 Géolocalisation approximative</div><div class="oscx-grid">'
      + '<div class="oscx-k">Pays</div><div class="oscx-v">' + oscxEsc(geo.country) + '</div>'
      + '<div class="oscx-k">Ville</div><div class="oscx-v">' + oscxEsc(geo.city) + '</div>'
      + '<div class="oscx-k">ASN</div><div class="oscx-v">' + oscxEsc(geo.asn) + '</div>'
      + '<div class="oscx-k">Organisation</div><div class="oscx-v">' + oscxEsc(geo.org) + '</div>'
      + '<div class="oscx-k">Timezone</div><div class="oscx-v">' + oscxEsc(geo.timezone) + '</div></div></div>';
  }
  if(res.notes && res.notes.length) html += '<div class="oscx-note">' + res.notes.map(oscxEsc).join('<br>') + '</div>';
  $('oscx-list').innerHTML = html + '</div>';
}

function renderOsintDomain(res){ $('oscx-list').innerHTML = '<div class="oscx-section">' + domainCardHtml(res, '🏛 Domaine') + '</div>'; }

function domainCardHtml(d, title){
  var ips = (d.ips || []).join('<br>') || 'non résolu';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + oscxEsc(title || 'Domaine') + '</div>'
    + '<div class="oscx-grid"><div class="oscx-k">Domaine</div><div class="oscx-v">' + oscxEsc(d.query) + '</div>'
    + '<div class="oscx-k">IP(s)</div><div class="oscx-v">' + ips + '</div></div>';
  if(d.rdap){
    html += '<div class="oscx-note"><strong>RDAP</strong><br>Handle : ' + oscxEsc(d.rdap.handle || '')
      + '<br>Status : ' + oscxEsc((d.rdap.status || []).join ? d.rdap.status.join(', ') : d.rdap.status || '') + '</div>';
  }
  if(d.notes && d.notes.length) html += '<div class="oscx-note">' + d.notes.map(oscxEsc).join('<br>') + '</div>';
  return html + '</div>';
}

function renderOsintGeneric(res){
  $('oscx-list').innerHTML = '<pre class="oscx-card" style="white-space:pre-wrap;font-family:var(--mono);max-height:360px;overflow:auto">' + oscxEsc(JSON.stringify(res, null, 2)) + '</pre>';
}





function renderCorrelationBlock(sc){
  var html = '<div class="oscx-score-card">';
  if(!sc || !sc.ok){
    return html + '<div class="oscx-score-title">🧭 Score de corrélation</div><div class="oscx-note">Score indisponible.</div></div>';
  }
  var score = Number(sc.score || 0);
  var cls = sc.color || (score >= 65 ? 'good' : (score >= 35 ? 'mid' : 'low'));
  html += '<div class="oscx-score-head"><div class="oscx-score-title">🧭 Score de corrélation</div>'
    + '<div class="oscx-score-badge ' + oscxEsc(cls) + '">' + oscxEsc(score) + '/100 · ' + oscxEsc(sc.level || '') + '</div></div>';
  html += '<div class="oscx-score-bar"><div class="oscx-score-fill" style="width:' + Math.max(0, Math.min(100, score)) + '%"></div></div>';
  html += '<div class="oscx-meta"><span>Sources : <strong>' + oscxEsc(sc.sources_count || 0) + '</strong></span><span>Signaux : <strong>' + oscxEsc(sc.signals_count || 0) + '</strong></span></div>';
  var reasons = sc.reasons || [];
  if(reasons.length){
    html += '<div class="oscx-score-reasons">' + reasons.map(function(r){
      return '<div class="oscx-score-reason"><div class="oscx-score-points">+' + oscxEsc(r.points || 0) + '</div><div><strong>' + oscxEsc(r.label || 'Indice') + '</strong><br>' + oscxEsc(r.detail || '') + '</div></div>';
    }).join('') + '</div>';
  }else{
    html += '<div class="oscx-empty">Pas encore assez d’indices pour calculer une concordance significative.</div>';
  }
  if(sc.warnings && sc.warnings.length){
    html += '<div class="oscx-score-warning">' + sc.warnings.map(oscxEsc).join('<br>') + '</div>';
  }
  return html + '</div>';
}

function renderLinkedInBlock(li){
  var title = li && li.ok ? '💼 LinkedIn via RapidAPI' : '💼 LinkedIn — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!li){ return html + '<div class="oscx-note">Aucune réponse LinkedIn.</div></div>'; }
  if(!li.ok){
    html += '<div class="oscx-note">' + oscxEsc(li.error || 'Erreur LinkedIn/RapidAPI') + '</div>';
    if(li.response_preview){ html += '<div class="oscx-json">' + oscxEsc(li.response_preview) + '</div>'; }
    return html + '</div>';
  }
  if(li.found === false){ return html + '<div class="oscx-empty">Aucune donnée structurée LinkedIn exploitable.</div></div>'; }
  var p = li.profile || {};
  html += '<div class="oscx-x-head">';
  if(p.avatar_url){ html += '<img class="oscx-avatar" src="' + oscxEsc(p.avatar_url) + '" alt="Avatar LinkedIn">'; }
  html += '<div><div class="oscx-profile-title">' + oscxEsc(p.full_name || ((p.first_name || '') + ' ' + (p.last_name || '')).trim() || li.query || 'Profil LinkedIn') + '</div>'
    + '<div class="oscx-url"><a href="' + oscxEsc(p.profile_url || li.profile_url || '') + '" target="_blank" rel="noopener">' + oscxEsc(p.profile_url || li.profile_url || '') + '</a></div></div></div>';
  var rows = [
    ['Nom complet', p.full_name], ['Prénom', p.first_name], ['Nom', p.last_name], ['Headline', p.headline], ['Localisation', p.location], ['Entreprise', p.company], ['Résumé', p.summary]
  ].filter(function(r){ return r[1] != null && r[1] !== ''; });
  if(rows.length){
    html += '<div class="oscx-grid oscx-profile-grid">' + rows.map(function(r){
      return '<div class="oscx-k">' + oscxEsc(r[0]) + '</div><div class="oscx-v">' + oscxEsc(r[1]) + '</div>';
    }).join('') + '</div>';
  }
  html += '<div class="oscx-meta"><span>Méthode : <strong>' + oscxEsc(li.method || '') + '</strong></span><span>Source : <strong>RapidAPI</strong></span></div>';
  if(li.notice){ html += '<div class="oscx-note">' + oscxEsc(li.notice) + '</div>'; }
  return html + '</div>';
}

function renderGitHubBlock(gh){
  var title = gh && gh.ok ? '🐙 GitHub public' : '🐙 GitHub — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!gh){ return html + '<div class="oscx-note">Aucune réponse GitHub.</div></div>'; }
  if(!gh.ok){ return html + '<div class="oscx-note">' + oscxEsc(gh.error || 'Erreur GitHub') + '</div></div>'; }
  if(gh.found === false){ return html + '<div class="oscx-empty">Aucun profil GitHub public trouvé.</div></div>'; }
  var p = gh.profile || {};
  html += '<div class="oscx-x-head">';
  if(p.avatar_url){ html += '<img class="oscx-avatar" src="' + oscxEsc(p.avatar_url) + '" alt="Avatar GitHub">'; }
  html += '<div><div class="oscx-profile-title">' + oscxEsc(p.name || p.login || gh.query) + '</div>'
    + '<div class="oscx-url"><a href="' + oscxEsc(p.html_url || '') + '" target="_blank" rel="noopener">' + oscxEsc(p.html_url || '') + '</a></div></div></div>';
  var rows = [
    ['Login', p.login], ['Nom affiché', p.name], ['Bio', p.bio], ['Entreprise', p.company], ['Localisation', p.location], ['Site', p.blog], ['Email public', p.email], ['X/Twitter', p.twitter_username], ['Créé le', p.created_at], ['Mis à jour', p.updated_at]
  ].filter(function(r){ return r[1] != null && r[1] !== ''; });
  if(rows.length){
    html += '<div class="oscx-grid oscx-profile-grid">' + rows.map(function(r){
      var v = (r[0] === 'Site' && String(r[1]).indexOf('http') === 0) ? '<a href="' + oscxEsc(r[1]) + '" target="_blank" rel="noopener">' + oscxEsc(r[1]) + '</a>' : oscxEsc(r[1]);
      return '<div class="oscx-k">' + oscxEsc(r[0]) + '</div><div class="oscx-v">' + v + '</div>';
    }).join('') + '</div>';
  }
  html += '<div class="oscx-meta"><span>Dépôts publics : <strong>' + oscxEsc(p.public_repos != null ? p.public_repos : '—') + '</strong></span><span>Followers : <strong>' + oscxEsc(p.followers != null ? p.followers : '—') + '</strong></span><span>Following : <strong>' + oscxEsc(p.following != null ? p.following : '—') + '</strong></span></div>';
  if(gh.notice){ html += '<div class="oscx-note">' + oscxEsc(gh.notice) + '</div>'; }
  return html + '</div>';
}

function renderWikidataBlock(wd){
  var title = wd && wd.ok ? '🧠 Wikidata' : '🧠 Wikidata — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!wd){ return html + '<div class="oscx-note">Aucune réponse Wikidata.</div></div>'; }
  if(!wd.ok){ return html + '<div class="oscx-note">' + oscxEsc(wd.error || 'Erreur Wikidata') + '</div></div>'; }
  var results = wd.results || [];
  html += '<div class="oscx-meta"><span>Entités : <strong>' + oscxEsc(wd.count || results.length) + '</strong></span><span>Source publique</span></div>';
  if(!results.length){ html += '<div class="oscx-empty">Aucune entité Wikidata trouvée.</div>'; }
  else{
    html += '<div class="oscx-section">' + results.map(function(it){
      return '<div class="oscx-card"><div class="oscx-card-title">' + oscxEsc(it.label || it.id || 'Entité') + '</div>'
        + '<div class="oscx-grid oscx-profile-grid"><div class="oscx-k">ID</div><div class="oscx-v">' + oscxEsc(it.id || '') + '</div>'
        + '<div class="oscx-k">Description</div><div class="oscx-v">' + oscxEsc(it.description || '') + '</div>'
        + '<div class="oscx-k">Lien</div><div class="oscx-v"><a href="' + oscxEsc(it.url || '') + '" target="_blank" rel="noopener">' + oscxEsc(it.url || '') + '</a></div></div></div>';
    }).join('') + '</div>';
  }
  if(wd.notice){ html += '<div class="oscx-note">' + oscxEsc(wd.notice) + '</div>'; }
  return html + '</div>';
}


function renderEntrepriseBlock(ent){
  var title = ent && ent.ok ? '🏢 API Entreprises françaises' : '🏢 API Entreprises — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!ent){ return html + '<div class="oscx-note">Aucune réponse.</div></div>'; }
  if(!ent.ok){ return html + '<div class="oscx-note">' + oscxEsc(ent.error || 'Erreur API Entreprises') + '</div></div>'; }
  var results = ent.results || [];
  html += '<div class="oscx-meta"><span>Résultats : <strong>' + oscxEsc(ent.count || results.length) + '</strong></span><span>Source publique</span></div>';
  if(!results.length){ html += '<div class="oscx-empty">Aucune entreprise trouvée pour cette requête.</div>'; }
  else{
    html += '<div class="oscx-results">' + results.map(function(e){
      var dirs = e.dirigeants || [];
      var rows = [
        ['SIREN', e.siren], ['SIRET siège', e.siret_siege], ['État', e.etat_administratif], ['Nature juridique', e.nature_juridique],
        ['Activité', e.activite_principale], ['Catégorie', e.categorie_entreprise], ['Création', e.date_creation], ['Adresse', e.adresse]
      ].filter(function(r){ return r[1] != null && r[1] !== ''; });
      var card = '<div class="oscx-profile"><div class="oscx-profile-head"><div class="oscx-profile-title">' + oscxEsc(e.nom_complet || 'Entreprise') + '</div></div>';
      if(rows.length){
        card += '<div class="oscx-grid oscx-profile-grid">' + rows.map(function(r){ return '<div class="oscx-k">' + oscxEsc(r[0]) + '</div><div class="oscx-v">' + oscxEsc(r[1]) + '</div>'; }).join('') + '</div>';
      }
      if(dirs.length){
        card += '<div class="oscx-note"><strong>Dirigeants déclarés</strong><br>' + dirs.map(function(d){
          var name = [d.prenoms, d.nom].filter(Boolean).join(' ');
          return oscxEsc(name || '—') + (d.qualite ? ' · ' + oscxEsc(d.qualite) : '') + (d.annee_naissance ? ' · né(e) en ' + oscxEsc(d.annee_naissance) : '');
        }).join('<br>') + '</div>';
      }
      return card + '</div>';
    }).join('') + '</div>';
  }
  if(ent.notice){ html += '<div class="oscx-note">' + oscxEsc(ent.notice) + '</div>'; }
  return html + '</div>';
}

function renderRedditBlock(rd){
  var title = rd && rd.ok ? '🤖 Reddit public' : '🤖 Reddit — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!rd){ return html + '<div class="oscx-note">Aucune réponse.</div></div>'; }
  if(!rd.ok){ return html + '<div class="oscx-note">' + oscxEsc(rd.error || 'Erreur Reddit') + '</div></div>'; }
  if(rd.found === false){ return html + '<div class="oscx-empty">Aucun profil Reddit public trouvé.</div></div>'; }
  var p = rd.profile || {};
  html += '<div class="oscx-grid oscx-profile-grid">'
    + '<div class="oscx-k">Profil</div><div class="oscx-v"><a href="' + oscxEsc(p.url || '') + '" target="_blank" rel="noopener">' + oscxEsc(p.url || p.name || '') + '</a></div>'
    + '<div class="oscx-k">Créé le</div><div class="oscx-v">' + oscxEsc(p.created_iso || '') + '</div>'
    + '<div class="oscx-k">Karma commentaire</div><div class="oscx-v">' + oscxEsc(p.comment_karma) + '</div>'
    + '<div class="oscx-k">Karma lien</div><div class="oscx-v">' + oscxEsc(p.link_karma) + '</div>'
    + '<div class="oscx-k">Karma total</div><div class="oscx-v">' + oscxEsc(p.total_karma) + '</div>'
    + '<div class="oscx-k">Modérateur</div><div class="oscx-v">' + (p.is_mod ? 'oui' : 'non') + '</div>'
    + '<div class="oscx-k">Compte vérifié</div><div class="oscx-v">' + (p.verified ? 'oui' : 'non') + '</div>'
    + '</div>';
  if(p.subreddit_title || p.subreddit_public_description){
    html += '<div class="oscx-note"><strong>Présentation publique</strong><br>' + oscxEsc(p.subreddit_title || '') + '<br>' + oscxEsc(p.subreddit_public_description || '') + '</div>';
  }
  if(rd.notice){ html += '<div class="oscx-note">' + oscxEsc(rd.notice) + '</div>'; }
  return html + '</div>';
}


function renderXProfileBlock(xp){
  var title = xp && xp.ok ? '𝕏 Profil X API' : '𝕏 Profil X API — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!xp){ return html + '<div class="oscx-note">Aucune réponse X.</div></div>'; }
  if(!xp.ok){
    html += '<div class="oscx-note">' + oscxEsc(xp.error || 'Erreur X API') + '</div>';
    if(xp.response_preview){ html += '<div class="oscx-json">' + oscxEsc(xp.response_preview) + '</div>'; }
    return html + '</div>';
  }
  if(xp.found === false){ return html + '<div class="oscx-empty">Aucun profil X trouvé.</div></div>'; }
  var p = xp.profile || {};
  var metrics = p.public_metrics || {};
  html += '<div class="oscx-x-head">';
  if(p.profile_image_url){ html += '<img class="oscx-avatar" src="' + oscxEsc(p.profile_image_url) + '" alt="Avatar X">'; }
  html += '<div><div class="oscx-profile-title">' + oscxEsc(p.name || p.username || xp.query) + '</div>'
    + '<div class="oscx-url"><a href="' + oscxEsc(p.url || ('https://x.com/' + xp.query)) + '" target="_blank" rel="noopener">' + oscxEsc(p.url || ('https://x.com/' + xp.query)) + '</a></div>'
    + '</div></div>';
  html += '<div class="oscx-grid oscx-profile-grid">'
    + '<div class="oscx-k">Username</div><div class="oscx-v">@' + oscxEsc(p.username || xp.query) + '</div>'
    + '<div class="oscx-k">ID</div><div class="oscx-v">' + oscxEsc(p.id || '') + '</div>'
    + '<div class="oscx-k">Bio</div><div class="oscx-v">' + oscxEsc(p.description || '') + '</div>'
    + '<div class="oscx-k">Localisation</div><div class="oscx-v">' + oscxEsc(p.location || '') + '</div>'
    + '<div class="oscx-k">Créé le</div><div class="oscx-v">' + oscxEsc(p.created_at || '') + '</div>'
    + '<div class="oscx-k">Vérifié</div><div class="oscx-v">' + (p.verified ? 'oui' : 'non') + (p.verified_type ? ' · ' + oscxEsc(p.verified_type) : '') + '</div>'
    + '<div class="oscx-k">URL externe</div><div class="oscx-v">' + (p.external_url ? '<a href="' + oscxEsc(p.external_url) + '" target="_blank" rel="noopener">' + oscxEsc(p.external_url) + '</a>' : '') + '</div>'
    + '</div>';
  html += '<div class="oscx-meta">'
    + '<span>Followers : <strong>' + oscxEsc(metrics.followers_count != null ? metrics.followers_count : '—') + '</strong></span>'
    + '<span>Following : <strong>' + oscxEsc(metrics.following_count != null ? metrics.following_count : '—') + '</strong></span>'
    + '<span>Posts : <strong>' + oscxEsc(metrics.tweet_count != null ? metrics.tweet_count : '—') + '</strong></span>'
    + '<span>Listes : <strong>' + oscxEsc(metrics.listed_count != null ? metrics.listed_count : '—') + '</strong></span>'
    + '</div>';
  if(xp.rate_limits && Object.keys(xp.rate_limits).length){
    html += '<div class="oscx-note"><strong>Rate limit X</strong><br><code>' + oscxEsc(JSON.stringify(xp.rate_limits)) + '</code></div>';
  }
  if(xp.notice){ html += '<div class="oscx-note">' + oscxEsc(xp.notice) + '</div>'; }
  return html + '</div>';
}

function renderSocialCliBlock(sc){
  var title = sc && sc.ok ? '🕵️ Maigret/Sherlock local' : '🕵️ Maigret/Sherlock — non disponible';
  var html = '<div class="oscx-card"><div class="oscx-card-title">' + title + '</div>';
  if(!sc){ return html + '<div class="oscx-note">Aucune réponse.</div></div>'; }
  if(!sc.ok){
    html += '<div class="oscx-note">' + oscxEsc(sc.error || 'Outil local indisponible') + '</div>';
    if(sc.install_help){ html += '<div class="oscx-note"><strong>Installation possible</strong><br><code>' + sc.install_help.map(oscxEsc).join('</code><br><code>') + '</code></div>'; }
    return html + '</div>';
  }
  var results = sc.results || [];
  html += '<div class="oscx-meta"><span>Outil : <strong>' + oscxEsc(sc.tool || '') + '</strong></span><span>Profils : <strong>' + oscxEsc(sc.count || results.length) + '</strong></span></div>';
  if(!results.length){ html += '<div class="oscx-empty">Aucun profil trouvé par l’outil local.</div>'; }
  else{
    html += '<div class="oscx-section">' + results.slice(0, 80).map(function(r){
      var label = r.site || r.url || 'Profil';
      return '<div class="oscx-card"><div class="oscx-card-title">🔗 ' + oscxEsc(label) + '</div><div class="oscx-url"><a href="' + oscxEsc(r.url || '') + '" target="_blank" rel="noopener">' + oscxEsc(r.url || '') + '</a></div>' + (r.status ? '<div class="oscx-note">Statut : ' + oscxEsc(r.status) + '</div>' : '') + '</div>';
    }).join('') + '</div>';
  }
  if(sc.notice){ html += '<div class="oscx-note">' + oscxEsc(sc.notice) + '</div>'; }
  return html + '</div>';
}

async function saveOsintCxAsFile(){
  if(!OSCX.data){ toast('Pas de résultat à sauver'); return; }
  if(typeof safeFileName !== 'function' || typeof post !== 'function' || typeof openFileTab !== 'function'){
    toast('⚠ API fichier Second Brain indisponible'); return;
  }
  var slug = safeFileName('osint-' + OSCX.query.substring(0, 50));
  var newPath = null;
  for(var i=1;i<30;i++){
    var name = i === 1 ? slug : slug + '-' + i;
    var resp = await post('/api/files/new', {dir: CUR_DIR, name: name});
    if(resp.ok){ newPath = resp.path; break; }
    if(resp.error !== 'Fichier existant'){ toast('⚠ ' + resp.error); return; }
  }
  if(!newPath){ toast('⚠ Création impossible'); return; }
  var md = '# 🔍 OSINT — ' + OSCX.query + '\n\n'
    + '*Type :* `' + (OSCX.data.type || OSCX.type) + '`  \n'
    + '*Date :* ' + new Date().toISOString() + '\n\n'
    + '```json\n' + JSON.stringify(OSCX.data, null, 2) + '\n```\n';
  await saveGenerated(newPath, md, {type:'import', outil:'osint-cx',
    prisme_requete:OSCX.query});
  openFileTab(newPath, md);
  loadDir(CUR_DIR);
  closeOsintCx();
  toast('✓ Rapport OSINT sauvegardé');
}

document.addEventListener('click', function(e){
  if(e.target === document.getElementById('moscx')) closeOsintCx();
});
document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && document.getElementById('moscx') && document.getElementById('moscx').classList.contains('on')) closeOsintCx();
});
