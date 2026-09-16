// ══════════════════════════════════════════════════
//  MINDMAP D3 (structure fichier)
// ══════════════════════════════════════════════════
var SVG_MM=d3.select('#mm'), G_MM=SVG_MM.append('g');
var ZT=d3.zoomIdentity;
var ZB=d3.zoom().scaleExtent([.04,8]).on('zoom',function(e){G_MM.attr('transform',e.transform);ZT=e.transform;});
SVG_MM.call(ZB);
var COLS=['#6d28d9','#2563eb','#0369a1','#065f46','#92400e','#9d174d','#4338ca'];
var NW=165,NH=38;
function gc(d){return COLS[d.depth%COLS.length];}
function trn(s,n){s=s||'';return s.length>n?s.slice(0,n)+'…':s;}

function updateMindmap(md,filename){
  var tree=mdToTree(md,filename); renderMM(tree,true);
  $('mm-title').textContent=filename||'Structure';
}
function mdToTree(md,filename){
  var root={id:'r',title:'📄 '+(filename||'Fichier'),content:'',children:[],collapsed:false};
  var stack=[{n:root,l:0}],buf=[];
  function flush(){var t=buf.join('\n').trim();if(t)stack[stack.length-1].n.content=t;buf=[];}
  (md||'').split('\n').forEach(function(line){
    var m=line.match(/^(#{1,6})\s+(.+)$/);
    if(m){flush();var l=m[1].length,t=m[2].trim();
      while(stack.length>1&&stack[stack.length-1].l>=l)stack.pop();
      var n={id:'n'+Math.random().toString(36).slice(2),title:t,content:'',children:[],collapsed:false};
      stack[stack.length-1].n.children.push(n);stack.push({n:n,l:l});
    }else buf.push(line);
  });
  flush();return root;
}
function renderMM(tree,fit){
  if(!tree) return;
  var ct=$('mm-wrap'),W=ct.clientWidth,H=ct.clientHeight;
  SVG_MM.attr('width',W).attr('height',H); G_MM.selectAll('*').remove();
  var root=d3.hierarchy(tree,function(d){return d.collapsed?[]:(d.children||[]);});
  d3.tree().nodeSize([NH+18,NW+70]).separation(function(a,b){return a.parent===b.parent?1.2:1.8;})(root);
  var ns=root.descendants(),ls=root.links();
  G_MM.selectAll('.lk').data(ls).enter().append('path').attr('class','lk')
    .attr('d',d3.linkHorizontal().x(function(d){return d.y;}).y(function(d){return d.x;}))
    .attr('fill','none').attr('stroke','#1a2640').attr('stroke-width',1.8).attr('opacity',.9);
  var ng=G_MM.selectAll('.ng').data(ns).enter().append('g').attr('class','ng')
    .attr('transform',function(d){return 'translate('+d.y+','+d.x+')';});
  function hk(d){return !!(d.data.children&&d.data.children.length);}
  ng.append('rect').attr('x',-NW/2).attr('y',-NH/2).attr('width',NW).attr('height',NH).attr('rx',8)
    .attr('fill',function(d){return gc(d)+'22';}).attr('stroke',function(d){return gc(d);})
    .attr('stroke-width',1).style('cursor','default');
  ng.append('text').attr('dy','0.35em').attr('text-anchor','middle')
    .attr('fill','#c4d0e4').attr('font-size','11.5px').attr('font-weight','500')
    .attr('font-family',"'DM Sans',system-ui,sans-serif").style('pointer-events','none')
    .text(function(d){return trn(d.data.title,18);});
  ng.filter(function(d){return !!(d.data.content&&d.data.content.trim());})
    .append('circle').attr('cx',NW/2-9).attr('cy',-NH/2+8).attr('r',3)
    .attr('fill',function(d){return gc(d);}).attr('opacity',.65).style('pointer-events','none');
  var wk=ng.filter(hk);
  wk.append('circle').attr('cx',NW/2+12).attr('cy',0).attr('r',9)
    .attr('fill','#0d1117').attr('stroke','#283856').style('cursor','pointer')
    .on('click',function(e,d){e.stopPropagation();d.data.collapsed=!d.data.collapsed;renderMM(tree,false);});
  wk.append('text').attr('x',NW/2+12).attr('y',0).attr('dy','0.35em')
    .attr('text-anchor','middle').attr('fill','#6b7a96').attr('font-size','10px')
    .style('pointer-events','none').text(function(d){return d.data.collapsed?'▶':'▼';});
  if(fit) doFit(ns);
}
function doFit(ns){
  var ct=$('mm-wrap'),W=ct.clientWidth,H=ct.clientHeight;
  if(!ns||!ns.length)return;
  var ys=ns.map(function(d){return d.y;}),xs=ns.map(function(d){return d.x;});
  var y0=Math.min.apply(null,ys)-NW/2-30,y1=Math.max.apply(null,ys)+NW/2+50;
  var x0=Math.min.apply(null,xs)-NH-30,x1=Math.max.apply(null,xs)+NH+30;
  var sc=Math.min(.85,Math.min(W/(y1-y0),H/(x1-x0)));
  SVG_MM.call(ZB.transform,d3.zoomIdentity.translate(W/2-sc*(y0+y1)/2,H/2-sc*(x0+x1)/2).scale(sc));
}
function fitView(){
  if(!ACTIVE)return;
  var root=d3.hierarchy(mdToTree($('md-editor').value,ACTIVE.split(/[/\\]/).pop()),function(d){return d.collapsed?[]:(d.children||[]);});
  d3.tree().nodeSize([NH+18,NW+70]).separation(function(a,b){return a.parent===b.parent?1.2:1.8;})(root);
  doFit(root.descendants());
}
function svgZoom(f){SVG_MM.call(ZB.scaleBy,f);}

