import argparse
import json
import time
import requests
from datetime import datetime, timedelta

def fetch_grid_weather(bbox=(0.15, 40.5, 3.35, 42.9), step=0.15, history_days=21):
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = [round(min_lon + i * step, 4) for i in range(int((max_lon - min_lon) / step) + 1)]
    lats = [round(min_lat + i * step, 4) for i in range(int((max_lat - min_lat) / step) + 1)]
    
    today = datetime.now()
    results = []
    
    print(f"Consultando Open-Meteo para Cataluña ({len(lats)}x{len(lons)} puntos)...")
    for lat in lats:
        for lon in lons:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
                f"&past_days={history_days}&forecast_days=7&timezone=Europe%2FMadrid"
            )
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    daily = res.json().get("daily", {})
                    precip = daily.get("precipitation_sum", [])
                    t_min = daily.get("temperature_2m_min", [])[:history_days]
                    t_max = daily.get("temperature_2m_max", [])[:history_days]
                    
                    results.append({
                        "lat": lat,
                        "lon": lon,
                        "rain_past_21d": round(sum(precip[:history_days]), 1),
                        "t_min_avg": round(sum(t_min) / max(len(t_min), 1), 1),
                        "t_max_avg": round(sum(t_max) / max(len(t_max), 1), 1),
                        "frost_days": sum(1 for t in t_min if t <= 0)
                    })
                time.sleep(0.05)
            except Exception as e:
                print(f"Error en ({lat}, {lon}): {e}")
                
    with open("data/meteo_catalunya_latest.json", "w", encoding="utf-8") as f:
        json.dump({"timestamp": today.isoformat(), "data": results}, f, indent=2)
    print("Meteo guardada en data/meteo_catalunya_latest.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-step", type=float, default=0.15)
    args = parser.parse_args()
    fetch_grid_weather(step=args.grid_step)
