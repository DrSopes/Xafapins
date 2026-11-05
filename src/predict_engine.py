"""Build shared clipped cells and compact, dated species suitability arrays."""
import argparse
import json
import math
from datetime import datetime, timezone, date
from pathlib import Path
import numpy as np
import yaml
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import box, mapping
from download_meteo import ROOT, atomic_json, boundary, validate_daily
from regions import regions


def load_rules():
    return yaml.safe_load((ROOT/'config/species_rules.yaml').read_text(encoding='utf-8'))


def score_weather(rain, temperature, frost, elevation, rule, month):
    """Uncalibrated weather/season index. Habitat is deliberately not invented."""
    trigger = rule['meteo_triggers']
    wet = np.clip(rain/trigger['rain_optimal_mm'], 0, 1)
    low, optimum, high = (trigger[k] for k in
        ['temp_min_celsius', 'temp_optimal_celsius', 'temp_max_celsius'])
    thermal = np.clip(np.minimum((temperature-low)/(optimum-low),
                                 (high-temperature)/(high-optimum)), 0, 1)
    freeze = np.clip(1-frost/max(trigger['frost_penalty_days'], 1)*0.15, 0, 1)
    altitude = np.clip(np.minimum((elevation-rule['altitude_min']+300)/300,
                                  (rule['altitude_max']+300-elevation)/300), 0, 1)
    season = 1 if month in rule['months'] else 0.15
    return np.rint(100*wet*thermal*freeze*altitude*season).astype(int)


def build(step_km=1.0, weather_path=None, output=None, allow_legacy=False, region_id=None):
    if not 0.5 <= step_km <= 5:
        raise ValueError('Cell size must be between 0.5 and 5 km')
    output = Path(output or ROOT/'web/data')
    weather = json.loads(Path(weather_path or ROOT/'data/meteo_spain_latest.json').read_text(encoding='utf-8'))
    rows = weather['data']
    if not rows:
        raise ValueError('No weather locations; refusing to publish')
    legacy = weather.get('schema_version') != 2
    if legacy and not allow_legacy:
        raise ValueError('Legacy snapshot: refresh weather or explicitly use --allow-legacy for a historical preview')
    if not legacy:
        dates = validate_daily(rows[0])
        for row in rows[1:]:
            validate_daily(row, dates)
        forecast_dates = weather['forecast_dates']
        if not forecast_dates or forecast_dates != dates[28:]:
            raise ValueError('Forecast dates must follow the complete 28-day history')
        stamp = datetime.fromisoformat(weather['timestamp'])
        if (datetime.now(timezone.utc)-stamp).total_seconds() > 48*3600:
            raise ValueError('Weather is older than 48 hours; refresh before publishing')
    else:
        forecast_dates = [weather['timestamp'][:10]]
    if region_id and weather.get('region_id', 'ES') not in ['ES', region_id]:
        raise ValueError('Weather coverage does not match the requested region')
    region = boundary(region_id) if region_id else boundary()
    shapely.prepare(region)
    west, south, east, north = region.bounds
    latitude = region.centroid.y
    dx, dy = step_km/(111.32*math.cos(math.radians(latitude))), step_km/111.32
    features, centers = [], []
    for y in np.arange(south, north, dy):
        for x in np.arange(west, east, dx):
            cell = box(x, y, x+dx, y+dy)
            if not region.intersects(cell):
                continue
            clipped = cell if region.covers(cell) else region.intersection(cell)
            if clipped.area < 1e-12:
                continue
            center = clipped.representative_point()
            centers.append([center.x, center.y])
            features.append({'type': 'Feature', 'id': len(features),
                             'properties': {'cell': len(features)}, 'geometry': mapping(clipped)})
    xy = np.array([[r['lon'], r['lat']] for r in rows])
    scale = [math.cos(math.radians(latitude)), 1]
    distances, indices = cKDTree(xy*scale).query(np.array(centers)*scale, k=min(4, len(rows)))
    if len(rows) == 1:
        distances, indices = distances[:, None], indices[:, None]
    if np.max(distances[:, 0])*111.32 > 60:
        raise ValueError('Weather coverage has a gap exceeding 60 km; refusing extrapolation')
    weights = 1/np.maximum(distances, 1e-9)**2
    weights /= weights.sum(axis=1)[:, None]

    def interpolate(values):
        return np.sum(np.array(values)[indices]*weights, axis=1)

    rules = load_rules()
    products = {key: [] for key in rules}
    environment = []
    elevation = interpolate([r.get('elevation', 0) for r in rows])
    for target in forecast_dates:
        if legacy:
            rain = interpolate([r['rain_past_21d'] for r in rows])
            temp = interpolate([(r['t_min_avg']+r['t_max_avg'])/2 for r in rows])
            frost = interpolate([r['frost_days'] for r in rows])
            env = {'rain_21d': rain.round(1).tolist(), 'temperature': temp.round(1).tolist()}
        else:
            index = dates.index(target)
            if index < 28:
                raise ValueError('28 days of antecedent weather are required')

            def aggregate(key, window, mode='mean', include_today=False):
                end = index+1 if include_today else index
                values = np.array([r['daily'][key][end-window:end] for r in rows])
                result = values.sum(axis=1) if mode == 'sum' else values.mean(axis=1)
                if mode == 'frost':
                    result = (values <= 0).sum(axis=1)
                return interpolate(result)

            rain = aggregate('precipitation_sum', 21, 'sum')
            temp = (aggregate('temperature_2m_min', 7)+aggregate('temperature_2m_max', 7))/2
            frost = aggregate('temperature_2m_min', 7, 'frost')
            env = {'rain_21d': rain.round(1).tolist(),
                   'rain_day': aggregate('precipitation_sum', 1, 'sum', True).round(1).tolist(),
                   'temperature': temp.round(1).tolist(),
                   'humidity': aggregate('relative_humidity_2m_mean', 1, include_today=True).round(1).tolist(),
                   'wind': aggregate('wind_speed_10m_max', 1, include_today=True).round(1).tolist(),
                   'water_balance': (rain-aggregate('et0_fao_evapotranspiration', 21, 'sum')).round(1).tolist(),
                   'frost': frost.round(1).tolist(), 'elevation': elevation.round().tolist()}
        environment.append(env)
        for key, rule in rules.items():
            species_rain = rain if legacy else aggregate('precipitation_sum', rule['meteo_triggers']['rain_window_days'], 'sum')
            z = np.full(len(features), (rule['altitude_min']+rule['altitude_max'])/2) if legacy else elevation
            products[key].append(score_weather(species_rain, temp, frost, z, rule, date.fromisoformat(target).month).tolist())
    atomic_json(output/'grid.geojson', {'type': 'FeatureCollection', 'features': features})
    atomic_json(output/'environment.json', {'dates': forecast_dates, 'days': environment})
    for key, scores in products.items():
        atomic_json(output/f'{key}.json', {'dates': forecast_dates, 'scores': scores})
    atomic_json(output/'manifest.json', {
        'schema_version': 2, 'generated_at': datetime.now(timezone.utc).isoformat(),
        'region_id': region_id, 'bounds': list(region.bounds),
        'weather_timestamp': weather['timestamp'], 'legacy_snapshot': legacy,
        'dates': forecast_dates, 'cell_count': len(features), 'cell_size_km': step_km,
        'weather_sampling_degrees': weather.get('sampling_step_degrees', 0.08),
        'weather_source': weather.get('source', 'Original snapshot; daily series unavailable'),
        'model': 'Uncalibrated weather and season suitability; not probability of occurrence',
        'missing_predictors': ['measured soil pH', 'host-tree species', 'local terrain DEM'],
        'species': [{'id': key, **rule} for key, rule in rules.items()],
        'layers': list(environment[0])})
    print(f'Built {region_id or "test"}: {len(features)} cells, {len(rules)} species, {len(forecast_dates)} dates', flush=True)


def build_spain(step_km=1):
    catalog = []
    for feature in regions():
        region_id = feature['properties']['id']
        output = ROOT/'web/data/regions'/region_id
        build(step_km=step_km, output=output, region_id=region_id)
        manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        overview={}
        for species in manifest['species']:
            scores=json.loads((output/(species['id']+'.json')).read_text(encoding='utf-8'))['scores']
            overview[species['id']]=[round(sum(day)/len(day),1) for day in scores]
        catalog.append({**feature['properties'], 'bounds': manifest['bounds'],
                        'cell_count': manifest['cell_count'], 'path': f'data/regions/{region_id}',
                        'overview':overview, 'dates':manifest['dates']})
    atomic_json(ROOT/'web/data/spain.json', {'regions': catalog,
        'boundary_source': 'Eurostat GISCO NUTS 2024 1:1M',
        'timezone': 'Europe/Madrid'})
    atomic_json(ROOT/'web/data/spain-regions.geojson', {'type':'FeatureCollection', 'features':regions()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cell-km', type=float, default=1)
    parser.add_argument('--allow-legacy', action='store_true')
    parser.add_argument('--all-spain', action='store_true')
    parser.add_argument('--region')
    args = parser.parse_args()
    if args.all_spain:
        build_spain(args.cell_km)
    else:
        build(step_km=args.cell_km, allow_legacy=args.allow_legacy, region_id=args.region)
