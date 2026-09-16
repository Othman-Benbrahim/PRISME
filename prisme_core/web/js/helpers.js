// ══════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════
function $(id){ return document.getElementById(id); }
var HC = {'Content-Type':'application/json'};
async function post(url,d){ var r=await fetch(url,{method:'POST',headers:HC,body:JSON.stringify(d)}); return r.json(); }
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function eu(s){ return encodeURIComponent(s); }

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

