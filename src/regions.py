"""Spain's 19 NUTS-2 regions, including both archipelagos and autonomous cities."""
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]

def regions():
    features=json.loads((ROOT/'data/spain-regions.geojson').read_text(encoding='utf-8'))['features']
    for feature in features:
        feature['id']=feature['properties']['id']
    return features

def region_geometry(region_id=None):
    features = regions()
    if region_id:
        features = [f for f in features if f['properties']['id'] == region_id]
        if not features:
            raise ValueError(f'Unknown Spanish region: {region_id}')
    return unary_union([shape(f['geometry']) for f in features])

def weather_points(step, geometry):
    """Sample components separately; retain a point even on tiny islands/cities."""
    import math
    from shapely.geometry import Point
    result = set()
    for part in geometry.geoms if geometry.geom_type == 'MultiPolygon' else [geometry]:
        region = part.buffer(step)
        west, south, east, north = region.bounds
        for y in range(math.ceil((north-south)/step)+1):
            for x in range(math.ceil((east-west)/step)+1):
                lat,lon=round(south+y*step,5),round(west+x*step,5)
                if region.covers(Point(lon,lat)):
                    result.add((lat,lon))
    return sorted(result)
