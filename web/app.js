'use strict';
const $ = id => document.getElementById(id);
const modes = {
  score: ['Idoneïtat meteorològica', 0, 100, ' / 100', ['#e1e6d6','#b8c976','#4a8050','#153e35']],
  rain_21d: ['Pluja antecedent · 21 dies',0,150,' mm',['#f2e7c9','#a3c9b9','#5597bb','#253c85']],
  rain_day: ['Precipitació · dia',0,40,' mm',['#f2e7c9','#a3c9b9','#5597bb','#253c85']],
  temperature: ['Temperatura mitjana · 7 dies',-5,30,' °C',['#456aa4','#b8d9c8','#efca7c','#ab463f']],
  humidity: ['Humitat relativa · dia',0,100,' %',['#e9d6a3','#bad5bb','#62ada6','#286482']],
  wind: ['Vent màxim · dia',0,70,' km/h',['#e8e5d8','#abc6bc','#789bb7','#5f4a85']],
  water_balance: ['Pluja − ET₀ · 21 dies',-80,150,' mm',['#b57142','#eee2bd','#8abeb0','#296c77']],
  frost: ['Dies de glaçada · 7 dies',0,7,' dies',['#f0eedc','#c2d4d9','#789eb9','#394b87']],
  elevation: ['Altitud del model meteorològic',0,3000,' m',['#dbe5c8','#9dae78','#958c69','#e8e5dc']],
  none: ['Només cartografia',0,1,'',['#ddd','#ddd','#ddd','#ddd']]
};
function wms(service, layer) {
  return `https://geoserveis.icgc.cat/servei/catalunya/${service}/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=${layer}&STYLES=&FORMAT=image/png&TRANSPARENT=true&SRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256`;
}
const EL=EnvironmentLayers;
const map = new maplibregl.Map({container:'map', center:[-5,37], zoom:4.5, maxZoom:18,
  style:{version:8,sources:{base:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}},
    layers:[{id:'background',type:'background',paint:{'background-color':'#edf0e8'}},{id:'base',type:'raster',source:'base'}]}});
map.addControl(new maplibregl.NavigationControl());
map.addControl(new maplibregl.GeolocateControl({positionOptions:{enableHighAccuracy:true},trackUserLocation:false}));
let manifest, environment, grid, currentScores, revision=0, selected=null, ready=false;
let national, regionRevision=0, dataPath='', inspectionController;
const speciesCache = new Map();
let photos={},photoSpecies=null;
const rasterLayers=new Map([['forest-map','ff_tipo_bosque'],['soil-map','phh2o_0-5cm_mean']]);
function status(text, warn=false) { $('status').textContent=text; $('status').classList.toggle('warn',warn); }
async function json(url) {
  if(url.startsWith('data/regions/')&&!url.endsWith('manifest.json')&&typeof DecompressionStream!=='undefined'){
    const packed=await fetch(url+'.gz');
    if(packed.ok)return new Response(packed.body.pipeThrough(new DecompressionStream('gzip'))).json();
    if(packed.status!==404)throw new Error('HTTP '+packed.status+': '+url);
  }
  const response=await fetch(url);if(!response.ok)throw new Error('HTTP '+response.status+': '+url);return response.json();
}
function option(select, value, label) { const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o); }
function text(tag, value, parent) { const node=document.createElement(tag);node.textContent=value;parent.append(node);return node; }
function baseTiles(id, service, layer) { map.getSource(id).setTiles([wms(service,layer)]); }
map.on('error', e => { if(e.sourceId && e.sourceId!=='cells') status('Una capa cartogràfica no respon. Torna-ho a intentar més tard.',true); });
map.on('load', async () => {
  VisualGrid.attach(map);
  json('species-photos.json').then(value=>{photos=value;if(ready)showPhoto(manifest.species.find(s=>s.id===$('species').value));}).catch(()=>{});
  map.addSource('cover',{type:'raster',tiles:[wms('cobertes-sol','cobertes_2024')],tileSize:256,attribution:'Cobertes del sòl © ICGC'});
  map.addLayer({id:'cover',type:'raster',source:'cover',layout:{visibility:'none'},paint:{'raster-opacity':0.7}});
  for(const [id,endpoint,layer,attribution] of [['forest-map',EL.FOREST,'ff_tipo_bosque','© MITECO · Mapa Forestal de España'],['soil-map',EL.SOIL,'phh2o_0-5cm_mean','© ISRIC SoilGrids · CC BY 4.0']]) {
    map.addSource(id,{type:'raster',tiles:[EL.tile(endpoint,layer)],tileSize:256,maxzoom:id==='soil-map'?11:13,attribution});
    map.addLayer({id,type:'raster',source:id,layout:{visibility:'none'},paint:{'raster-opacity':0.75}});
  }
  EL.forestTypes.forEach(([id,label])=>option($('forest'),id,label));
  try {
    const [catalog,borders]=await Promise.all([json('data/spain.json'),json('data/spain-regions.geojson')]);
    national=catalog;
    catalog.regions.sort((a,b)=>a.name.localeCompare(b.name)).forEach(r=>option($('region'),r.id,r.name));
    map.addSource('regions',{type:'geojson',data:borders});
    map.addLayer({id:'region-hit',type:'fill',source:'regions',paint:{'fill-color':'#386547','fill-opacity':0.015}});
    map.addLayer({id:'region-outline',type:'line',source:'regions',paint:{'line-color':'#386547','line-width':1,'line-opacity':0.5}});
    $('region').disabled=false;$('region').value='ES51';
    $('region').onchange=()=>loadRegion($('region').value,true);
    ['species','date','layer'].forEach(id=>$(id).addEventListener('change',render));
    map.fitBounds([[-18.3,27.5],[4.4,43.9]],{padding:35,duration:0});
    await loadRegion('ES51',false);
  } catch(error) { status(`No s’ha pogut carregar Espanya: ${error.message}`,true); }
});
async function loadRegion(id,focus=true) {
  const token=++regionRevision;++revision;ready=false;currentScores=null;selected=null;
  $('detail').classList.add('hidden');speciesCache.clear();
  if(map.getLayer('conditions'))map.setPaintProperty('conditions','fill-opacity',0);
  ['species','date','layer'].forEach(key=>$(key).disabled=true);
  const region=national.regions.find(r=>r.id===id);if(!region)return;
  $('region').value=id;status(`Carregant ${region.name}…`);
  const previousSpecies=$('species').value,previousDate=$('date').value,previousLayer=$('layer').value;
  try {
    const values=await Promise.all([json(`${region.path}/manifest.json`),json(`${region.path}/environment.json`),json(`${region.path}/grid.geojson`)]);
    if(token!==regionRevision)return;
    [manifest,environment,grid]=values;dataPath=region.path;
    if(grid.features.length!==manifest.cell_count) throw new Error('La malla no coincideix amb les dades');
    ['species','date','layer'].forEach(key=>$(key).replaceChildren());
    manifest.species.forEach(s=>option($('species'),s.id,`${s.common_name} · ${s.scientific_name}`));
    manifest.dates.forEach((d,i)=>option($('date'),i,(d<(manifest.forecast_start||manifest.dates[0])?'Històric · ':'Previsió · ')+new Date(d+'T12:00:00').toLocaleDateString('ca',{weekday:'short',day:'numeric',month:'short'})));
    $('date').value=String(Math.max(0,manifest.dates.indexOf(manifest.forecast_start))); 
    ['score',...manifest.layers,'none'].forEach(k=>option($('layer'),k,modes[k][0]));
    if(previousSpecies)$('species').value=previousSpecies;
    if(previousDate&&Number(previousDate)<manifest.dates.length)$('date').value=previousDate;
    if(previousLayer)$('layer').value=previousLayer;
    if(!map.getSource('cells')) {
      map.addSource('cells',{type:'geojson',data:grid});
      map.addLayer({id:'conditions',type:'fill',source:'cells',paint:{'fill-color':'#ccc','fill-opacity':0}},'region-outline');
    } else {map.removeFeatureState({source:'cells'});map.getSource('cells').setData(grid);}
    map.moveLayer('visual-grid');
    ['species','date','layer'].forEach(key=>$(key).disabled=false);
    $('resolution').textContent=`Regió activa: retícula visual ≈ 250 m en apropar-te · càlcul ${manifest.cell_size_km} km · meteo ${manifest.weather_sampling_degrees}°`;
    const stale = Date.now()-Date.parse(manifest.weather_timestamp)>48*3600*1000;
    $('notice').textContent=stale?'Dades antigues: no les interpretis com una previsió actual.':'Bosc i pH disponibles per consulta; encara no ponderen l’índex. Hores en Europe/Madrid.';
    ready=true;
    if(focus)map.fitBounds([[region.bounds[0],region.bounds[1]],[region.bounds[2],region.bounds[3]]],{padding:50});
    await render();
  } catch(error) {if(token===regionRevision)status(`No s’han pogut carregar les dades de ${region.name}: ${error.message}. Selecciona una altra regió.`,true);}
}
async function render() {
  if(!ready) return;
  const token=++revision, species=$('species').value, day=Number($('date').value), mode=$('layer').value;
  if(mode!=='none'&&($('forest').value!=='off'||$('soil').value!=='off')) {
    $('forest').value='off';$('soil').value='off';
    map.setLayoutProperty('forest-map','visibility','none');map.setLayoutProperty('soil-map','visibility','none');
    $('environment-legend').classList.add('hidden');
  }
  if(national) {
    for(const region of national.regions)map.setFeatureState({source:'regions',id:region.id},{value:region.overview?.[species]?.[day]??0});
    map.setPaintProperty('region-hit','fill-color',['interpolate',['linear'],['coalesce',['feature-state','value'],0],0,'#e1e6d6',33,'#b8c976',66,'#4a8050',100,'#153e35']);
    map.setPaintProperty('region-hit','fill-opacity',mode==='score'?0.5:0.015);
  }
  map.setPaintProperty('conditions','fill-opacity',0);
  $('detail').classList.add('hidden');currentScores=null;
  const profile=manifest.species.find(s=>s.id===species);
  $('profile').textContent=`${profile.habitat}. ${profile.altitude_min}–${profile.altitude_max} m. Mesos: ${profile.months.join(', ')}. Perfil provisional.`;
  showPhoto(profile);
  if(mode==='none'){
    $('legend-title').textContent='Sense capa meteorològica';$('legend-min').textContent='';$('legend-max').textContent='';$('legend-bar').style.background='#ddd';
    status('Cartografia · activa bosc o pH i fes clic per consultar.');return;
  }
  status('Actualitzant condicions…');
  try {
    let result=speciesCache.get(species);
    if(!result) {result=await json(`${dataPath}/${species}.json`);if(token!==revision)return;speciesCache.set(species,result);}
    if(token!==revision) return;
    if(JSON.stringify(result.dates)!==JSON.stringify(manifest.dates) || result.scores[day].length!==manifest.cell_count) throw new Error('Sèrie incompatible');
    const values=mode==='score'?result.scores[day]:environment.days[day][mode];
    if(mode!=='none') {
      for(let start=0;start<manifest.cell_count;start+=1500) {
        if(token!==revision) return;
        for(let i=start;i<Math.min(start+1500,manifest.cell_count);i++) map.setFeatureState({source:'cells',id:i},{value:values[i]});
        await new Promise(requestAnimationFrame);
      }
    }
    if(token!==revision) return;
    currentScores=result.scores[day];
    const [title,min,max,unit,colors]=modes[mode];
    const expression=['interpolate',['linear'],['coalesce',['feature-state','value'],0]];
    colors.forEach((color,i)=>expression.push(min+(max-min)*i/3,color));
    map.setPaintProperty('conditions','fill-color',expression);
    map.setPaintProperty('conditions','fill-opacity',mode==='none'?0:Number($('opacity').value)/100);
    $('legend-title').textContent=title;$('legend-min').textContent=min+unit;$('legend-max').textContent=max+unit;
    $('legend-bar').style.background=`linear-gradient(90deg,${colors.join(',')})`;
    status(`${manifest.species.length} espècies · dades ${manifest.weather_timestamp.slice(0,10)} · ${manifest.legacy_snapshot?'instantània històrica':(manifest.historical_days||0)+' dies d’històric + '+(manifest.dates.length-(manifest.historical_days||0))+' dies de previsió'}`,manifest.legacy_snapshot||Date.now()-Date.parse(manifest.weather_timestamp)>48*3600*1000);
    if(selected) showDetail();
  } catch(error) {if(token===revision) status('Error de dades: '+error.message+'. Canvia de capa o torna-ho a intentar.',true);}
}
map.on('click', event=>{
  if(!national)return;
  const regionFeature=map.queryRenderedFeatures(event.point,{layers:['region-hit']})[0];
  if(!regionFeature)return;
  const regionId=regionFeature.properties.id;
  const cells=map.getLayer('conditions')?map.queryRenderedFeatures(event.point,{layers:['conditions']}):[];
  if(regionId!==$('region').value)loadRegion(regionId,false);
  else if(currentScores&&cells.length){selected={cell:Number(cells[0].id),lat:event.lngLat.lat,lon:event.lngLat.lng};showDetail();}
  inspectEnvironment(event.lngLat.lng,event.lngLat.lat);
});
async function inspectEnvironment(lon,lat) {
  inspectionController?.abort();
  const root=$('environment-detail');root.replaceChildren();
  const kind=$('forest').value!=='off'?'forest':$('soil').value==='on'?'soil':null;
  if(!kind){root.classList.add('hidden');return;}
  const controller=new AbortController();inspectionController=controller;
  const timeout=setTimeout(()=>controller.abort(),15000);
  root.classList.remove('hidden');text('h2',kind==='forest'?'Bosc en aquest punt':'pH en aquest punt',root);
  text('p',lat.toFixed(5)+', '+lon.toFixed(5),root);
  const result=text('p','Consultant '+(kind==='forest'?'MITECO':'SoilGrids')+'…',root);
  try{
    const value=kind==='forest'?await EL.forest(lon,lat,controller.signal):await EL.ph(lon,lat,'0-5cm','mean',controller.signal);
    if(controller!==inspectionController)return;
    result.textContent=kind==='forest'?(value?'Bosc: '+value.formation+'. Tipus: '+value.type+'. Arbres: '+(value.hosts.join(', ')||'sense dades')+'.':'MITECO: cap formació retornada; no confirma absència de bosc.'):
      (value===null?'SoilGrids: pH no disponible en aquest punt.':'pH '+value.toFixed(1)+' · '+EL.phClass(value)+' · superfície 0–5 cm · estimació a 250 m, no una mesura local.');
  }catch(error){if(controller===inspectionController)result.textContent='Servei no disponible ara. Torna a clicar per reintentar.';}
  finally{clearTimeout(timeout);}
}
function showPhoto(species){
  if(!species)return;
  const photo=photos[species.id];
  if(!photo){$('species-photo').classList.add('hidden');photoSpecies=null;return;}
  if(photoSpecies===species.id)return;photoSpecies=species.id;
  const frame=$('species-photo'),img=$('species-image'),credit=$('photo-credit');
  frame.classList.remove('hidden');img.classList.remove('hidden');img.alt=species.common_name+' · '+species.scientific_name;
  img.onerror=()=>{img.classList.add('hidden');credit.textContent='Fotografia no disponible. Torna a carregar la pàgina.';};
  img.src=photo.image;credit.replaceChildren();
  text('span',photo.author+' · ',credit);
  const license=text('a',photo.license,credit);license.href=photo.licenseUrl;license.target='_blank';license.rel='noopener';
  text('span',' · ',credit);const source=text('a','Wikimedia Commons',credit);source.href=photo.source;source.target='_blank';source.rel='noopener';
}
function showDetail() {
  if(!selected || !currentScores) return;
  const root=$('detail'), day=Number($('date').value), s=manifest.species.find(s=>s.id===$('species').value), i=selected.cell;
  root.replaceChildren();root.classList.remove('hidden');
  text('h2',s.common_name,root);text('strong',`${currentScores[i]} / 100`,root);
  text('p',`Idoneïtat meteorològica · ${manifest.dates[day]}`,root);
  text('p',`${selected.lat.toFixed(4)}, ${selected.lon.toFixed(4)}`,root);
  for(const [key,values] of Object.entries(environment.days[day])) text('p',`${modes[key][0]}: ${values[i]}${modes[key][3]}`,root);
}
$('opacity').oninput=()=>{if(currentScores)map.setPaintProperty('conditions','fill-opacity',$('layer').value==='none'?0:Number($('opacity').value)/100);};
$('landcover').onchange=()=>{if(!map.getLayer('cover'))return;const v=$('landcover').value;map.setLayoutProperty('cover','visibility',v==='off'?'none':'visible');if(v!=='off')baseTiles('cover','cobertes-sol',v);};
$('toggle').onclick=()=>{const collapsed=$('panel').classList.toggle('collapsed');$('toggle').textContent=collapsed?'+':'−';$('toggle').setAttribute('aria-expanded',String(!collapsed));};
let searchRevision=0;
$('search-form').onsubmit=async event=>{
  event.preventDefault();const token=++searchRevision,q=$('search').value.trim();$('search-message').textContent='Cercant…';
  try {
    let point,name;const match=q.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
    if(match){point=[Number(match[2]),Number(match[1])];name=q;}
    else {const data=await json(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=20&language=ca&countryCode=ES`);
      const result=(data.results||[]).find(r=>r.country_code==='ES');
      if(!result)throw new Error('No s’ha trobat cap lloc d’Espanya. Prova coordenades.');point=[result.longitude,result.latitude];name=result.name;}
    if(token!==searchRevision)return;
    if(point[0]<-18.3||point[0]>4.4||point[1]<27.5||point[1]>43.9)throw new Error('Coordenades fora de l’àrea d’Espanya.');
    map.flyTo({center:point,zoom:12});$('search-message').textContent=name;
  }catch(error){if(token===searchRevision)$('search-message').textContent=error.message;}
};
$('all-spain').onclick=()=>map.fitBounds([[-18.3,27.5],[4.4,43.9]],{padding:35});
$('canaries').onclick=()=>{if(national)loadRegion('ES70',true);};
function overlayChange(kind) {
  inspectionController?.abort();$('environment-detail').classList.add('hidden');
  const forest=$('forest').value,soil=$('soil').value;
  // The thematic maps are mutually exclusive, with their original provider legend.
  if(kind==='forest'&&forest!=='off')$('soil').value='off';
  if(kind==='soil'&&soil!=='off')$('forest').value='off';
  for(const [control,id,endpoint,layer] of [['forest','forest-map',EL.FOREST,$('forest').value],['soil','soil-map',EL.SOIL,'phh2o_0-5cm_mean']]) {
    if(!map.getLayer(id))continue;
    const visible=$(control).value!=='off';map.setLayoutProperty(id,'visibility',visible?'visible':'none');
    if(visible){if(rasterLayers.get(id)!==layer){map.getSource(id).setTiles([EL.tile(endpoint,layer)]);rasterLayers.set(id,layer);}map.moveLayer(id);}
  }
  const active=$('forest').value!=='off'?'forest':$('soil').value!=='off'?'soil':null;
  $('environment-legend').classList.toggle('hidden',!active);
  if(active){
    $('layer').value='none';render();
    const layer=active==='forest'?$('forest').value:'phh2o_0-5cm_mean';
    $('source-legend').src=EL.url(active==='forest'?EL.FOREST:EL.SOIL,{SERVICE:'WMS',VERSION:'1.1.1',REQUEST:'GetLegendGraphic',LAYER:layer,FORMAT:'image/png'});
    $('environment-caption').textContent=active==='forest'?'Llegenda MITECO · '+(EL.forestTypes.find(([id])=>id===$('forest').value)?.[1]||'Bosc'):'SoilGrids · pH estimat; els valors pH×10 es divideixen per 10. Sense color = sense dades.';
  }
  if(map.getLayer('visual-grid'))map.moveLayer('visual-grid');
}
$('forest').onchange=()=>overlayChange('forest');$('soil').onchange=()=>overlayChange('soil');
