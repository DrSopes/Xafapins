import argparse
import json
import time
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def get_resilient_session():
    """Configura reintentos automáticos ante timeouts o saturación (429, 5xx)."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_grid_weather(bbox=(0.15, 40.5, 3.35, 42.9), step=0.08, history_days=21):
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = [round(min_lon + i * step, 4) for i in range(int((max_lon - min_lon) / step) + 1)]
    lats = [round(min_lat + i * step, 4) for i in range(int((max_lat - min_lat) / step) + 1)]
    
    points = [(lat, lon) for lat in lats for lon in lons]
    print(f"Descargando {len(points)} puntos en lotes seguros...", flush=True)

    session = get_resilient_session()
    batch_size = 25  # Tamaño de lote moderado para evitar timeouts en Open-Meteo
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
        
        try:
            res = session.get(url, timeout=35)
            if res.status_code == 200:
                data = res.json()
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
            else:
                print(f"[!] Respuesta {res.status_code} en lote {i}. Omitiendo...", flush=True)
        except Exception as e:
            print(f"[!] Error puntual en lote {i}: {e}. Continuando con los demás...", flush=True)
            
        time.sleep(0.3)  # Pausa para evitar rate-limiting

    with open("data/meteo_catalunya_latest.json", "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "data": results}, f, indent=2)
