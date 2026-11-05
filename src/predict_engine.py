import argparse
import json
import yaml
import os

def load_rules(path="config/species_rules.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def is_in_catalonia_land(lat, lon):
    """Filtro geográfico para descartar mar y zonas fuera del territorio catalán."""
    if lat < 40.52 or lat > 42.88 or lon < 0.16 or lon > 3.33:
        return False
    # Filtro de la costa catalana (aproximación para descartar mar abierto)
    if lon > 1.4 and lat < 41.15 and (lat < 40.5 + (lon - 0.5) * 0.55):
        return False
    if lon > 2.2 and lat < 41.4:
        return False
    if lon > 3.0 and lat < 41.75:
        return False
    return True

def get_habitat_info(lat, lon):
    """
    Infiere el tipo de suelo (pH) y arbolado dominante según la geografía catalana:
    - Pirineos/Montseny/Guilleries: silíceo/ácido (Castanyer, Faig, Pi roig).
    - Litoral/Prelitoral/Depressió Central: calcáreo/básico (Pi blanc, Alzina).
    """
    # Determinación aproximada de pH (Suelo ácido vs calcáreo)
    if lat > 42.1 or (lon > 2.2 and 41.65 < lat < 41.95):  # Pirineu y Montseny
        ph = 5.2
        soil_type = "Silici (Àcid)"
        tree_type = "Pi roig / Faig / Castanyer"
    elif lat > 41.8 and lon < 1.5:  # Prepirineu lleidatà
        ph = 7.4
        soil_type = "Calcari (Bàsic)"
        tree_type = "Pi negre / Roure"
    elif lon < 1.0:  # Ponent / Terres de Ponent
        ph = 7.8
        soil_type = "Calcari argilós"
        tree_type = "Garriga / Conreus"
    else:  # Litoral / Prelitoral
        ph = 7.2
        soil_type = "Calcari (Bàsic)"
        tree_type = "Pi blanc / Alzina"
        
    return ph, soil_type, tree_type

def calculate_suitability(pt, rule, ph):
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
    
    # Factor de suelo (penalización si no cuadra con el pH de la especie)
    ph_min = rule.get("ph_min", 4.0)
    ph_max = rule.get("ph_max", 8.5)
    soil_factor = 1.0 if (ph_min <= ph <= ph_max) else 0.25

    final_score = (rain_score * 0.55 + temp_score * 0.45) * frost_penalty * soil_factor
    return round(min(max(final_score, 0.0), 1.0), 3)

def generate_predictions(species="lactarius_deliciosus"):
    rules = load_rules()
    rule = rules[species]
    meteo_file = "data/meteo_catalunya_latest.json"
    
    if not os.path.exists(meteo_file):
        raise FileNotFoundError(f"No existe {meteo_file}. Ejecuta download_meteo.py primero.")

    with open(meteo_file, "r") as f:
        data = json.load(f)["data"]
        
    features = []
    # Usamos d = 0.041 para un step de 0.08, asegurando solapamiento continuo sin huecos
    d_lat = 0.041
    d_lon = 0.041
    
    for pt in data:
        lat, lon = pt["lat"], pt["lon"]
        if not is_in_catalonia_land(lat, lon):
            continue  # Descarta mar y exterior
            
        ph, soil_type, tree_type = get_habitat_info(lat, lon)
        score = calculate_suitability(pt, rule, ph)
        
        poly = [
            [round(lon - d_lon, 4), round(lat - d_lat, 4)],
            [round(lon + d_lon, 4), round(lat - d_lat, 4)],
            [round(lon + d_lon, 4), round(lat + d_lat, 4)],
            [round(lon - d_lon, 4), round(lat + d_lat, 4)],
            [round(lon - d_lon, 4), round(lat - d_lat, 4)]
        ]
        
        features.append({
            "type": "Feature",
            "properties": {
                "species": rule["common_name"],
                "score": score,
                "rain_21d": pt.get("rain_past_21d", 0),
                "temp_min": pt.get("t_min_avg", 0),
                "soil_type": soil_type,
                "ph": ph,
                "tree_type": tree_type
            },
            "geometry": {"type": "Polygon", "coordinates": [poly]}
        })
        
    out_file = f"web/prediction_{species}.geojson"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)
    print(f"Generado {out_file} con {len(features)} celdas terrestres.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", default="lactarius_deliciosus")
    args = parser.parse_args()
    generate_predictions(args.species)
