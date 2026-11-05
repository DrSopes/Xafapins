import argparse
import json
import yaml
import math
import os

def load_rules(path="config/species_rules.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def is_in_catalonia_land(lat, lon):
    """Malla de contorno terrestre de Cataluña."""
    if lat < 40.52 or lat > 42.88 or lon < 0.16 or lon > 3.33:
        return False
    # Filtro del mar Mediterráneo
    if lon > 1.35 and lat < 41.15 and (lat < 40.5 + (lon - 0.4) * 0.55):
        return False
    if lon > 2.15 and lat < 41.40:
        return False
    if lon > 3.00 and lat < 41.75:
        return False
    if lat > 42.85:
        return False
    return True

def get_fine_habitat(lat, lon):
    """
    Gradiente continuo de suelo (pH) y masa forestal con transiciones suaves.
    """
    # 1. Gradiente de pH continuo
    # Zonas ácidas (silíceas): Pirineo axial y Montseny/Guilleries
    dist_pirineu = max(0.0, lat - 42.1)
    dist_montseny = math.sqrt((lat - 41.77)**2 + (lon - 2.45)**2)
    
    if dist_pirineu > 0:
        ph = max(4.6, 6.2 - dist_pirineu * 2.5)
        tree_id = 1 # Pi roig / Faig / Avet
        tree_name = "Pi roig / Faig / Avet"
    elif dist_montseny < 0.35:
        ph = 5.2
        tree_id = 1
        tree_name = "Castanyer / Alzina / Faig"
    elif lon < 1.1:
        ph = min(8.3, 7.5 + (1.1 - lon) * 0.8)
        tree_id = 3 # Plana / Matoll / Conreus
        tree_name = "Secà / Garriga / Matollar"
    elif lat > 41.8 and lon < 1.7:
        ph = 7.6
        tree_id = 2 # Prepirineu calcari
        tree_name = "Pi negre / Roure / Pinyaire"
    else:
        ph = 7.3
        tree_id = 4 # Litoral i prelitoral calcari
        tree_name = "Pi blanc / Alzinar"

    # Clasificación descriptiva de suelo
    if ph < 6.2:
        soil_type = "Silici (Àcid)"
    elif ph > 7.6:
        soil_type = "Calcari dur (Bàsic)"
    else:
        soil_type = "Neutre / Calcari suau"

    return round(ph, 2), soil_type, tree_id, tree_name

def interpolate_meteo(target_lat, target_lon, meteo_pts):
    """Interpolación espacial por distancia inversa (IDW) sobre los 4 vecinos más próximos."""
    dists = []
    for pt in meteo_pts:
        d = math.hypot(target_lat - pt["lat"], target_lon - pt["lon"])
        dists.append((d, pt))
    
    dists.sort(key=lambda x: x[0])
    top = dists[:4]
    
    if top[0][0] < 1e-5:
        p0 = top[0][1]
        return p0.get("rain_past_21d", 0), p0.get("t_min_avg", 10), p0.get("frost_days", 0)

    weights = [1.0 / (d[0] ** 2) for d in top]
    w_sum = sum(weights)
    
    rain = sum(d[1].get("rain_past_21d", 0) * w for d, w in zip(top, weights)) / w_sum
    t_min = sum(d[1].get("t_min_avg", 10) * w for d, w in zip(top, weights)) / w_sum
    frost = sum(d[1].get("frost_days", 0) * w for d, w in zip(top, weights)) / w_sum
    
    return round(rain, 1), round(t_min, 1), int(round(frost))

def calculate_suitability(rain, t_min, frost_days, rule, ph, tree_id):
    rain_opt = rule["meteo_triggers"]["rain_optimal_mm"]
    rain_min = rule["meteo_triggers"]["rain_min_mm"]
    
    if rain < rain_min:
        rain_score = (rain / rain_min) * 0.2
    else:
        rain_score = min(1.0, 0.4 + 0.6 * (rain - rain_min) / (rain_opt - rain_min + 1e-5))

    t_opt = rule["meteo_triggers"]["temp_optimal_celsius"]
    t_req_min = rule["meteo_triggers"]["temp_min_celsius"]
    t_req_max = rule["meteo_triggers"]["temp_max_celsius"]
    
    if t_min < t_req_min or t_min > t_req_max:
        temp_score = 0.15
    else:
        dist = abs(t_min - t_opt)
        temp_score = max(0.2, 1.0 - (dist / 9.0))

    frost_pen_days = rule["meteo_triggers"]["frost_penalty_days"]
    frost_factor = max(0.0, 1.0 - (frost_days / max(frost_pen_days, 1)) * 0.4)

    # Coincidencia con arbolado y pH
    ph_min, ph_max = rule["ph_min"], rule["ph_max"]
    ph_factor = 1.0 if (ph_min <= ph <= ph_max) else 0.2
    tree_factor = 1.0 if (tree_id in rule["tree_target"]) else 0.15

    score = (rain_score * 0.55 + temp_score * 0.45) * frost_factor * ph_factor * tree_factor
    return round(min(max(score, 0.0), 1.0), 3)

def generate_predictions(species="lactarius_deliciosus"):
    rules = load_rules()
    if species not in rules:
        raise ValueError(f"Especie {species} no catalogada.")
        
    rule = rules[species]
    with open("data/meteo_catalunya_latest.json", "r") as f:
        meteo_data = json.load(f)["data"]

    # Malla de alta densidad (~2.5 km de resolución)
    fine_step = 0.025
    min_lon, min_lat, max_lon, max_lat = 0.18, 40.52, 3.32, 42.86
    
    lons = [round(min_lon + i * fine_step, 4) for i in range(int((max_lon - min_lon) / fine_step) + 1)]
    lats = [round(min_lat + i * fine_step, 4) for i in range(int((max_lat - min_lat) / fine_step) + 1)]

    features = []
    for lat in lats:
        for lon in lons:
            if not is_in_catalonia_land(lat, lon):
                continue
                
            ph, soil_type, tree_id, tree_name = get_fine_habitat(lat, lon)
            rain, t_min, frost = interpolate_meteo(lat, lon, meteo_data)
            score = calculate_suitability(rain, t_min, frost, rule, ph, tree_id)

            # Para la capa de suelo, convertimos el pH en un valor normalizado [0, 1]
            # 0.0 (muy ácido, 4.5) -> 1.0 (muy básico, 8.5)
            ph_norm = round(min(max((ph - 4.5) / 4.0, 0.0), 1.0), 3)

            features.append({
                "type": "Feature",
                "properties": {
                    "species": rule["common_name"],
                    "score": score,
                    "rain_21d": rain,
                    "temp_min": t_min,
                    "soil_type": soil_type,
                    "ph": ph,
                    "ph_norm": ph_norm,
                    "tree_id": tree_id,
                    "tree_type": tree_name
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            })

    out_file = f"web/prediction_{species}.geojson"
    os.makedirs("web", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    print(f"✓ Generado {out_file} con {len(features)} puntos de alta resolución.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", default="lactarius_deliciosus")
    args = parser.parse_args()
    generate_predictions(args.species)
