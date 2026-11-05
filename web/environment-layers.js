/* Official sources; WMS display and point inspection are independent of forecast cells. */
(function(root) {
  'use strict';
  const FOREST='https://iepnb.gob.es/geoserver/foto_fija_mfe/wms';
  const SOIL='https://maps.isric.org/mapserv?map=/map/phh2o.map';
  function url(endpoint,params) {
    return endpoint+(endpoint.includes('?')?'&':'?')+new URLSearchParams(params).toString();
  }
  function tile(endpoint,layer) {
    return url(endpoint,{SERVICE:'WMS',VERSION:'1.1.1',REQUEST:'GetMap',LAYERS:layer,
      STYLES:'',FORMAT:'image/png',TRANSPARENT:'true',SRS:'EPSG:3857',
      BBOX:'{bbox-epsg-3857}',WIDTH:256,HEIGHT:256}).replace('%7Bbbox-epsg-3857%7D','{bbox-epsg-3857}');
  }
  function featureUrl(endpoint,layer,lon,lat,format) {
    // Small fixed footprint avoids zoom-dependent picking of neighbouring forests.
    const delta=0.0001;
    return url(endpoint,{SERVICE:'WMS',VERSION:'1.1.1',REQUEST:'GetFeatureInfo',LAYERS:layer,
      QUERY_LAYERS:layer,STYLES:'',FORMAT:'image/png',SRS:'EPSG:4326',
      BBOX:[lon-delta,lat-delta,lon+delta,lat+delta].join(','),WIDTH:101,HEIGHT:101,
      X:50,Y:50,INFO_FORMAT:format,FEATURE_COUNT:1,BUFFER:0});
  }
  function phValue(doc) {
    const value=doc?.features?.[0]?.properties?.pixel_value;
    if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>140) return null;
    return value/10;
  }
  function phClass(value) {
    if(value===null||!Number.isFinite(value))return 'Sense dades';
    return value<5.5?'Àcid':value<6.5?'Lleugerament àcid':value<=7.5?'Proper a neutre':'Alcalí';
  }
  function forestValue(doc) {
    const p=doc?.features?.[0]?.properties;
    if(!p)return null;
    return {formation:p.descr_forarb||p.descr_tipobosque||'Formació no especificada',
      type:p.descr_tipobosque||'Sense classificació',
      hosts:[p.nom_sp1,p.nom_sp2,p.nom_sp3].filter(v=>v&&v!=='Sin especie arbórea'),
      canopy:typeof p.nm_fccarb==='number'?p.nm_fccarb:null};
  }
  async function request(endpoint,layer,lon,lat,format,signal) {
    const response=await fetch(featureUrl(endpoint,layer,lon,lat,format),{signal});
    if(!response.ok)throw new Error('HTTP '+response.status);
    return response.json();
  }
  const forestTypes=[
    ['ff_form_arbolada','Totes les formacions'],['ff_tipo_bosque','Coníferes / frondoses / mixt'],
    ['pinar_pino_albar','Pi roig · Pinus sylvestris'],['pinar_pino_negro','Pi negre · P. uncinata'],
    ['pinar_pino_carrasco','Pi blanc · P. halepensis'],['pinar_pino_salgareno','Pinassa · P. nigra'],
    ['pinar_pino_pinonero','Pi pinyer · P. pinea'],['pinar_pino_canario','Pi canari'],
    ['pinar_pino_pinaster_reg_atlantica','Pinastre atlàntic'],['pinar_pino_pinaster_reg_mediterranea','Pinastre mediterrani'],
    ['encinares','Alzinars'],['alcornocales','Suredes'],['hayedos','Fagedes'],['abetales','Avetoses'],
    ['castanares','Castanyedes'],['robledales_qrobur_qpetraea','Rouredes de roure pènol / fulla gran'],
    ['robledales_roble_pubescente','Rouredes de roure martinenc'],['melojares','Rouredes de reboll'],
    ['quejigares','Rouredes de roure de fulla petita'],['abedulares','Bedollars'],
    ['bosque_ribereno','Bosc de ribera'],['dehesas','Deveses'],['eucaliptales','Eucaliptus'],
    ['pinsapares','Pinsapars'],['laurisilvas_macaronesicas','Laurisilva'],['fayal_brezal','Fayal-brezal']];
  root.EnvironmentLayers={FOREST,SOIL,tile,url,featureUrl,phValue,phClass,forestValue,forestTypes,
    forest:(lon,lat,signal)=>request(FOREST,'ff_form_arbolada',lon,lat,'application/json',signal).then(forestValue),
    ph:(lon,lat,depth,stat,signal)=>request(SOIL,`phh2o_${depth}_${stat}`,lon,lat,'application/geo+json',signal).then(phValue)};
  if(typeof module!=='undefined')module.exports=root.EnvironmentLayers;
})(typeof globalThis!=='undefined'?globalThis:this);
