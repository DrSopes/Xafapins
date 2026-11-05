import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from unittest.mock import patch
import numpy as np
from shapely.geometry import box, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from download_meteo import VARIABLES, validate_daily, atomic_json
from predict_engine import build, load_rules, score_weather
from validate_output import validate
from regions import regions, region_geometry, weather_points
from shapely.geometry import Point


def fixture():
    start = date(2026, 10, 8)
    dates = [(start+timedelta(days=i)).isoformat() for i in range(35)]
    daily = {'time': dates}
    for key, value in zip(VARIABLES, [3, 8, 18, 80, 15, 2]):
        daily[key] = [value]*35
    return {'schema_version':2, 'timestamp':datetime.now(timezone.utc).isoformat(),
            'forecast_dates':dates[28:], 'sampling_step_degrees':0.08,
            'data':[{'lon':2,'lat':42,'elevation':900,'daily':daily}]}


class PipelineTests(unittest.TestCase):
    def test_spain_has_19_regions_and_islands_and_cities(self):
        self.assertEqual(len(regions()),19)
        for code,lon,lat in [('ES51',2.17,41.39),('ES53',2.65,39.57),('ES70',-16.25,28.46),('ES63',-5.32,35.89),('ES64',-2.95,35.29)]:
            self.assertTrue(region_geometry(code).buffer(0.02).covers(Point(lon,lat)))

    def test_tiny_regions_keep_weather_samples(self):
        for code in ['ES63','ES64','ES53','ES70']:
            self.assertGreater(len(weather_points(.16,region_geometry(code))),0)

    def test_weather_gap_refuses_distant_extrapolation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'weather.json';atomic_json(path,fixture())
            with patch('predict_engine.boundary',return_value=box(-16,28,-15.99,28.01)):
                with self.assertRaisesRegex(ValueError,'60 km'):build(weather_path=path)

    def test_null_weather_is_rejected(self):
        item=fixture()['data'][0]
        item['daily']['precipitation_sum'][2]=None
        with self.assertRaises(ValueError): validate_daily(item)

    def test_misaligned_dates_rejected(self):
        with self.assertRaises(ValueError): validate_daily(fixture()['data'][0], ['2026-01-01'])

    def test_missing_calendar_day_rejected(self):
        item=fixture()['data'][0]
        item['daily']['time'][-1]='2026-11-13'
        with self.assertRaises(ValueError): validate_daily(item)

    def test_atomic_write_keeps_previous_data_on_serialization_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'weather.json'
            atomic_json(path,{'valid':True})
            with self.assertRaises(ValueError): atomic_json(path,{'invalid':float('nan')})
            self.assertEqual(json.loads(path.read_text()),{'valid':True})

    def test_species_are_distinct_and_valid(self):
        rules=load_rules()
        self.assertEqual(len(rules),24)
        self.assertNotEqual(rules['lactarius_deliciosus'],rules['lactarius_sanguifluus'])
        for rule in rules.values():
            self.assertTrue(all(1<=m<=12 for m in rule['months']))
            self.assertLessEqual(rule['meteo_triggers']['rain_window_days'],28)
            self.assertLess(rule['altitude_min'],rule['altitude_max'])

    def test_drought_frost_season_and_altitude_reduce_score(self):
        rule=load_rules()['lactarius_deliciosus']
        def score(rain=75,temp=13,frost=0,z=800,month=10):
            return score_weather(np.array([rain]),np.array([temp]),np.array([frost]),np.array([z]),rule,month)[0]
        self.assertEqual(score(),100)
        self.assertEqual(score(rain=0),0)
        self.assertEqual(score(temp=40),0)
        self.assertLess(score(frost=5),score())
        self.assertLess(score(month=3),score())
        self.assertEqual(score(z=3000),0)

    def test_end_to_end_dates_clipping_and_antecedent_rain(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); weather=fixture()
            # A storm on the first forecast day must not enter that day's antecedent window.
            weather['data'][0]['daily']['precipitation_sum'][28]=100
            atomic_json(folder/'weather.json',weather)
            region=box(1.99,41.99,2.02,42.02)
            with patch('predict_engine.boundary',return_value=region):
                build(weather_path=folder/'weather.json',output=folder/'out')
            validate(folder/'out')
            grid=json.loads((folder/'out/grid.geojson').read_text())
            self.assertTrue(all(region.covers(shape(f['geometry'])) for f in grid['features']))
            env=json.loads((folder/'out/environment.json').read_text())
            self.assertEqual(env['days'][0]['rain_21d'][0],63)
            self.assertEqual(env['days'][1]['rain_21d'][0],160)
            self.assertEqual(env['days'][0]['rain_day'][0],100)
            self.assertEqual(len(env['days']),7)

    def test_empty_and_legacy_weather_fail_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'weather.json'
            for payload in [{'data':[]},{'data':[{'lat':42,'lon':2}]}]:
                atomic_json(path,payload)
                with self.assertRaises(ValueError): build(weather_path=path)

    def test_stale_weather_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'weather.json';weather=fixture();weather['timestamp']='2000-01-01T00:00:00+00:00'
            atomic_json(path,weather)
            with self.assertRaises(ValueError): build(weather_path=path)


if __name__ == '__main__': unittest.main()
