"""Stage only the current application and validated Spain data for GitHub Pages."""
import json
import gzip
import shutil
from pathlib import Path
from download_meteo import ROOT
from regions import regions

def package():
    web=ROOT/'web'
    catalog=json.loads((web/'data/spain.json').read_text(encoding='utf-8'))
    expected={f['properties']['id'] for f in regions()}
    if {r['id'] for r in catalog['regions']} != expected:
        raise ValueError('Incomplete Spain catalogue')
    output=ROOT/'dist'
    if output.is_symlink() or output.resolve().parent!=ROOT.resolve():
        raise ValueError('Build directory must be the real project-local dist folder')
    # Fixed project-local output; never copy old prediction_*.geojson or source files.
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for name in ['index.html','app.js','app.css','environment-layers.js','visual-grid.js','tile-cache-sw.js','species-photos.json']:
        shutil.copy2(web/name,output/name)
    shutil.copytree(web/'images', output/'images')
    (output/'data/regions').mkdir(parents=True)
    for name in ['spain.json','spain-regions.geojson']:
        shutil.copy2(web/'data'/name,output/'data'/name)
    for region in catalog['regions']:
        region_id=region['id']
        if region_id not in expected or region['path']!=f'data/regions/{region_id}':
            raise ValueError('Invalid region output path')
        source=web/'data/regions'/region_id
        manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
        destination=output/'data/regions'/region_id
        destination.mkdir()
        names=['manifest.json','environment.json','grid.geojson']+[s['id']+'.json' for s in manifest['species']]
        for name in names:
            if Path(name).name!=name:
                raise ValueError('Invalid species filename')
            # Explicit gzip files keep the 22-day national artifact small on Pages.
            # The browser decompresses these; no custom HTTP headers are needed.
            if name == 'manifest.json':
                shutil.copy2(source/name,destination/name)
            else:
                with open(source/name, 'rb') as original, gzip.open(destination/(name+'.gz'), 'wb', compresslevel=6) as compressed:
                    shutil.copyfileobj(original, compressed)
    (output/'.nojekyll').touch()
    total=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if total>=1_000_000_000:
        raise ValueError('Pages output exceeds 1 GB; reduce grid density')
    print(f'Pages artifact ready: {len(expected)} regions, {total/1e6:.1f} MB',flush=True)

if __name__=='__main__':package()
