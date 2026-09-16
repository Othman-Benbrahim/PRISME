// ══════════════════════════════════════════════════
//  TAGS
// ══════════════════════════════════════════════════
async function loadTags(){
  var d=await fetch('/api/tags?dir='+eu(CUR_DIR)).then(function(r){return r.json();});
  TAGS_DATA=d.tags||[];
  var cloud=$('tagcloud');
  if(!TAGS_DATA.length){cloud.innerHTML='<div style="padding:6px 4px;font-size:11px;color:var(--tx2)">Aucun #tag trouvé</div>';return;}
  cloud.innerHTML=TAGS_DATA.map(function(t){
    return '<span class="tg'+(TAG_FILTER===t.tag?' act':'')+'" onclick="filterByTag(\''+t.tag+'\')">#'+esc(t.tag)+' <sup>'+t.count+'</sup></span>';
  }).join('');
}
function filterByTag(tag){
  TAG_FILTER=tag;
  $('tf-label').textContent='#'+tag;
  $('tag-filter-bar').style.display='flex';
  renderFileList(tag);
  document.querySelectorAll('.tg').forEach(function(el){ el.classList.toggle('act',el.textContent.includes('#'+tag)); });
}
function clearTagFilter(){
  TAG_FILTER=null; $('tag-filter-bar').style.display='none';
  document.querySelectorAll('.tg').forEach(function(el){el.classList.remove('act');});
  renderFileList(null);
}
function toggleTagSect(){
  $('tag-sect').classList.toggle('collapsed');
}

