/* Cache only successful environmental map images. Forecasts remain network-fresh. */
'use strict';
const CACHE = 'xafapins-environment-v1-' + encodeURIComponent(self.registration.scope);
const MAX_TILES = 128, MAX_AGE = 7 * 24 * 3600 * 1000;
let writes = Promise.resolve();
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
function isMap(request) {
  const u = new URL(request.url);
  return request.method === 'GET' &&
    ((u.origin === 'https://iepnb.gob.es' && u.pathname === '/geoserver/foto_fija_mfe/wms') ||
     (u.origin === 'https://maps.isric.org' && u.pathname === '/mapserv')) &&
    u.searchParams.get('REQUEST') === 'GetMap';
}
async function tile(request, event) {
  let cache;
  try {
    cache = await caches.open(CACHE);
    const hit = await cache.match(request);
    if (hit && Date.now() - Number(hit.headers.get('x-xafapins-cached')) < MAX_AGE) return hit;
  } catch (_) { /* Private browsing or storage limits must not block the map. */ }
  const response = await fetch(request);
  if (cache && response.ok && (response.headers.get('content-type') || '').startsWith('image/')) {
    const copy = response.clone();
    writes = writes.catch(() => {}).then(async () => {
      const headers = new Headers(copy.headers);
      headers.delete('content-encoding');
      headers.delete('content-length');
      headers.set('x-xafapins-cached', String(Date.now()));
      await cache.put(request, new Response(await copy.blob(), {status:200, headers}));
      const keys = await cache.keys();
      for (const key of keys.slice(0, Math.max(0, keys.length - MAX_TILES))) await cache.delete(key);
    });
    event.waitUntil(writes.catch(() => {}));
  }
  return response;
}
self.addEventListener('fetch', event => {
  if (isMap(event.request)) event.respondWith(tile(event.request, event));
});
