from utils.maps_utils import text_search, place_details
from utils.weather_utils import get_weather
from utils.common import categorize_place, filter_places_by_categories, build_maps_link_by_place_id, build_maps_link_by_latlng
from config import GOOGLE_MAPS_API_KEY

def search_by_province(province: str, categories_th=None, limit=20):
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "GOOGLE_MAPS_API_KEY not configured"}

    query = f"สถานที่ท่องเที่ยว {province} ประเทศไทย"
    base = text_search(query)
    results = base.get("results", [])

    if categories_th:
        results = filter_places_by_categories(results, categories_th)

    items = []
    for r in results[:limit]:
        place_id = r.get("place_id")
        details = place_details(place_id)
        name = details.get("name", r.get("name"))
        addr = details.get("formatted_address", r.get("formatted_address"))
        loc = details.get("geometry", {}).get("location", r.get("geometry", {}).get("location", {}))
        lat, lng = loc.get("lat"), loc.get("lng")
        opening = details.get("current_opening_hours") or details.get("opening_hours")
        weekday_text = opening.get("weekday_text") if opening else None
        map_url = build_maps_link_by_place_id(place_id) if place_id else build_maps_link_by_latlng(lat, lng, name)
        rating = details.get("rating", r.get("rating"))
        total = details.get("user_ratings_total", r.get("user_ratings_total"))
        website = details.get("website")
        weather = get_weather(lat, lng) if (lat and lng) else None

        # ใช้ function ใหม่ในการจัดหมวดหมู่
        cats = categorize_place(details if details.get("types") else r)

        items.append({
            "name": name,
            "place_id": place_id,
            "address": addr,
            "location": {"lat": lat, "lng": lng},
            "rating": rating,
            "user_ratings_total": total,
            "website": website,
            "opening_hours_text": weekday_text,
            "map_url": map_url,
            "weather": weather,
            "categories": cats
        })
        items.sort(key=lambda x: (
        -(x.get("user_ratings_total") or 0)
        -(x.get("rating") or 0),      
    ))
    return {"province": province, "items": items}
