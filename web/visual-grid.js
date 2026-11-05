/* Viewport-only nominal 250 m grid. This does not increase weather resolution. */
(function(root){
  'use strict';
  function grid(bounds, latitude, spacing=250) {
    const dy=spacing/111320, dx=dy/Math.cos(latitude*Math.PI/180);
    const west=bounds[0],south=bounds[1],east=bounds[2],north=bounds[3];
    const features=[];
    // Bound the work even if a caller supplies the national extent.
    if(Math.ceil((east-west)/dx)+Math.ceil((north-south)/dy)>600)return {type:'FeatureCollection',features};
    const line=coordinates=>features.push({type:'Feature',properties:{},geometry:{type:'LineString',coordinates}});
    for(let i=Math.ceil(west/dx);i*dx<=east;i++)line([[i*dx,south],[i*dx,north]]);
    for(let i=Math.ceil(south/dy);i*dy<=north;i++)line([[west,i*dy],[east,i*dy]]);
    return {type:'FeatureCollection',features};
  }
  function attach(map){
    const empty={type:'FeatureCollection',features:[]};
    map.addSource('visual-grid',{type:'geojson',data:empty});
    map.addLayer({id:'visual-grid',type:'line',source:'visual-grid',minzoom:12,
      paint:{'line-color':'#254c3c','line-width':0.5,'line-opacity':0.35}});
    const update=()=>{
      const b=map.getBounds(),latitude=map.getCenter().lat;
      map.getSource('visual-grid').setData(map.getZoom()<12?empty:grid([b.getWest(),b.getSouth(),b.getEast(),b.getNorth()],latitude));
    };
    map.on('moveend',update);update();
  }
  root.VisualGrid={grid,attach};
  if(typeof module!=='undefined')module.exports=root.VisualGrid;
})(typeof globalThis!=='undefined'?globalThis:this);
