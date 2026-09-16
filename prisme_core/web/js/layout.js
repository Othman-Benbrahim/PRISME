// ══════════════════════════════════════════════════
//  TOGGLE CARTE + DIVISEUR
// ══════════════════════════════════════════════════
function toggleMM(){
  MM_VISIBLE=!MM_VISIBLE;
  $('mm-col').classList.toggle('hidden',!MM_VISIBLE);
  $('divbar').style.display=MM_VISIBLE?'block':'none';
  $('btn-mm').textContent=MM_VISIBLE?'◀ Carte':'▶ Carte';
  if(MM_VISIBLE)setTimeout(function(){if(ACTIVE)fitView();},60);
}
(function(){
  var drag=false,startX,startW;
  $('divbar').addEventListener('mousedown',function(e){
    drag=true;startX=e.clientX;startW=$('mm-col').offsetWidth;
    $('divbar').classList.add('dragging');document.body.style.cursor='col-resize';document.body.style.userSelect='none';
  });
  document.addEventListener('mousemove',function(e){
    if(!drag)return;
    var w=Math.max(140,Math.min(700,startW+(startX-e.clientX)));
    $('mm-col').style.width=w+'px';$('mm-col').style.transition='none';
  });
  document.addEventListener('mouseup',function(){
    if(!drag)return;drag=false;
    $('divbar').classList.remove('dragging');$('mm-col').style.transition='';
    document.body.style.cursor='';document.body.style.userSelect='';
  });
})();

