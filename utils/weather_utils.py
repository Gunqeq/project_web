import requests
from datetime import datetime
from config import OPENWEATHER_API_KEY

def get_weather(lat, lon):
    if not OPENWEATHER_API_KEY:
        return None
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "th"
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return {
            "condition": data["weather"][0]["description"] if data.get("weather") else None,
            "temp_c": data.get("main", {}).get("temp"),
            "humidity": data.get("main", {}).get("humidity"),
            "wind_kph": round(float(data.get("wind", {}).get("speed", 0))*3.6, 1) if data.get("wind") else None,
            "icon": f"https://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png" if data.get("weather") else None,
            "as_of": datetime.fromtimestamp(data.get("dt", 0)).strftime("%Y-%m-%d %H:%M") if data.get("dt") else None,
        }
    except Exception:
        return None