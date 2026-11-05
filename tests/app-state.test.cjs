// Offline controller tests with stubbed map/DOM adapters. No browser or network.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const E=require('../web/environment-layers.js');

async function setup() {
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
  const nodes={};
  function element(tag='div') {
    return {tag,value:'',textContent:'',children:[],disabled:false,style:{},events:{},
      classList:{toggle(){},add(){},remove(){}},
      append(child){this.children.push(child);if(this.tag==='select'&&!this.value)this.value=child.value;},
      replaceChildren(){this.children=[];if(this.tag==='select')this.value='';},
      addEventListener(name,fn){this.events[name]=fn;},setAttribute(){},click(){}};
  }
  for(const match of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"/g))nodes[match[2]]=element(match[1]);
  Object.assign(nodes.opacity,{value:'65'});
  for(const id of ['forest','soil','landcover'])nodes[id].value='off';
  let map;
  class MapStub {
    constructor(options){map=this;this.events={};this.sources={};this.layers={};this.states={};
      for(const [id,data] of Object.entries(options.style.sources))this.addSource(id,data);
      for(const layer of options.style.layers)this.addLayer(layer);}
    on(event,fn){this.events[event]=fn;}addControl(){}fitBounds(){}flyTo(){}
    addSource(id,data){this.sources[id]={...data,setTiles(tiles){this.tiles=tiles;},setData(value){this.data=value;}};}
    getSource(id){return this.sources[id];}addLayer(layer){this.layers[layer.id]=layer;}
    getLayer(id){return this.layers[id];}moveLayer(){}removeFeatureState(){}
    setPaintProperty(id,key,value){assert.ok(this.layers[id],id);(this.layers[id].paint??={})[key]=value;}
    setLayoutProperty(id,key,value){assert.ok(this.layers[id],id);(this.layers[id].layout??={})[key]=value;}
    setFeatureState(key,value){this.states[key.source+':'+key.id]=value;}
  }
  const species={id:'test_species',common_name:'Test',scientific_name:'Test species',habitat:'Pinedes',months:[11],altitude_min:0,altitude_max:1000};
  const dates=['2026-11-05'];
  const regions=['ES51','ES70'].map(id=>({id,name:id,bounds:[0,40,1,41],path:'data/regions/'+id,overview:{test_species:[50]},dates}));
  const assets={
    'data/spain.json':{regions},'data/spain-regions.geojson':{type:'FeatureCollection',features:[]}
  };
  for(const r of regions){
    assets[r.path+'/manifest.json']={region_id:r.id,species:[species],dates,cell_count:1,cell_size_km:1,layers:['rain_21d'],weather_timestamp:'2026-11-05T12:00:00Z',weather_sampling_degrees:0.16};
    assets[r.path+'/environment.json']={dates,days:[{rain_21d:[50]}]};
    assets[r.path+'/grid.geojson']={type:'FeatureCollection',features:[{id:0,properties:{cell:0},geometry:{type:'Polygon',coordinates:[]}}]};
    assets[r.path+'/test_species.json']={dates,scores:[[r.id==='ES51'?30:70]]};
  }
  const context=vm.createContext({EnvironmentLayers:E,document:{getElementById:id=>nodes[id],createElement:element},
    maplibregl:{Map:MapStub,NavigationControl:class{},GeolocateControl:class{}},
    localStorage:{getItem(){return null;},setItem(){}},
    fetch:async url=>({ok:!!assets[url],status:assets[url]?200:404,json:async()=>structuredClone(assets[url])}),
    requestAnimationFrame:fn=>fn(),setTimeout,clearTimeout,AbortController,URL,Blob,console});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),context);
  await map.events.load();
  return {context,map,nodes,assets};
}
test('controller loads national catalogue and detailed region data',async()=>{
  const {map,nodes}=await setup();
  assert.equal(nodes.region.value,'ES51');assert.equal(nodes.species.disabled,false);
  assert.equal(map.states['cells:0'].value,30);assert.equal(map.states['regions:ES70'].value,50);
});
test('region change replaces score arrays and rejects delayed previous responses',async()=>{
  const {context,map,nodes}=await setup();
  const originalFetch=context.fetch,pending=[];
  context.fetch=url=>url.startsWith('data/regions/ES51/')?new Promise(resolve=>pending.push(()=>originalFetch(url).then(resolve))):originalFetch(url);
  const old=context.loadRegion('ES51',false);
  await context.loadRegion('ES70',false);
  pending.forEach(resolve=>resolve());await old;
  assert.equal(nodes.region.value,'ES70');assert.equal(map.states['cells:0'].value,70);
});
test('forest and soil overlays are exclusive and weather selection clears them',async()=>{
  const {context,map,nodes}=await setup();
  nodes.forest.value='hayedos';context.overlayChange('forest');
  assert.equal(nodes.layer.value,'none');assert.equal(map.layers['forest-map'].layout.visibility,'visible');
  nodes.soil.value='0-5cm';context.overlayChange('soil');
  assert.equal(nodes.forest.value,'off');assert.equal(map.layers['forest-map'].layout.visibility,'none');
  assert.equal(map.layers['soil-map'].layout.visibility,'visible');
  nodes.layer.value='score';await context.render();
  assert.equal(nodes.soil.value,'off');assert.equal(map.layers['soil-map'].layout.visibility,'none');
  assert.equal(map.states['cells:0'].value,30);
});
