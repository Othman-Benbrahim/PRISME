// ══════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════
async function init(){
  var cfg=await fetch('/api/config').then(function(r){return r.json();});
  loadDir(cfg.workspace||'');
  renderTabBar(); showNoFile();
  window.addEventListener('resize',function(){if(ACTIVE)renderMM(null,false);});
  document.addEventListener('click',function(e){
    if(!e.target.closest('#ctx')) hideCtx();
    if(e.target===$('mcfg')) closeCfg();
    if(e.target===$('msearch')) closeSearch();
    if(e.target===$('mgraph')) closeGraph();
    if(e.target===$('msyn')) closeSyn();
    if(!e.target.closest('#sel-bar')&&!e.target.closest('#md-editor')) hideSelBar();
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'){hideCtx();closeCfg();closeSearch();closeGraph();closeSyn();hideSelBar();}
    if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();saveFile();}
    if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key==='F'){e.preventDefault();openSearch();}
  });
}
init();
