// ══════════════════════════════════════════════════
//  GRAPHE DE DOSSIER
// ══════════════════════════════════════════════════
async function openGraph(dir){
  var d=dir||CUR_DIR; if(!d) return;
  $('graph-title').textContent='Graphe — '+d.split(/[/\\]/).pop();
  $('mgraph').classList.add('on');
  GRAPH_DATA=null; GRAPH_MODE='force';
  $('gbt-force').classList.add('on'); $('gbt-tree').classList.remove('on');
  $('graph-svg').innerHTML='';
  $('graph-tooltip').style.display='none';
  var data=await fetch('/api/files/graph?dir='+eu(d)).then(function(r){return r.json();});
  if(data.error){toast('⚠ '+data.error);return;}
  GRAPH_DATA=data;
  renderForceGraph(data);
}
function closeGraph(){ $('mgraph').classList.remove('on'); }
function switchGraph(mode){
  GRAPH_MODE=mode;
  $('gbt-force').classList.toggle('on',mode==='force');
  $('gbt-tree').classList.toggle('on',mode==='tree');
  if(!GRAPH_DATA) return;
  $('graph-svg').innerHTML=''; $('graph-tooltip').style.display='none';
  if(mode==='force') renderForceGraph(GRAPH_DATA);
  else renderFolderTree(GRAPH_DATA);
}

function renderForceGraph(data){
  var wrap=$('graph-wrap'),W=wrap.clientWidth,H=wrap.clientHeight;
  var svg=d3.select('#graph-svg').attr('width',W).attr('height',H);
  var g=svg.append('g');
  var zoom=d3.zoom().scaleExtent([.1,8]).on('zoom',function(e){g.attr('transform',e.transform);});
  svg.call(zoom);
  var nodes=data.nodes.map(function(n){return Object.assign({},n);});
  var nodeMap={};nodes.forEach(function(n){nodeMap[n.id]=n;});
  var links=data.links.filter(function(l){return nodeMap[l.source]&&nodeMap[l.target];})
    .map(function(l){return {source:nodeMap[l.source],target:nodeMap[l.target]};});
  var maxDeg=Math.max(1,d3.max(nodes,function(n){return n.degree||0;}));
  var colScale=d3.scaleSequential([0,maxDeg],d3.interpolateBlues);
  var sim=d3.forceSimulation(nodes)
    .force('link',d3.forceLink(links).distance(100).strength(.3))
    .force('charge',d3.forceManyBody().strength(-180))
    .force('center',d3.forceCenter(W/2,H/2))
    .force('col',d3.forceCollide().radius(function(d){return (d.degree||0)*2+22;}));
  var link=g.append('g').selectAll('line').data(links).enter().append('line')
    .attr('stroke','#1e2a3d').attr('stroke-width',1.5).attr('opacity',.7);
  var node=g.append('g').selectAll('.gn').data(nodes).enter().append('g').attr('class','gn')
    .call(d3.drag().on('start',function(e,d){if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y;})
      .on('drag',function(e,d){d.fx=e.x;d.fy=e.y;})
      .on('end',function(e,d){if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}));
  node.append('circle')
    .attr('r',function(d){return Math.max(7,Math.min(22,(d.degree||0)*2.5+8));})
    .attr('fill',function(d){return colScale(d.degree||0);})
    .attr('stroke','#0d1117').attr('stroke-width',1.5).style('cursor','pointer')
    .on('mouseover',function(e,d){
      var tt=$('graph-tooltip'); tt.style.display='block';
      tt.textContent=d.name+' ('+d.degree+' lien'+(d.degree!==1?'s':'')+')';
      tt.style.left=(e.clientX-wrap.getBoundingClientRect().left+12)+'px';
      tt.style.top=(e.clientY-wrap.getBoundingClientRect().top-10)+'px';
    })
    .on('mouseout',function(){$('graph-tooltip').style.display='none';})
    .on('click',async function(e,d){
      var r=await fetch('/api/files/read?path='+eu(d.path)).then(function(r){return r.json();});
      if(r.error){toast('⚠ '+r.error);return;}
      openFileTab(d.path,r.content); closeGraph();
    });
  node.append('text').attr('dy','0.35em').attr('text-anchor','middle')
    .attr('fill','#e2e8f0').attr('font-size','9px').attr('font-family',"'DM Sans',sans-serif")
    .style('pointer-events','none')
    .text(function(d){return d.name.length>10?d.name.slice(0,10)+'…':d.name;});
  sim.on('tick',function(){
    link.attr('x1',function(d){return d.source.x;}).attr('y1',function(d){return d.source.y;})
      .attr('x2',function(d){return d.target.x;}).attr('y2',function(d){return d.target.y;});
    node.attr('transform',function(d){return 'translate('+d.x+','+d.y+')';});
  });
}

function renderFolderTree(data){
  var wrap=$('graph-wrap'),W=wrap.clientWidth,H=wrap.clientHeight;
  var svg=d3.select('#graph-svg').attr('width',W).attr('height',H);
  var g=svg.append('g');
  svg.call(d3.zoom().scaleExtent([.05,5]).on('zoom',function(e){g.attr('transform',e.transform);}));
  var folderName=($('graph-title').textContent||'').replace('Graphe — ','');
  var root={name:folderName,children:data.nodes};
  var h=d3.hierarchy(root,function(d){return d.children;});
  var NW=150,NH=32;
  d3.tree().nodeSize([NH+12,NW+60]).separation(function(a,b){return a.parent===b.parent?1.2:1.8;})(h);
  var ns=h.descendants(),ls=h.links();
  g.selectAll('path').data(ls).enter().append('path')
    .attr('d',d3.linkHorizontal().x(function(d){return d.y;}).y(function(d){return d.x;}))
    .attr('fill','none').attr('stroke','#1e2a3d').attr('stroke-width',1.5);
  var ng=g.selectAll('g').data(ns).enter().append('g')
    .attr('transform',function(d){return 'translate('+d.y+','+d.x+')';});
  ng.append('rect').attr('x',-NW/2).attr('y',-NH/2).attr('width',NW).attr('height',NH).attr('rx',7)
    .attr('fill',function(d){return d.depth===0?'#2563eb22':d.data.degree>0?'#059669aa':'#1e2a3d';})
    .attr('stroke',function(d){return d.depth===0?'#2563eb':d.data.degree>0?'#059669':'#283856';})
    .attr('stroke-width',1).style('cursor',function(d){return d.depth>0?'pointer':'default';})
    .on('click',async function(e,d){
      if(d.depth===0||!d.data.path) return;
      var r=await fetch('/api/files/read?path='+eu(d.data.path)).then(function(r){return r.json();});
      if(r.error){toast('⚠ '+r.error);return;}
      openFileTab(d.data.path,r.content); closeGraph();
    });
  ng.append('text').attr('dy','0.35em').attr('text-anchor','middle')
    .attr('fill','#c4d0e4').attr('font-size','11px').attr('font-family',"'DM Sans',sans-serif")
    .style('pointer-events','none')
    .text(function(d){return d.depth===0?d.data.name:(d.data.name.length>16?d.data.name.slice(0,16)+'…':d.data.name);});
  // Auto-fit
  var ys=ns.map(function(d){return d.y;}),xs=ns.map(function(d){return d.x;});
  var y0=Math.min.apply(null,ys)-NW/2-20,y1=Math.max.apply(null,ys)+NW/2+20;
  var x0=Math.min.apply(null,xs)-NH-20,x1=Math.max.apply(null,xs)+NH+20;
  var sc=Math.min(.9,Math.min(W/(y1-y0),H/(x1-x0)));
  svg.call(d3.zoom().transform,d3.zoomIdentity.translate(W/2-sc*(y0+y1)/2,H/2-sc*(x0+x1)/2).scale(sc));
}

