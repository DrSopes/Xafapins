import os
import json
import requests

def load_prediction(species):
    filepath = f"web/prediction_{species}.geojson"
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def format_report():
    species_map = {
        "lactarius_deliciosus": "🌲 Rovelló / Pinetell",
        "boletus_edulis": "🍄 Cep (Boletus edulis)"
    }
    
    lines = ["<b>🍄 XAFAPINS - Butlletí Micològic Diari 🌲</b>\n"]
    
    for sp_key, sp_name in species_map.items():
        data = load_prediction(sp_key)
        if not data:
            continue
            
        features = data.get("features", [])
        # Ordenar por índice de probabilidad descendente
        sorted_spots = sorted(
            features, 
            key=lambda f: f["properties"].get("score", 0), 
            reverse=True
        )
        
        top_spots = [s for s in sorted_spots if s["properties"].get("score", 0) >= 0.5][:3]
        
        lines.append(f"<b>{sp_name}</b>")
        if not top_spots:
            lines.append("<i>Sense zones òptimes detectades avui (falta pluja o fred acusat).</i>\n")
            continue
            
        for i, spot in enumerate(top_spots, 1):
            p = spot["properties"]
            coords = spot["geometry"]["coordinates"][0][0]
            lon, lat = coords[0], coords[1]
            score_pct = int(p["score"] * 100)
            
            # Enlace directo a Google Maps / OpenStreetMap
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat:.3f},{lon:.3f}"
            
            lines.append(
                f"{i}. <b>Probabilitat: {score_pct}%</b>\n"
                f"   🌧️ Pluja 21d: {p['rain_21d']} mm | 🌡️ T.mín: {p['temp_min']}°C\n"
                f"   📍 <a href='{maps_url}'>Veure coordenades ({lat:.2f}, {lon:.2f})</a>"
            )
        lines.append("")
        
    lines.append("🌐 <i>Consulta el visor complet a la teva web local de Xafapins.</i>")
    return "\n".join(lines)

def send_telegram_message():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("[!] Falten les variables TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")
        return

    text = format_report()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    res = requests.post(url, json=payload, timeout=10)
    if res.status_code == 200:
        print("[✓] Butlletí de Xafapins enviat correctament a Telegram.")
    else:
        print(f"[!] Error enviant a Telegram: {res.status_code} - {res.text}")

if __name__ == "__main__":
    send_telegram_message()