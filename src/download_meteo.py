"""Fetch dated weather; incomplete downloads never replace the last good file."""
import argparse
import json
import math
import os
import time
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape, Point
from regions import region_geometry, weather_points

ROOT = Path(__file__).resolve().parents[1]
VARIABLES = ['precipitation_sum', 'temperature_2m_min', 'temperature_2m_max',
             'relative_humidity_2m_mean', 'wind_speed_10m_max', 'et0_fao_evapotranspiration']


def boundary(region_id=None):
    return region_geometry(region_id)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    os.replace(tmp, path)


def validate_daily(item, expected_dates=None):
    daily = item.get('daily', {})
    dates = daily.get('time', [])
    if not dates or len(dates) != len(set(dates)) or dates != sorted(dates):
        raise ValueError('Missing, duplicated or unordered weather dates')
    start = date.fromisoformat(dates[0])
    if dates != [(start+timedelta(days=i)).isoformat() for i in range(len(dates))]:
        raise ValueError('Weather dates must be consecutive calendar days')
    if expected_dates is not None and dates != expected_dates:
        raise ValueError('Weather date coverage differs between locations')
    for key in VARIABLES:
        values = daily.get(key, [])
        if len(values) != len(dates) or any(v is None or not math.isfinite(v) for v in values):
            raise ValueError(f'Incomplete weather variable: {key}')
    if not isinstance(item.get('elevation'), (int, float)) or not math.isfinite(item['elevation']):
        raise ValueError('Missing model elevation')
    return dates


def fetch_grid_weather(step=0.16, history_days=28, forecast_days=7, output=None, region_id=None):
    if not 0.04 <= step <= 0.5:
        raise ValueError('Weather grid step must be between 0.04 and 0.5 degrees')
    points = weather_points(step, boundary(region_id))
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=Retry(total=4, backoff_factor=2,
                  status_forcelist=[429, 500, 502, 503, 504])))
    results, dates = [], None
    for start in range(0, len(points), 25):
        chunk = points[start:start+25]
        response = session.get('https://api.open-meteo.com/v1/forecast', params={
            'latitude': ','.join(str(p[0]) for p in chunk),
            'longitude': ','.join(str(p[1]) for p in chunk), 'daily': ','.join(VARIABLES),
            'past_days': history_days, 'forecast_days': forecast_days,
            # One calendar reference across Spain, explicitly disclosed for Canarias.
            'timezone': 'Europe/Madrid', 'wind_speed_unit': 'kmh',
        }, timeout=(15, 90))
        response.raise_for_status()
        items = response.json()
        items = items if isinstance(items, list) else [items]
        if len(items) != len(chunk):
            raise ValueError('Incomplete weather batch')
        for (lat, lon), item in zip(chunk, items):
            dates = validate_daily(item, dates)
            if len(dates) != history_days+forecast_days:
                raise ValueError('Unexpected number of weather days')
            results.append({'lat': lat, 'lon': lon, 'model_lat': item['latitude'],
                            'model_lon': item['longitude'], 'elevation': item['elevation'],
                            'daily': item['daily']})
        print(f'Weather: {len(results)}/{len(points)} locations', flush=True)
        time.sleep(0.35)
    payload = {'schema_version': 2, 'timestamp': datetime.now(timezone.utc).isoformat(),
               'source': 'Open-Meteo best_match; archived forecasts + forecast',
               'sampling_step_degrees': step, 'history_days': history_days,
               'region_id': region_id or 'ES', 'timezone': 'Europe/Madrid',
               'forecast_dates': dates[history_days:], 'data': results}
    atomic_json(output or ROOT/'data/meteo_spain_latest.json', payload)
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grid-step', type=float, default=0.16)
    parser.add_argument('--region', default=None)
    parser.add_argument('--forecast-days', type=int, choices=range(1, 17), default=7)
    args = parser.parse_args()
    fetch_grid_weather(step=args.grid_step, forecast_days=args.forecast_days, region_id=args.region)
