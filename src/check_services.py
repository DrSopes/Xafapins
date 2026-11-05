"""Explicit network smoke test for the public environmental services (not run in CI)."""
import json
from datetime import datetime, timezone
import requests
from download_meteo import ROOT, atomic_json

FOREST='https://iepnb.gob.es/geoserver/foto_fija_mfe/wms'
SOIL='https://maps.isric.org/mapserv?map=/map/phh2o.map'

def check():
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'checks':[]}
    common={'SERVICE':'WMS','VERSION':'1.1.1','STYLES':'','FORMAT':'image/png',
            'SRS':'EPSG:4326','BBOX':'2.39,41.79,2.41,41.81','WIDTH':101,'HEIGHT':101}
    for endpoint,layer in [(FOREST,'ff_tipo_bosque'),(SOIL,'phh2o_0-5cm_mean')]:
        response=requests.get(endpoint,params={**common,'REQUEST':'GetMap','LAYERS':layer},timeout=45)
        response.raise_for_status()
        assert response.content.startswith(b'\x89PNG\r\n\x1a\n'),f'{layer}: expected PNG, got {response.text[:100]}'
        report['checks'].append({'layer':layer,'png':True,'cors':response.headers.get('Access-Control-Allow-Origin')})
        print(f'PNG tile OK: {layer}',flush=True)
    for endpoint,layer,format in [(FOREST,'ff_form_arbolada','application/json')]+[
            (SOIL,'phh2o_0-5cm_'+stat,'application/geo+json') for stat in ['mean','Q0.05','Q0.95']]:
        response=requests.get(endpoint,params={**common,'REQUEST':'GetFeatureInfo','LAYERS':layer,
            'QUERY_LAYERS':layer,'X':50,'Y':50,'INFO_FORMAT':format,'FEATURE_COUNT':1},timeout=45)
        response.raise_for_status(); data=response.json()
        assert response.headers.get('Access-Control-Allow-Origin')=='*','Browser CORS not enabled'
        properties=data['features'][0]['properties']
        value=properties.get('descr_forarb') if endpoint==FOREST else properties['pixel_value']/10
        report['checks'].append({'layer':layer,'point_value':value,'cors':'*'})
        print(f'Point query OK: {layer} = {value}',flush=True)
    atomic_json(ROOT/'data/service-check.json',report)

if __name__=='__main__':check()
