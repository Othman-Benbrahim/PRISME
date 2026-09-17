// ══════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════
function $(id){ return document.getElementById(id); }
var HC = {'Content-Type':'application/json'};
async function post(url,d){ var r=await fetch(url,{method:'POST',headers:HC,body:JSON.stringify(d)}); return r.json(); }
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function eu(s){ return encodeURIComponent(s); }

// Ouvre une reponse JSON de l'API dans un nouvel onglet (le jeton est ajoute par token.js)
async function openJson(url){
  var w=window.open('','_blank');
  try{
    var r=await fetch(url); var t=await r.text();
    try{ t=JSON.stringify(JSON.parse(t),null,2); }catch(e){}
    if(w){ w.document.title=url; var pre=w.document.createElement('pre'); pre.textContent=t; w.document.body.appendChild(pre); }
  }catch(e){ if(w) w.close(); toast('⚠ '+e); }
}

// Signale les plugins dont un hook a echoue ou a depasse son delai
function reportHooks(r){
  if(!r || !r.hooks || !r.hooks.length) return;
  var msg=r.hooks.map(function(h){return h.plugin+' ('+(h.probleme==='delai'?'trop lent':'erreur')+')';}).join(', ');
  setTimeout(function(){ toast('⚠ Plugin : '+msg, 5000); }, 1200);
}

function toast(msg,d){
  d=d||2800; var t=$('toast'); t.textContent=msg; t.classList.add('v');
  clearTimeout(t._t); t._t=setTimeout(function(){t.classList.remove('v');},d);
}

// ══════════════════════════════════════════════════
//  ÉTAT
// ══════════════════════════════════════════════════
var TABS={}, ACTIVE=null, EDITOR_MODE='edit';
var MM_VISIBLE=true, ACTIVE_MM_TAB=0;
var FILE_ITEMS=[], CUR_DIR='', TAG_FILTER=null, TAGS_DATA=[];
var CTX_IDX=-1, FAIRES=null, SEL_RESULT=null;
var GRAPH_DATA=null, GRAPH_MODE='force';

