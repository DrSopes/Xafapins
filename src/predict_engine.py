import argparse
import json
import yaml
import os

def load_rules(path="config/species_rules.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def calculate_suitability(pt, rule):
    rain = pt.get("rain_past_21d", 0.0)
    rain_opt = rule["meteo_triggers"]["rain_optimal_mm"]
    rain_min = rule["meteo_triggers"]["rain_min_mm"]
    
    if rain < rain_min:
        rain_score = (rain / rain_min) * 0.3
    else:
        rain_score = min(1.0, 0.4 + 0.6 * (rain - rain_min) / (rain_opt - rain_min + 1e-5))
        
    t_min = pt.get("t_min_avg", 10.0)
    t_opt = rule["meteo_triggers"]["temp_optimal_celsius"]
    t_req_min = rule["meteo_triggers"]["temp_min_celsius"]
    t_req_max = rule["meteo_triggers"]["temp_max_celsius"]
    
    if t_min < t_req_min or t_min > t_req_max:
        temp_score = 0.2
    else:
        dist = abs(t_min - t_opt)
        temp_score = max(0.2, 1.0 - (dist / 10.0))
        
    frost_penalty = max(0.0, 1.0 - (pt.get("frost_days", 0) * 0.25))
    return round(min(max((rain_score * 0.6 + temp_score * 0.4) * frost_penalty, 0.0), 1.0), 3)

def generate_predictions(species="lactarius_deliciosus"):
    rules = load_rules()
    rule = rules[species]
    meteo_file = "data/meteo_catalunya_latest.json"
    
    if not os.path.exists(meteo_file):
        # Datos de demostración si aún no se ha ejecutado el descargador
        mock = []
        for lat_idx in range(12):
            lat = 40.6 + lat_idx * 0.2
            for lon_idx in range(14):
                lon = 0.3 + lon_idx * 0.2
                mock.append({
                    "lat": round(lat, 3), "lon": round(lon, 3),
                    "rain_past_21d": round(45 + (lat - 40.5) * 25 + (lon_idx % 3) * 10, 1),
                    "t_min_avg": round(14.0 - (lat - 40.5) * 4, 1),
                    "t_max_avg": round(22.0 - (lat - 40.5) * 4, 1),
                    "frost_days": 1 if lat > 42.2 else 0
                })
        with open(meteo_file, "w") as f:
            json.dump({"data": mock}, f)

    with open(meteo_file, "r") as f:
        data = json.load(f)["data"]
        
    features = []
    d = 0.04
    for pt in data:
        score = calculate_suitability(pt, rule)
        lon, lat = pt["lon"], pt["lat"]
        poly = [[lon-d, lat-d], [lon+d, lat-d], [lon+d, lat+d], [lon-d, lat+d], [lon-d, lat-d]]
        features.append({
            "type": "Feature",
            "properties": {
                "species": rule["common_name"],
                "score": score,
                "rain_21d": pt["rain_past_21d"],
                "temp_min": pt["t_min_avg"],
                "frost_days": pt["frost_days"]
            },
            "geometry": {"type": "Polygon", "coordinates": [poly]}
        })
        
    out_file = f"web/prediction_{species}.geojson"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)
    print(f"Generado: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", default="lactarius_deliciosus")
    args = parser.parse_args()
    generate_predictions(args.species)
