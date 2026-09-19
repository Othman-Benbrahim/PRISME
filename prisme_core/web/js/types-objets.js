// Contrat reçu du serveur : mêmes champs et règles pour l'auteur et les agents.
var TYP = {types: {}, reglages: {}, liste: [], edition: null, proposition: null};

function typElement(tag, texte, classe){
  var n = document.createElement(tag);
  if(texte !== undefined) n.textContent = texte;
  if(classe) n.className = classe;
  return n;
}
function typBouton(texte, action){
  var b = typElement('button', texte, 'btn bs');
  b.type = 'button'; b.onclick = action; return b;
}
async function typCatalogue(){
  var d = await fetch('/api/objets/types').then(r => r.json());
  TYP.types = d.types; TYP.reglages = d.reglages;
}
async function typCharger(){
  try{
    await typCatalogue();
    var select = $('typ-filtre'), ancien = select.value;
    select.replaceChildren(new Option('Tous les types', ''));
    Object.keys(TYP.types).forEach(t => select.add(new Option(TYP.types[t].libelle, t)));
    select.value = ancien;
    var d = await fetch('/api/objets/registre?type=' + eu(select.value)).then(r => r.json());
    if(d.error) throw new Error(d.error);
    TYP.liste = d.objets || [];
    $('typ-liste').replaceChildren();
    if(!TYP.liste.length) $('typ-liste').append(typElement('p', 'Aucun objet de ce type.', 'pv-muted'));
    TYP.liste.forEach(o => {
      var carte = typElement('div', undefined, 'obj-c');
      var h = typElement('div', undefined, 'obj-h');
      h.append(typElement('strong', o.titre), typElement('span', TYP.types[o.type].libelle + ' · ' + o.champs.statut, 'obj-statut'));
      carte.append(h);
      if(o.type === 'prediction') carte.append(typElement('p', 'Probabilité : ' + o.champs.probabilite + ' · Date butoir : ' + o.champs.echeance, 'pv-muted'));
      var actions = typElement('div', undefined, 'obj-a');
      actions.append(typBouton('Ouvrir la note', () => objOuvrir(eu(o.chemin))),
        typBouton('Modifier la fiche', () => typFormulaire(o)),
        typBouton('Retirer', () => typRetirer(o)));
      carte.append(actions); $('typ-liste').append(carte);
    });
  }catch(e){ toast('⚠ ' + e.message); }
}
async function typNouveau(){
  if(!Object.keys(TYP.types).length) await typCatalogue();
  typFormulaire({type: $('typ-filtre').value || 'decision', titre: '', champs: {}});
}
function typFormulaire(o, proposition){
  TYP.edition = o.cle && !proposition ? o.cle : null;
  TYP.proposition = proposition || null;
  var cont = $('typ-form'); cont.replaceChildren(); cont.hidden = false;
  var form = typElement('form');
  form.append(typElement('h4', proposition ? 'Relire et compléter la proposition' : (TYP.edition ? 'Modifier la fiche' : 'Créer un objet')));
  var type = typElement('select'); type.id = 'typ-type'; type.setAttribute('aria-label', 'Type d’objet');
  Object.keys(TYP.types).forEach(t => type.add(new Option(TYP.types[t].libelle, t)));
  type.value = o.type; type.disabled = !!(TYP.edition || proposition);
  type.onchange = () => typFormulaire({type: type.value, titre: $('typ-titre').value, champs: {}});
  form.append(type);
  var titre = typElement('input'); titre.id = 'typ-titre'; titre.value = o.titre; titre.required = true; titre.maxLength = 200;
  var label = typElement('label', 'Titre'); label.append(titre); form.append(label);
  var spec = TYP.types[o.type];
  var statut = typElement('select'); statut.id = 'typ-statut';
  spec.statuts.forEach(s => statut.add(new Option(s.replaceAll('_',' '), s)));
  statut.value = o.champs.statut || spec.statuts[0];
  label = typElement('label', 'Statut'); label.append(statut); form.append(label);
  spec.champs.forEach(c => {
    var input = typElement(c.format === 'choix' ? 'select' : 'input');
    input.id = 'typ-' + c.nom;
    if(c.format === 'choix') c.choix.forEach(v => input.add(new Option(v || 'Non renseigné', v)));
    else if(c.format === 'date') input.type = 'date';
    else if(c.format === 'nombre'){ input.type = 'number'; input.min = 0; input.max = 1; input.step = 'any'; }
    else {input.type = 'text'; input.maxLength = 4000;}
    input.value = o.champs[c.nom] === undefined ? '' : o.champs[c.nom];
    input.required = c.requis;
    var lab = typElement('label', c.libelle + (c.requis ? ' *' : ''));
    lab.append(input); form.append(lab);
  });
  var raison = typElement('input'); raison.id = 'typ-raison'; raison.maxLength = 4000;
  label = typElement('label', 'Raison de cette validation ou modification (facultative)'); label.append(raison); form.append(label);
  if(proposition){
    form.append(typElement('p', 'Proposé par : ' + proposition.origine, 'pv-muted'));
    if(proposition.indice) form.append(typElement('blockquote', proposition.indice));
    if(proposition.motif) form.append(typElement('p', proposition.motif, 'pv-muted'));
    if(proposition.note) form.append(typBouton('Voir la note d’origine', () => objOuvrir(eu(proposition.note))));
  }
  var avertissement = o.type === 'prediction'
    ? 'La probabilité exprime votre pari. Le scoring viendra avec le plugin de calibration. Les modifications restent possibles : cette fiche n’est pas une archive scellée.'
    : 'La note sera créée dans le vault principal. Vos sections libres seront conservées lors des modifications.';
  form.append(typElement('p', avertissement, 'eng-note'));
  var erreur = typElement('p', '', 'eng-err'); erreur.id = 'typ-erreur'; erreur.setAttribute('role', 'alert'); form.append(erreur);
  var actions = typElement('div', undefined, 'obj-a');
  var valider = typElement('button', proposition ? 'Valider et créer la note' : 'Enregistrer', 'btn bp'); valider.type = 'submit';
  actions.append(valider, typBouton('Annuler', () => {cont.hidden = true;})); form.append(actions);
  form.onsubmit = async function(e){
    e.preventDefault(); valider.disabled = true;
    var champs = {statut: statut.value};
    spec.champs.forEach(c => { champs[c.nom] = $('typ-' + c.nom).value; });
    var corps = {type: o.type, titre: titre.value, champs: champs, raison: raison.value};
    if(TYP.edition) corps.cle = TYP.edition;
    if(proposition) corps.cle = proposition.cle;
    try{
      var d = await post(proposition ? '/api/objets/file/accepter' : '/api/objets/registre', corps);
      if(d.error){ erreur.textContent = d.error; return; }
      cont.hidden = true; toast('Objet enregistré');
      typCharger(); if(proposition) objChargerFile(); loadDir(CUR_DIR);
    }catch(err){ erreur.textContent = err.message; }
    finally{ valider.disabled = false; }
  };
  cont.append(form); cont.scrollIntoView({block: 'nearest'});
}
async function typRetirer(o){
  var raison = await demanderTexte({titre: 'Retirer cet objet', label: 'Raison (facultative)', ok: 'Retirer', libre: true});
  if(raison === null) return;
  var d = await post('/api/objets/registre/supprimer', {cle: o.cle, raison: raison});
  if(d.error){toast('⚠ ' + d.error); return;}
  toast('Objet en corbeille, rejet mémorisé'); typCharger(); loadDir(CUR_DIR);
}
async function typRelire(index){
  var p = OBJ.file[index]; await typCatalogue();
  objOnglet(3); typFormulaire({type: p.type, titre: p.titre, champs: p.champs || {}}, p);
}
function typCarteFile(e, index){
  // Aucun attribut dynamique : texte échappé, indices locaux pour les actions.
  return '<div class="obj-c file"><strong>' + esc(e.titre) + '</strong><div class="pv-muted">'
    + esc(e.type) + ' · ' + esc(e.origine) + '</div><div>' + esc(e.motif || '') + '</div>'
    + '<div class="obj-indice">' + esc(e.indice || '') + '</div><div class="obj-a">'
    + '<button class="btn bp" onclick="typRelire(' + index + ')">Relire et compléter</button>'
    + '<button class="btn bs" onclick="typRejeter(' + index + ')">Rejeter</button></div></div>';
}
async function typRejeter(index){
  var e = OBJ.file[index];
  var raison = await demanderTexte({titre: 'Rejeter la proposition', label: 'Raison (facultative)', ok: 'Rejeter', libre: true});
  if(raison === null) return;
  var d = await post('/api/objets/file/rejeter', {cle: e.cle, raison: raison});
  if(d.error){toast('⚠ ' + d.error); return;} objChargerFile();
}
async function typReglages(){
  await typCatalogue();
  var cont = $('typ-reglages'); cont.replaceChildren();
  ['source'].concat(Object.keys(TYP.types)).forEach(t => {
    var form = typElement('form', undefined, 'typ-regle');
    var r = TYP.reglages[t];
    form.append(typElement('strong', t === 'source' ? 'Source' : TYP.types[t].libelle));
    var actif = typElement('input'); actif.type = 'checkbox'; actif.checked = r.entree_directe;
    var lab = typElement('label', 'Entrée directe des imports'); lab.prepend(actif); form.append(lab);
    var seuil = typElement('input'); seuil.type = 'number'; seuil.min = 0; seuil.max = 100; seuil.step = 1; seuil.required = true; seuil.value = r.seuil;
    lab = typElement('label', 'Seuil (0 à 100)'); lab.append(seuil); form.append(lab);
    form.append(typElement('p', t === 'source' ? 'Identifiant reconnu mécaniquement : 100/100 sur la forme, pas sur la vérité de la source.' : 'Aucun signal mécanique défini : la validation reste obligatoire, même si cette option est activée.', 'eng-note'));
    var b = typElement('button', 'Enregistrer', 'btn bs'); b.type = 'submit'; form.append(b);
    form.onsubmit = async e => {
      e.preventDefault(); b.disabled = true;
      try{var d = await post('/api/objets/types/reglages', {type:t, entree_directe:actif.checked, seuil:Number(seuil.value)}); toast(d.error || 'Réglage enregistré');}
      finally{b.disabled = false;}
    };
    cont.append(form);
  });
}
