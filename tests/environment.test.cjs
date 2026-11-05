const {test}=require('node:test');
const assert=require('node:assert/strict');
const E=require('../web/environment-layers.js');
test('pH scaling and nodata are explicit',()=>{
  const data=v=>({features:[{properties:{pixel_value:v}}]});
  assert.equal(E.phValue(data(62)),6.2);
  for(const v of [null,undefined,-32768,255,'62',NaN])assert.equal(E.phValue(data(v)),null);
  assert.equal(E.phValue({features:[]}),null);
});
test('pH classes distinguish acidic, neutral and alkaline soil',()=>{
  assert.equal(E.phClass(4.5),'Àcid');assert.equal(E.phClass(6.2),'Lleugerament àcid');
  assert.equal(E.phClass(7),'Proper a neutre');assert.equal(E.phClass(8),'Alcalí');
  assert.equal(E.phClass(null),'Sense dades');
});
test('forest query keeps real formation and dominant species',()=>{
  assert.deepEqual(E.forestValue({features:[{properties:{descr_forarb:'Hayedos',descr_tipobosque:'Frondosas',nom_sp1:'Fagus sylvatica',nom_sp2:'Sin especie arbórea',nm_fccarb:90}}]}),
    {formation:'Hayedos',type:'Frondosas',hosts:['Fagus sylvatica'],canopy:90});
  assert.equal(E.forestValue({features:[]}),null);
});
test('WMS URLs preserve map parameter, tile token and longitude-latitude axis order',()=>{
  const tile=E.tile(E.SOIL,'phh2o_0-5cm_mean');
  assert.ok(tile.includes('map=/map/phh2o.map'));assert.ok(tile.includes('{bbox-epsg-3857}'));
  const query=new URL(E.featureUrl(E.FOREST,'ff_form_arbolada',2.4,41.8,'application/json'));
  assert.equal(query.searchParams.get('STYLES'),'');assert.equal(query.searchParams.get('SRS'),'EPSG:4326');
  const bbox=query.searchParams.get('BBOX').split(',').map(Number);
  assert.ok(bbox[0]<2.4&&bbox[2]>2.4&&bbox[1]<41.8&&bbox[3]>41.8);
});
