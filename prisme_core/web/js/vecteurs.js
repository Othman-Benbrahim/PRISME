// ══════════════════════════════════════════════════
//  RECHERCHE SÉMANTIQUE — PARAMÉTRAGE ET VECTORISATION
// ══════════════════════════════════════════════════
// Désactivée par défaut : vectoriser, c'est parfois envoyer le texte de ses notes à
// un tiers. Le mode actif reste visible en permanence, et ce qui sort de la machine
// est dit sans détour (décision 0019).
var VEC = {etat: null, timer: null};

async function vecCharger(){
  clearTimeout(VEC.timer);
  var d = await fetch('/api/vecteurs/etat').then(function(r){ return r.json(); });
  VEC.etat = d;
  $('vec-actif').checked = !!d.actif;
  $('vec-fournisseur').innerHTML = (d.fournisseurs || []).map(function(f){
    return '<option value="' + esc(f) + '">' + esc(vecLibelle(f)) + '</option>';
  }).join('');
  $('vec-fournisseur').value = d.fournisseur || 'api';
  $('vec-modele').value = d.modele || '';
  vecRendreEtat(d);
  if(d.progression && d.progression.en_cours) VEC.timer = setTimeout(vecCharger, 800);
}

function vecLibelle(f){
  return {api: 'API compatible OpenAI (/embeddings)', ollama: 'Ollama (local)',
          onnx: 'ONNX local (plugin)'}[f] || f;
}

function vecRendreEtat(d){
  var e = $('vec-etat');
  var p = d.progression || {};
  if(p.en_cours){
    e.className = 'vec-etat en-cours';
    e.textContent = '⏳ Vectorisation… ' + p.faits + ' / ' + p.total + ' segment(s)';
    return;
  }
  if(!d.actif){
    e.className = 'vec-etat off';
    e.textContent = '○ Désactivée — recherche par mots seule. '
      + (d.vecteurs ? d.vecteurs + ' vecteur(s) conservé(s).' : '');
    return;
  }
  if(!d.disponible){
    e.className = 'vec-etat ko';
    e.textContent = '⚠ ' + (d.raison || 'Fournisseur indisponible') + ' — repli sur la recherche par mots.';
    return;
  }
  e.className = 'vec-etat ok';
  e.textContent = (d.distant ? '⚠ ACTIVE, MODE DISTANT — le texte de vos notes est envoyé à '
                             : '● Active, en local — rien ne sort de votre machine. ')
    + (d.distant ? (d.signature_attendue || '').split(':')[0] + ' pour être vectorisé. ' : '')
    + d.vecteurs + ' segment(s) vectorisé(s)'
    + (d.signature ? ' · ' + esc(d.signature) : '');
  if(p.erreur) e.textContent += ' · dernière erreur : ' + p.erreur;
}

async function vecTester(){
  var btn = $('vec-tester'); btn.disabled = true; btn.textContent = '⏳…';
  var d = await post('/api/vecteurs/tester', vecChamps());
  btn.disabled = false; btn.textContent = 'Tester';
  if(!d.ok){ toast('⚠ ' + (d.raison || d.error), 6000); return; }
  toast('✓ ' + d.modele + ' · ' + d.dimension + ' dimensions · '
        + (d.distant ? 'service distant' : 'local'), 5000);
}

function vecChamps(){
  var c = {emb_fournisseur: $('vec-fournisseur').value, emb_modele: $('vec-modele').value.trim(),
           emb_base_url: $('vec-url').value.trim()};
  var k = $('vec-cle').value;
  if(k) c.emb_api_key = k;
  return c;
}

async function vecEnregistrer(){
  var c = vecChamps();
  c.emb_actif = $('vec-actif').checked;
  if(c.emb_actif && !c.emb_modele){ toast('⚠ Indiquez le modèle d\'embeddings'); return; }
  var d = await post('/api/vecteurs/config', c);
  if(d.error){ toast('⚠ ' + d.error); return; }
  $('vec-cle').value = '';
  toast('✓ Recherche sémantique enregistrée');
  vecCharger();
}

async function vecVectoriser(){
  if(!VEC.etat || !VEC.etat.actif){ toast('Activez d\'abord la recherche sémantique'); return; }
  if(VEC.etat.distant){
    if(!await confirmer({titre: 'Envoi à un service distant', ok: 'Vectoriser', danger: true,
        message: 'Le texte de toutes vos notes va être envoyé au service configuré pour y être '
          + 'vectorisé. Rien n\'est envoyé pour les notes déjà vectorisées. Continuer ?'})) return;
  }
  var d = await post('/api/vecteurs/vectoriser', {fond: true});
  if(d.error){ toast('⚠ ' + d.error); return; }
  toast(d.lance ? 'Vectorisation lancée — vous pouvez continuer à travailler'
                : 'Une vectorisation est déjà en cours');
  vecCharger();
}

async function vecVider(){
  if(!await confirmer({titre: 'Effacer les vecteurs', ok: 'Effacer', danger: true,
      message: 'Les vecteurs seront supprimés. Vos notes et l\'index ne sont pas touchés, '
        + 'mais il faudra tout revectoriser — ce qui peut être long, voire payant.'})) return;
  var d = await post('/api/vecteurs/vider', {});
  toast(d.supprimes + ' vecteur(s) effacé(s)');
  vecCharger();
}
