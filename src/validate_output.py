"""Validate deployable assets, including date and array alignment."""
import json
import argparse
import math
from pathlib import Path
from download_meteo import ROOT


def validate(folder=ROOT/'web/data'):
    def read(name):
        return json.loads((Path(folder)/name).read_text(encoding='utf-8'))
    manifest, grid, env = read('manifest.json'), read('grid.geojson'), read('environment.json')
    count = manifest['cell_count']
    assert count > 0 and len(grid['features']) == count
    assert [f['id'] for f in grid['features']] == list(range(count))
    assert env['dates'] == manifest['dates'] and len(env['days']) == len(env['dates'])
    for day in env['days']:
        for values in day.values():
            assert len(values) == count and all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)
    for species in manifest['species']:
        data = read(species['id']+'.json')
        assert data['dates'] == manifest['dates'] and len(data['scores']) == len(data['dates'])
        assert all(len(scores) == count and all(0 <= s <= 100 for s in scores) for scores in data['scores'])
    print(f'Validated {count} cells, {len(manifest["species"])} species and {len(manifest["dates"])} dates')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--all-spain',action='store_true')
    args=parser.parse_args()
    if args.all_spain:
        catalog=json.loads((ROOT/'web/data/spain.json').read_text(encoding='utf-8'))
        from regions import regions
        assert {r['id'] for r in catalog['regions']} == {f['properties']['id'] for f in regions()}
        dates=None
        for region in catalog['regions']:
            folder=ROOT/'web'/region['path']
            validate(folder)
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            assert manifest['region_id']==region['id']
            assert manifest['cell_count']==region['cell_count']
            assert dates is None or dates==manifest['dates']
            dates=manifest['dates']
            assert region['dates']==dates
            assert set(region['overview'])=={s['id'] for s in manifest['species']}
            assert all(len(values)==len(dates) and all(0<=v<=100 for v in values) for values in region['overview'].values())
        print('Validated all 19 Spanish regions')
    else:
        validate()
