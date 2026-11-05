import argparse
import json
import requests
from datetime import datetime, timedelta

def fetch_grid_weather(bbox=(0.15, 40.5, 3.35, 42.9), step=0.20, history_days=21):
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = [round(min_lon + i * step, 4) for i in range(int((max_lon - min_lon) / step) + 1)]
    lats = [round(min_lat + i * step, 4) for i in range(int((max_lat - min_lat) / step) + 1)]
    
    # Generar todos los pares de coordenadas
    points = [(lat, lon) for lat in lats for lon in lons]
    print(f"Descargando {len(points)} puntos en lote...")

    # Open-Meteo acepta listas separadas por comas (lotes de hasta 50-100 puntos por llamada)
    batch_size = 50
    results = []
    
    for i in range(0, len(points), batch_size):
        chunk = points[i:i + batch_size]
        lat_str = ",".join(str(p[0]) for p in chunk)
        lon_str = ",".join(str(p[1]) for p in chunk)
        
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat_str}&longitude={lon_str}&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
            f"&past_days={history_days}&forecast_days=7&timezone=Europe%2FMadrid"
        )
        
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            data = res.json()
            # Si se envía más de un punto, devuelve una lista de diccionarios
            items = data if isinstance(data, list) else [data]
            for item in items:
                daily = item.get("daily", {})
                precip = daily.get("precipitation_sum", [])
                t_min = daily.get("temperature_2m_min", [])[:history_days]
                t_max = daily.get("temperature_2m_max", [])[:history_days]
                
                results.append({
                    "lat": item.get("latitude"),
                    "lon": item.get("longitude"),
                    "rain_past_21d": round(sum(precip[:history_days]), 1) if precip else 0.0,
                    "t_min_avg": round(sum(t_min) / max(len(t_min), 1), 1) if t_min else 0.0,
                    "t_max_avg": round(sum(t_max) / max(len(t_max), 1), 1) if t_max else 0.0,
                    "frost_days": sum(1 for t in t_min if t <= 0) if t_min else 0
                })
            print(f"Procesados {min(i + batch_size, len(points))}/{len(points)} puntos...", flush=True)

    with open("data/meteo_catalunya_latest.json", "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "data": results}, f, indent=2)
    print("✓ Meteo descargada con éxito en segundos.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-step", type=float, default=0.20)
    args = parser.parse_args()
    fetch_grid_weather(step=args.grid_step)