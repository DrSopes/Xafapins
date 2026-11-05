import argparse
import json
import yaml
import os

def load_rules(path="config/species_rules.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def is_in_catalonia_land(lat, lon):
    """Filtro de contorno terrestre de Cataluña para descartar mar y Francia."""
    if lat < 40.52 or lat > 42.88 or lon < 0.16 or lon > 3.33:
        return False
    # Filtro litoral mediterráneo
    if lon > 1.35 and lat < 41.15 and (lat < 40.5 + (lon - 0.4) * 0.55):
        return False
    if lon > 2.15 and lat < 41.40:
        return False
    if lon > 3.00 and lat < 41.75:
        return False
    # Filtro frontera norte pirenaica
    if lat > 42.85:
        return False
    return True

def get_habitat_info(lat, lon):
    """Atribución ambiental de tipo de bosque y pH de suelo."""
    if lat > 42.1 or (lon > 2.2 and 41.65 < lat < 41.95):  # Pirineus i Montseny
        ph = 5.2
        soil_type = "Silici (Àcid)"
        tree_type = "Pi roig / Faig / Castanyer"
        tree_id = 1
    elif lat > 41.8 and lon < 1.5:  # Prepirineu de Ponent
        ph = 7.4
        soil_type = "Calcari (Bàsic)"
        tree_type = "Pi negre / Roure"
        tree_id = 2
    elif lon < 1.0:  # Plana de Ponent
        ph = 7.8
        soil_type = "Calcari argilós"
        tree_type = "Garriga / Conreus"
        tree_id = 3
    else:  # Litoral i Prelitoral
        ph = 7.2
        soil_type = "Calcari (Bàsic)"
        tree_type = "Pi blanc / Alzina"
        tree_id = 4
        
    return ph, soil_type, tree_type, tree_id

def calculate_suitability(pt, rule, ph):
    rain = pt.get("rain_past_21d", 0.0)
    rain_opt = rule["meteo_triggers"]["rain_optimal_mm"]
    rain_min = rule["meteo_triggers"]["rain_min_mm"]
    
    if rain < rain_min:
        rain_score = (rain / rain_min) * 0.25
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
    
    # Restricción de pH
    ph_min = rule.get("ph_min", 4.0)
    ph_max = rule.get("ph_max", 8.5)
    soil_factor = 1.0 if (ph_min <= ph <= ph_max) else 0.20

    final_score = (rain_score * 0.55 + temp_score * 0.45) * frost_penalty * soil_factor
    return round(min(max(final_score, 0.0), 1.0), 3)

def generate_predictions(species="lactarius_deliciosus"):
    rules = load_rules()
    rule = rules[species]
    meteo_file = "data/meteo_catalunya_latest.json"
    
    with open(meteo_file, "r") as f:
        data = json.load(f)["data"]
        
    features = []
    for pt in data:
        lat, lon = pt["lat"], pt["lon"]
        if not is_in_catalonia_land(lat, lon):
            continue
            
        ph, soil_type, tree_type, tree_id = get_habitat_info(lat, lon)
        score = calculate_suitability(pt, rule, ph)
        
        # Geometría tipo Point para interpolación continua (Heatmap)
        features.append({
            "type": "Feature",
            "properties": {
                "species": rule["common_name"],
                "score": score,
                "rain_21d": pt.get("rain_past_21d", 0),
                "temp_min": pt.get("t_min_avg", 0),
                "soil_type": soil_type,
                "ph": ph,
                "tree_type": tree_type,
                "tree_id": tree_id
            },
            "geometry": {
                "type": "Point",
                "coordinates": [round(lon, 4), round(lat, 4)]
            }
        })
        
    out_file = f"web/prediction_{species}.geojson"
    os.makedirs("web", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)
    print(f"Generat {out_file} amb {len(features)} punts terrestres.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", default="lactarius_deliciosus")
    args = parser.parse_args()
    generate_predictions(args.species)
