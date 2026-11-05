import os
import json
import sys
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
    
    web_url = os.environ.get("PAGES_URL", "https://drsopes.github.io/Xafapins/")
    lines = ["<b>🍄 XAFAPINS - Butlletí Micològic Diari 🌲</b>\n"]
    
    for sp_key, sp_name in species_map.items():
        data = load_prediction(sp_key)
        if not data:
            continue
            
        features = data.get("features", [])
        sorted_spots = sorted(
            features, 
            key=lambda f: f["properties"].get("score", 0), 
            reverse=True
        )
        
        top_spots = [s for s in sorted_spots if s["properties"].get("score", 0) >= 0.4][:3]
        
        lines.append(f"<b>{sp_name}</b>")
        if not top_spots:
            lines.append("<i>Sense zones favorables detectades avui (manca d'humitat acumulada).</i>\n")
            continue
            
        for i, spot in enumerate(top_spots, 1):
            p = spot["properties"]
            # Coordenadas (Point)
            coords = spot["geometry"]["coordinates"]
            lon, lat = coords[0], coords[1]
            score_pct = int(p["score"] * 100)
            
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat:.4f},{lon:.4f}"
            
            lines.append(
                f"{i}. <b>Probabilitat: {score_pct}%</b>\n"
                f"   🌧️ Pluja 21d: {p['rain_21d']} mm | 🌡️ T.mín: {p['temp_min']}°C\n"
                f"   🌲 Bosc: {p.get('tree_type', 'N/A')}\n"
                f"   📍 <a href='{maps_url}'>Veure a Google Maps ({lat:.2f}, {lon:.2f})</a>"
            )
        lines.append("")
        
    lines.append(f"🗺️ <b>Mapa interactiu continu:</b>\n👉 <a href='{web_url}'>{web_url}</a>")
    return "\n".join(lines)

def send_telegram_message():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token:
        print("❌ ERROR: El secret TELEGRAM_BOT_TOKEN no està definit a GitHub Secrets.", file=sys.stderr)
        sys.exit(1)
    if not chat_id:
        print("❌ ERROR: El secret TELEGRAM_CHAT_ID no està definit a GitHub Secrets.", file=sys.stderr)
        sys.exit(1)

    # Limpiar posibles comillas o espacios accidentales en secrets
    token = token.strip().replace('"', '').replace("'", "")
    chat_id = chat_id.strip().replace('"', '').replace("'", "")

    text = format_report()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    print(f"Enviant missatge al xat {chat_id}...")
    res = requests.post(url, json=payload, timeout=15)
    
    if res.status_code != 200:
        print(f"❌ Error de Telegram API ({res.status_code}): {res.text}", file=sys.stderr)
        print("💡 Recorda: Si és la primera vegada, HAS d'enviar /start al teu bot des de Telegram abans que pugui enviar-te res.", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ Missatge enviat amb èxit a Telegram!")

if __name__ == "__main__":
    send_telegram_message()
