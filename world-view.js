// Geographic anchors describe source labels, never inferred face origins.
let worldTransform=d3.zoomIdentity;
function hullLayer(parent,points,assignment,padding){
 if(!$('hulls').checked)return;
 const layer=el('g',{class:'cluster-hulls','pointer-events':'none'},parent);
 for(let c=0;c<+$('k').value;c++){
  const expanded=[];
  points.forEach((p,i)=>{if(assignment[i]===c)for(let a=0;a<16;a++){const t=a*Math.PI/8,r=Array.isArray(padding)?padding[i]:padding;expanded.push([p[0]+Math.cos(t)*r,p[1]+Math.sin(t)*r]);}});
  const hull=d3.polygonHull(expanded);if(!hull)continue;
  el('path',{class:'cluster-hull',d:d3.line().curve(d3.curveCatmullRomClosed.alpha(.5))(hull),fill:D.colors[c],'fill-opacity':.10,stroke:D.colors[c],'stroke-opacity':.32,'stroke-width':1.2,'data-cluster':c+1},layer);
 }
}
function closest(i,count=5){
 return D.records.map((r,j)=>({id:j,cosine_similarity:D.similarities[i][j]})).filter(n=>n.id!==i).sort((a,b)=>b.cosine_similarity-a.cosine_similarity||a.id-b.id).slice(0,count);
}
const FIRST_NEIGHBORS=D.records.map((_,i)=>closest(i,1)[0]);
const NEAREST_GRAPH_EDGES=FIRST_NEIGHBORS.map((n,source)=>({
 source,target:n.id,similarity:n.cosine_similarity,rank:1,primary:true,
 mutual:FIRST_NEIGHBORS[n.id].id===source
}));
// One domain for every view: all pairs eligible for the top-10 link option.
const LINK_COLOR_DOMAIN=d3.extent(D.records.flatMap((_,i)=>closest(i,10).map(n=>n.cosine_similarity)));
const linkColor=d3.scaleSequential(d3.interpolateYlGnBu).domain(LINK_COLOR_DOMAIN).clamp(true);
function cardPositions(anchors,size,showLabels,ticks=360,sizes=null){
 if(!$('repel').checked)return anchors.map(a=>a.slice());
 const offset=0,nodes=anchors.map((a,i)=>({x:a[0],y:a[1]+offset,ax:a[0],ay:a[1]+offset,r:((sizes?sizes[i]:size)+3)*Math.SQRT1_2+1}));
 d3.forceSimulation(nodes).force('x',d3.forceX(d=>d.ax).strength(.4)).force('y',d3.forceY(d=>d.ay).strength(.4))
  .force('collision',d3.forceCollide(d=>d.r).iterations(6)).velocityDecay(.4).alphaDecay(.025).stop().tick(ticks);
 return nodes.map(n=>[n.x,n.y-offset]);
}
function drawSimilarityLinks(parent,points,neighbors,sizes=null){
 const graphMode=$('nearestGraph').checked;
 const edges=graphMode?NEAREST_GRAPH_EDGES:neighbors.map((n,index)=>({source:selected,target:n.id,similarity:n.cosine_similarity,rank:index+1,primary:index===0,mutual:index===0&&FIRST_NEIGHBORS[n.id].id===selected}));
 if(!edges.length)return;
 const defs=el('defs',{},parent);
 [...edges].sort((a,b)=>a.similarity-b.similarity).forEach(edge=>{
  const a=points[edge.source],b=points[edge.target],dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy)||1;
  // Reciprocal arrows use the same signed bend in opposite directions,
  // putting them on opposite sides of the pair rather than on the same path.
  const bend=(graphMode&&edge.mutual?12:Math.min(60,Math.max(15,length*.16)))*((edge.source+edge.target)%2?-1:1);
  const control=[(a[0]+b[0])/2-dy/length*bend,(a[1]+b[1])/2+dx/length*bend];
  const directed=graphMode||(edge.primary&&!edge.mutual),color=linkColor(edge.similarity);
  let end=b,curveControl=control;
  if(directed){
   // Keep each arrowhead just outside its target portrait at every zoom level.
   const targetSize=sizes?sizes[edge.target]:Math.round(+$('size').value*.68);
   const half=$('worldphotos').checked?targetSize/2+4:7;
   const point=t=>[(1-t)**2*a[0]+2*(1-t)*t*control[0]+t*t*b[0],(1-t)**2*a[1]+2*(1-t)*t*control[1]+t*t*b[1]];
   let lo=0,hi=1;
   for(let step=0;step<32;step++){const t=(lo+hi)/2,q=point(t);if(Math.abs(q[0]-b[0])<=half&&Math.abs(q[1]-b[1])<=half)hi=t;else lo=t;}
   const t=(lo+hi)/2;end=point(t);curveControl=[a[0]+t*(control[0]-a[0]),a[1]+t*(control[1]-a[1])];
  }
  if(directed){
   // The path ends at the arrow's base, not at its tip. Keep the tip at the
   // already-clipped target position without letting the thick shaft fill it.
   const arrowLength=8,tx=end[0]-curveControl[0],ty=end[1]-curveControl[1],tangentLength=Math.hypot(tx,ty)||1;
   end=[end[0]-tx/tangentLength*arrowLength,end[1]-ty/tangentLength*arrowLength];
  }
  const attrs={class:'similarity-link',d:`M${a[0]},${a[1]}Q${curveControl[0]},${curveControl[1]} ${end[0]},${end[1]}`,stroke:color,'stroke-opacity':.9,'stroke-linecap':'butt','stroke-width':graphMode?2.2:edge.primary?3.2:1.7,'data-rank':edge.rank,'data-source':edge.source,'data-target':edge.target,'data-similarity':edge.similarity,'data-directed':directed,'data-mutual':edge.mutual,'data-graph':graphMode};
  if(directed){
   const id=`similarity-arrow-${edge.source}-${edge.target}`;
   const marker=el('marker',{id,viewBox:'-1 -1 10 10',refX:0,refY:4,markerWidth:10,markerHeight:10,markerUnits:'userSpaceOnUse',orient:'auto'},defs);
   el('path',{d:'M0,0L8,4L0,8Z',fill:color,'fill-opacity':.9,stroke:'none','shape-rendering':'geometricPrecision'},marker);attrs['marker-end']=`url(#${id})`;
  }
  const line=el('path',attrs,parent),relation=directed?'→':edge.mutual?'↔':'—';
  el('title',{},line).textContent=`${D.records[edge.source].label} ${relation} ${D.records[edge.target].label} · Cosine similarity ${edge.similarity.toFixed(3)}${edge.mutual?' · Mutual nearest neighbors':''}`;
 });
}
function renderWorld(){
 const svg=$('map');svg.replaceChildren();svg.setAttribute('viewBox','-60 -35 1220 720');svg.setAttribute('aria-label','World map of face similarities');
 const graphMode=$('nearestGraph').checked,k=$('k').value,assignment=D.clusters[k],labels=$('labels').checked,size=Math.round(+$('size').value*.68);
 const projection=d3.geoNaturalEarth1().rotate([-10,0]).fitExtent([[24,28],[1076,575]],WORLD),path=d3.geoPath(projection);
 const layer=el('g',{class:'world-layer',transform:worldTransform.toString()},svg);
 el('path',{d:path({type:'Sphere'}),fill:'#edf1ef',stroke:'none'},layer);
 WORLD.features.forEach(f=>el('path',{d:path(f),fill:'#fafbf8',stroke:'#d5dcd5','stroke-width':.65,'vector-effect':'non-scaling-stroke'},layer));
 const geographicAnchors=D.records.map(r=>projection(GEO[r.label].coordinates));
 // Only geographic geometry inherits the zoom transform. Cards and labels
 // are drawn in screen coordinates, at a constant size, after zooming anchors.
 const hullHost=el('g',{class:'world-hull-overlay'},svg);
 const neighbors=linksVisible?closest(selected,+$('edges').value):[];
 const connected=new Set(graphMode?NEAREST_GRAPH_EDGES.flatMap(edge=>edge.source===selected?[edge.target]:edge.target===selected?[edge.source]:[]):neighbors.map(n=>n.id));
 const near=new Set([selected,...connected]);
 const photoSizes=D.records.map((_,i)=>Math.round(size*(selectionActive?(i===selected?1.8:connected.has(i)?1.4:1):1)));
 const links=el('g',{class:'similarity-links',fill:'none','pointer-events':'none'},svg);
 const markers=el('g',{class:'world-markers'},svg),photos=el('g',{class:'world-photos'},svg);
 function drawOverlays(ticks=360){
 if(!photos.isConnected)return;
 const anchors=geographicAnchors.map(a=>worldTransform.apply(a));
 const pos=cardPositions(anchors,size,labels,ticks,photoSizes);
 hullHost.replaceChildren();links.replaceChildren();markers.replaceChildren();photos.replaceChildren();
 hullLayer(hullHost,$('worldphotos').checked?pos:anchors,assignment,$('worldphotos').checked?photoSizes.map(s=>s/2+14):12);
 const imageDefs=el('defs',{},photos);
 const grayscale=el('filter',{id:'world-grayscale','color-interpolation-filters':'sRGB'},imageDefs);
 el('feColorMatrix',{type:'saturate',values:0},grayscale);
 drawSimilarityLinks(links,$('worldphotos').checked?pos:anchors,neighbors,photoSizes);
 D.records.forEach((r,i)=>{
  const a=anchors[i],p=pos[i],photoSize=photoSizes[i],active=graphMode||near.has(i),color=D.colors[assignment[i]];
  if($('worldphotos').checked&&linksVisible){
   el('line',{x1:a[0],y1:a[1],x2:p[0],y2:p[1],stroke:'#9ca3af','stroke-opacity':.3,'stroke-width':.65,'vector-effect':'non-scaling-stroke'},markers);
  }
  const dot=el('circle',{class:'geo-anchor',cx:a[0],cy:a[1],r:selectionActive&&i===selected?5:active?4:2.6,fill:active?'#245d60':'#82948b',stroke:'#fff','stroke-width':.7,tabindex:0,role:'button','aria-label':r.label},markers);
  const g=el('g',{class:$('worldphotos').checked?'node geo-node':'geo-marker',tabindex:0,role:'button','aria-label':r.label,'aria-pressed':selectionActive&&i===selected,'data-id':i,opacity:1},photos);
  if($('worldphotos').checked){
   const radius=Math.min(14,photoSize*.22),clipId=`world-face-clip-${i}`;
   const clip=el('clipPath',{id:clipId,clipPathUnits:'userSpaceOnUse'},imageDefs);
   el('rect',{x:p[0]-photoSize/2,y:p[1]-photoSize/2,width:photoSize,height:photoSize,rx:radius},clip);
   el('rect',{class:'photo-frame',x:p[0]-photoSize/2-1.5,y:p[1]-photoSize/2-1.5,width:photoSize+3,height:photoSize+3,rx:radius+1.5,fill:'#fff',stroke:selectionActive&&i===selected?'#52616a':'none','stroke-width':selectionActive&&i===selected?2:0},g);
   el('image',{href:r.image,x:p[0]-photoSize/2,y:p[1]-photoSize/2,width:photoSize,height:photoSize,'clip-path':`url(#${clipId})`,filter:linksVisible&&!active?'url(#world-grayscale)':'none'},g);
  }
  if(labels&&($('worldphotos').checked||active)){
   const text=el('text',{x:($('worldphotos').checked?p[0]:a[0]),y:($('worldphotos').checked?p[1]+photoSize/2+10:a[1]+13),'text-anchor':'middle',style:'font-size:8px;fill:#3f4d46;paint-order:stroke;stroke:#f6f5f1;stroke-width:2px'},g);
   const words=r.label.replace('/','/ ').split(' '),chunks=[];let line='';
   for(const w of words){if(line&&(line+' '+w).length>10){chunks.push(line);line=w;}else line+=(line?' ':'')+w;}if(line)chunks.push(line);
   chunks.forEach((t,j)=>el('tspan',{x:$('worldphotos').checked?p[0]:a[0],dy:j?9:0},text).textContent=t);
  }
  const info=`${r.label} · Cluster ${assignment[i]+1}\nCosine similarity to ${D.records[selected].label}: ${D.similarities[selected][i].toFixed(3)}`;
  el('title',{},g).textContent=info;if(g!==dot)el('title',{},dot).textContent=info;
  for(const target of new Set([g,dot])){
   // Selecting a face must not start the map's mouse/touch drag gesture.
   target.onmousedown=e=>e.stopPropagation();
   target.ontouchstart=e=>e.stopPropagation();
   target.ondblclick=e=>e.stopPropagation();
   target.onclick=e=>{e.stopPropagation();select(i);};
   target.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();select(i);}};
  }
 });
 // The final SVG sibling paints on top, even after zoom redraws the cards.
 const selectedPhoto=photos.querySelector(`[data-id="${selected}"]`);
 if(selectionActive&&selectedPhoto)photos.appendChild(selectedPhoto);
 }
 drawOverlays();
 let overlayFrame=null,zoomMoved=false;
 const zoom=d3.zoom().clickDistance(5).scaleExtent([.9,9]).extent([[-60,-35],[1160,685]])
  .on('start',()=>{zoomMoved=false;})
  .on('zoom',e=>{
   zoomMoved=true;
   worldTransform=e.transform;
   layer.setAttribute('transform',worldTransform.toString());
   if(overlayFrame===null)overlayFrame=requestAnimationFrame(()=>{overlayFrame=null;drawOverlays(160);});
  })
  .on('end',()=>{if(!zoomMoved)return;if(overlayFrame!==null){cancelAnimationFrame(overlayFrame);overlayFrame=null;}drawOverlays();});
 d3.select(svg).call(zoom);svg.__zoom=worldTransform;
 sidebar();
}
