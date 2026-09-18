// ══════════════════════════════════════════════════
//  DIALOGUES DANS L'INTERFACE (au lieu des popups du navigateur)
// ══════════════════════════════════════════════════
// alert(), confirm() et prompt() bloquent la page, ne se stylent pas et
// s'affichent hors de PRISME. Tout passe désormais par ces deux fonctions.
var DLG = {resoudre: null};

function _dlgFermer(valeur){
  $('mdialog').classList.remove('on');
  var f = DLG.resoudre; DLG.resoudre = null;
  if(f) f(valeur);
}

function _dlgOuvrir(html, apres){
  $('dlg-body').innerHTML = html;
  $('mdialog').classList.add('on');
  if(apres) apres();
  return new Promise(function(r){ DLG.resoudre = r; });
}

// Confirmation : renvoie true ou false
function confirmer(options){
  var o = typeof options === 'string' ? {message: options} : (options || {});
  return _dlgOuvrir(
    '<div class="mt">' + esc(o.titre || 'Confirmer') + '</div>'
    + '<div class="dlg-msg">' + esc(o.message || '') + '</div>'
    + '<div class="mf"><button class="btn bs" onclick="_dlgFermer(false)">' + esc(o.annuler || 'Annuler') + '</button>'
    + '<button class="btn ' + (o.danger ? 'bd' : 'bp') + '" id="dlg-ok" onclick="_dlgFermer(true)">'
    + esc(o.ok || 'Confirmer') + '</button></div>',
    function(){ $('dlg-ok').focus(); });
}

// Saisie : renvoie le texte, ou null si annulé
function demanderTexte(options){
  var o = options || {};
  return _dlgOuvrir(
    '<div class="mt">' + esc(o.titre || 'Saisie') + '</div>'
    + '<div class="dlg-f"><label>' + esc(o.label || '') + '</label>'
    + '<input id="dlg-input" type="text" value="' + esc(o.valeur || '') + '" placeholder="' + esc(o.placeholder || '') + '"></div>'
    + (o.aide ? '<div class="dlg-aide">' + esc(o.aide) + '</div>' : '')
    + '<div class="mf"><button class="btn bs" onclick="_dlgFermer(null)">Annuler</button>'
    + '<button class="btn bp" onclick="_dlgValider()">' + esc(o.ok || 'Valider') + '</button></div>',
    function(){
      var i = $('dlg-input'); i.focus(); i.select();
      i.addEventListener('keydown', function(e){
        if(e.key === 'Enter'){ e.preventDefault(); _dlgValider(); }
        else if(e.key === 'Escape'){ e.preventDefault(); _dlgFermer(null); }
      });
    });
}
function _dlgValider(){
  var v = $('dlg-input').value.trim();
  if(!v) { $('dlg-input').focus(); return; }
  _dlgFermer(v);
}

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && $('mdialog').classList.contains('on')) _dlgFermer(null);
});
