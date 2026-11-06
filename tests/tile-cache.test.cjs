const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function setup() {
  const events={}, entries=new Map();let calls=0,now=1000000,fail=false,xml=false;
  const cache={match:async r=>entries.get(r.url)?.clone(),
    put:async(r,v)=>entries.set(r.url,v),keys:async()=>[...entries.keys()].map(url=>({url})),
    delete:async r=>entries.delete(r.url)};
  const context={self:{registration:{scope:'https://example.com/Xafapins/'},
    addEventListener:(name,fn)=>events[name]=fn},URL,Headers,Response,Promise,
    Date:{now:()=>now},caches:{open:async()=>cache},fetch:async()=>{
      calls++;return new Response(fail?'error':xml?'<ServiceException/>':'image',
        {status:fail?503:200,headers:{'content-type':xml?'text/xml':'image/png'}});
    }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/tile-cache-sw.js'),'utf8'),context);
  async function request(url='https://maps.isric.org/mapserv?REQUEST=GetMap') {
    const waits=[];let result;
    events.fetch({request:{url,method:'GET'},respondWith:p=>result=p,waitUntil:p=>waits.push(p)});
    const response=await result;await Promise.all(waits);return response;
  }
  return {request,entries,get calls(){return calls;},expire(){now+=8*86400000;},fail(){fail=true;},xml(){xml=true;}};
}
test('tiles reuse successful images, then refresh after seven days',async()=>{
  const s=setup();await s.request();await s.request();assert.equal(s.calls,1);
  s.expire();await s.request();assert.equal(s.calls,2);
});
test('errors and WMS exception documents are not cached',async()=>{
  for(const kind of ['fail','xml']){const s=setup();s[kind]();await s.request();await s.request();assert.equal(s.calls,2);assert.equal(s.entries.size,0);}
});
test('forecast requests and other map providers are not intercepted',async()=>{
  const s=setup();
  for(const url of ['https://example.com/data/spain.json','https://tile.openstreetmap.org/1/1/1.png','https://maps.isric.org/mapserv?REQUEST=GetFeatureInfo'])assert.equal(await s.request(url),undefined);
  assert.equal(s.calls,0);
});
test('tile storage stays bounded',async()=>{
  const s=setup();for(let i=0;i<135;i++)await s.request('https://maps.isric.org/mapserv?REQUEST=GetMap&BBOX='+i);
  assert.equal(s.entries.size,128);
});
