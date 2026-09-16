#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_settings.py — aligne le modal "Parametres" sur l'ecran d'accueil.

  python patch_settings.py --dry-run
  python patch_settings.py

CORRIGE UNE REGRESSION introduite par patch_onboarding.py :
le champ Modele etait un <select> a 8 options figees. Des que le modele
configure n'y figure pas (openai/gpt-4o-mini, llama3.1, claude-sonnet-5...),
le select s'affiche VIDE — et Sauvegarder ecrase alors le modele par "".

Corrections apportees :
  1. Modele : <select> fige  ->  champ texte + datalist (accepte tout nom)
  2. Ajout du selecteur de fournisseur (meme liste que l'accueil)
  3. Etiquette "Cle API FantasyAI" -> "Cle API" + placeholder dynamique
  4. loadMods() remplit la datalist au lieu d'ecraser un select
  5. saveCfg() refuse d'enregistrer un modele vide

PREREQUIS : patch_onboarding.py et patch_providers.py appliques
(le selecteur reutilise la liste ONB_PROVIDERS).
"""
import argparse
import shutil
import sys
from pathlib import Path

MARKER = "SB_SETTINGS_PATCH"

# ═══════════════════════════════════════════════════════════════════════
#  1. Champ cle + selecteur de fournisseur
# ═══════════════════════════════════════════════════════════════════════

OLD_KEY_FIELD = '''  <div><label>Clé API FantasyAI</label>
  <input id="ckey" type="password" placeholder="fantasy-xxxxxxxxxxxx">
  <div id="kinfo" style="font-size:11px;margin-top:5px"></div></div>'''

NEW_KEY_FIELD = '''  <!-- ''' + MARKER + ''' -->
  <div><label>Fournisseur</label>
  <select id="cprov" onchange="cfgProv()"></select>
  <div id="cprov-help" style="font-size:11px;color:var(--tx2);margin-top:4px"></div></div>
  <div><label>Clé API <span style="color:var(--tx2);font-weight:400">(inutile en local)</span></label>
  <input id="ckey" type="password" placeholder="">
  <div id="kinfo" style="font-size:11px;margin-top:5px"></div></div>'''

# ═══════════════════════════════════════════════════════════════════════
#  2. Modele : select fige -> texte libre + datalist
# ═══════════════════════════════════════════════════════════════════════

OLD_MODEL_FIELD = '''  <div><label>Modèle IA</label>
  <select id="cmod">
    <option value="gpt-4o">GPT-4o</option><option value="gpt-4o-mini">GPT-4o Mini</option>
    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
    <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
    <option value="deepseek-chat">DeepSeek Chat</option>
    <option value="deepseek-r1">DeepSeek R1</option>
  </select></div>'''

NEW_MODEL_FIELD = '''  <div><label>Modèle IA</label>
  <input id="cmod" type="text" list="cfg-models" placeholder="nom exact du modèle">
  <datalist id="cfg-models"></datalist></div>'''

# ═══════════════════════════════════════════════════════════════════════
#  3. openCfg : placeholder + remplissage
# ═══════════════════════════════════════════════════════════════════════

OLD_PLACEHOLDER = """  $('ckey').placeholder=c.has_key?'(clé définie — laisser vide pour garder)':'fantasy-xxxxxxxxxxxx';"""

NEW_PLACEHOLDER = """  $('ckey').placeholder=c.has_key?'(clé définie — laisser vide pour garder)':'votre clé API';
  cfgFillProviders(c);"""

OLD_FILL = """  $('cmod').value=c.model||'gpt-4o';$('cws').value=c.workspace||'';$('curl').value=c.base_url||'https://fantasyai.cloud/api/v1';"""

NEW_FILL = """  $('cmod').value=c.model||'';$('cws').value=c.workspace||'';$('curl').value=c.base_url||'';"""

# ═══════════════════════════════════════════════════════════════════════
#  4. loadMods : remplir la datalist
# ═══════════════════════════════════════════════════════════════════════

OLD_LOADMODS = """  if(d.models&&d.models.length){
    $('cmod').innerHTML=d.models.map(function(m){return '<option value="'+m+'">'+m+'</option>';}).join('');
    toast('✓ '+d.models.length+' modèles');
  }else toast('⚠ '+(d.error||'Aucun modèle'));"""

NEW_LOADMODS = """  if(d.models&&d.models.length){
    $('cfg-models').innerHTML=d.models.slice(0,300).map(function(m){
      return '<option value="'+m+'">';}).join('');
    if(!$('cmod').value) $('cmod').value=d.models[0];
    toast('✓ '+d.models.length+' modèles — cliquez dans le champ Modèle');
  }else toast('⚠ '+(d.error||'Aucun modèle — vérifiez la clé et l\\'URL'));"""

# ═══════════════════════════════════════════════════════════════════════
#  5. saveCfg : refuser un modele vide + helpers
# ═══════════════════════════════════════════════════════════════════════

OLD_SAVE = """async function saveCfg(){
  var u={model:$('cmod').value,workspace:$('cws').value,base_url:$('curl').value};
  var k=$('ckey').value;if(k)u.api_key=k;
  await post('/api/config',u); closeCfg(); toast('✓ Paramètres sauvegardés'); loadDir(u.workspace);
}"""

NEW_SAVE = """// """ + MARKER + """
function cfgFillProviders(c){
  if(typeof ONB_PROVIDERS === 'undefined') return;
  var url=(c.base_url||'').replace(/\\/$/,'');
  var match='custom';
  for(var i=0;i<ONB_PROVIDERS.length;i++){
    if(ONB_PROVIDERS[i].url && ONB_PROVIDERS[i].url.replace(/\\/$/,'')===url){ match=ONB_PROVIDERS[i].id; break; }
  }
  $('cprov').innerHTML=ONB_PROVIDERS.map(function(p){
    return '<option value="'+p.id+'">'+p.label+'</option>';}).join('');
  $('cprov').value=match;
  var p=ONB_PROVIDERS.filter(function(x){return x.id===match;})[0];
  if(p){ $('cprov-help').textContent=p.help; if(p.ph && !c.has_key) $('ckey').placeholder=p.ph; }
}

function cfgProv(){
  if(typeof ONB_PROVIDERS === 'undefined') return;
  var p=ONB_PROVIDERS.filter(function(x){return x.id===$('cprov').value;})[0];
  if(!p) return;
  if(p.url) $('curl').value=p.url;
  if(p.model) $('cmod').value=p.model;
  $('cprov-help').textContent=p.help;
  $('ckey').placeholder=p.key?(p.ph||'votre clé API'):'aucune clé nécessaire';
  $('cfg-models').innerHTML='';
}

async function saveCfg(){
  var model=$('cmod').value.trim();
  var url=$('curl').value.trim();
  if(!model){ toast('⚠ Indiquez un modèle — ou cliquez sur « Charger les modèles »',5000); return; }
  if(!url){ toast('⚠ Indiquez l\\'URL du service',5000); return; }
  var u={model:model,workspace:$('cws').value,base_url:url};
  var k=$('ckey').value;if(k)u.api_key=k;
  await post('/api/config',u); closeCfg(); toast('✓ Paramètres sauvegardés'); loadDir(u.workspace);
}"""

HTML_EDITS = [
    (OLD_KEY_FIELD, NEW_KEY_FIELD, "Champ clé générique + sélecteur de fournisseur"),
    (OLD_MODEL_FIELD, NEW_MODEL_FIELD, "Modèle : champ texte + datalist (fin du select figé)"),
    (OLD_PLACEHOLDER, NEW_PLACEHOLDER, "openCfg : placeholder dynamique"),
    (OLD_FILL, NEW_FILL, "openCfg : plus de valeurs FantasyAI en dur"),
    (OLD_LOADMODS, NEW_LOADMODS, "loadMods : remplit la datalist"),
    (OLD_SAVE, NEW_SAVE, "saveCfg : refuse un modèle vide + helpers fournisseur"),
]


def patch_html(src):
    report, out, failed = [], src, False
    for anchor, repl, label in HTML_EDITS:
        n = out.count(anchor)
        if n != 1:
            report.append(("✗", label, "ancre introuvable" if n == 0 else "%d occurrences" % n))
            failed = True
            continue
        out = out.replace(anchor, repl)
        report.append(("✓", label, "1 remplacement"))
    return out, report, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    html_f = Path(args.dir).resolve() / "ui.html"
    if not html_f.exists():
        print("✗ Introuvable : %s" % html_f)
        return 1

    src = html_f.read_text(encoding="utf-8")
    if "SB_ONBOARD_PATCH" not in src:
        print("✗ patch_onboarding.py n'a pas été appliqué. Lancez-le d'abord.")
        return 1
    if MARKER in src:
        print("⚠ Déjà appliqué. Rien à faire.")
        return 0

    out, report, failed = patch_html(src)

    print("\n── ui.html " + "─" * 50)
    for mark, label, detail in report:
        print("  %s %-52s %s" % (mark, label, detail))

    if failed:
        print("\n✗ ABANDON — rien n'a été écrit.")
        print("  Envoyez-moi les lignes ✗ telles qu'elles sont dans votre ui.html.")
        return 2
    if args.dry_run:
        print("\n(--dry-run : aucun fichier modifié)")
        return 0

    shutil.copy2(html_f, html_f.with_suffix(".html.bak3"))
    html_f.write_text(out, encoding="utf-8")
    print("\n✓ Patch appliqué.  Sauvegarde : ui.html.bak3")
    print("  Rechargez la page (Ctrl+Maj+R), puis ⚙ Paramètres.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
