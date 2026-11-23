// Shared anchored D3 force layout for the HTML viewer and PNG.
function faceLayout(points,size,avoidOverlap=true,showLabels=true){
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),scale=Math.min(900/(Math.max(...xs)-Math.min(...xs)),710/(Math.max(...ys)-Math.min(...ys)));
 const cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2;
 const anchors=points.map(p=>[550+(p[0]-cx)*scale,440-(p[1]-cy)*scale]);
 if(!avoidOverlap)return {anchors,pos:anchors.map(p=>p.slice())};
 const offsetY=0; // Labels do not enlarge the collision envelope.
 const nodes=anchors.map((a,i)=>({id:i,x:a[0],y:a[1]+offsetY,ax:a[0],ay:a[1]+offsetY}));
 // Start at the actual projection. Position forces tether each card to its
 // own UMAP coordinate; collision is the only force pushing cards apart.
 const radius=(size+4)*Math.SQRT1_2+1; // Circumscribe only the photo and its frame.
 d3.forceSimulation(nodes)
  .force('x',d3.forceX(d=>d.ax).strength(.28))
  .force('y',d3.forceY(d=>d.ay).strength(.28))
  .force('collide',d3.forceCollide(radius).strength(1).iterations(6))
  .velocityDecay(.4).alphaDecay(.025).stop().tick(360);
 const pos=nodes.map(d=>[d.x,d.y-offsetY]);
 return {anchors,pos};
}
