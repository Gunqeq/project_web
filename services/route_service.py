# --- START OF FILE route_service.py ---

from utils.maps_utils import directions, nearby_search, place_details
from utils.weather_utils import get_weather
from utils.common import (
    estimate_detour_minutes,
    categorize_place,
    build_maps_link_by_place_id,
    build_maps_link_by_latlng,
    CATEGORY_MAP,
    CATEGORY_KEYWORDS,
    validate_province_in_thailand,
    km_between
)

from config import GOOGLE_MAPS_API_KEY




def route_suggestions(origin, destination, categories_th=None, mode="driving",
                      search_radius_m=2000, per_point=5, max_detour_km=15):
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "GOOGLE_MAPS_API_KEY not configured"}

    # ✅ ไม่ต้องทำความสะอาดชื่อสถานที่เพราะ frontend ทำให้แล้ว
    # แค่เติม ", ประเทศไทย" ถ้ายังไม่มี
    if origin and "ไทย" not in origin and "ประเทศไทย" not in origin:
        origin = f"{origin}, ประเทศไทย"
    
    if destination and "ไทย" not in destination and "ประเทศไทย" not in destination:
        destination = f"{destination}, ประเทศไทย"

    # --- Google Directions API ---
    d = directions(origin, destination, mode=mode)
    if d.get("status") != "OK":
        return {"error": f"Directions failed: {d.get('status')}", "raw": d}

    route = d["routes"][0]
    leg = route["legs"][0]
    steps = leg.get("steps", [])

    # Sample route points
    route_points = []
    for s in steps:
        end = s.get("end_location")
        if end:
            route_points.append({"lat": end["lat"], "lng": end["lng"]})

    # --- Build filters from categories ---
    type_filters = []
    search_keywords = []

    if categories_th:
        for c in categories_th:
            if c in CATEGORY_MAP:
                type_filters.extend(CATEGORY_MAP[c])
            if c in CATEGORY_KEYWORDS:
                search_keywords.extend(CATEGORY_KEYWORDS[c][:2])

    if not type_filters:
        type_filters = ["tourist_attraction", "cafe", "restaurant", "museum", "park"]

    # --- Search nearby places ---
    seen = set()
    found = []

    sample_points = route_points[::max(1, len(route_points)//15 or 1)]  # ~15 points

    for idx, p in enumerate(sample_points):
        for type_filter in type_filters[:3]:
            nr = nearby_search(p["lat"], p["lng"],
                               radius_m=search_radius_m,
                               type_filters=[type_filter])

            for r in nr.get("results", [])[:per_point]:
                pid = r.get("place_id")
                if not pid or pid in seen:
                    continue
                seen.add(pid)

                # filter categories
                if categories_th:
                    place_cats = categorize_place(r)
                    if not any(cat in categories_th for cat in place_cats):
                        continue

                place_lat = r["geometry"]["location"]["lat"]
                place_lng = r["geometry"]["location"]["lng"]

                # Filter by distance from route
                if max_detour_km:
                    min_dist_km = min(km_between((place_lat, place_lng), (point["lat"], point["lng"])) for point in route_points)
                    if min_dist_km > max_detour_km:
                        continue

                detour_min = estimate_detour_minutes(route_points, place_lat, place_lng)
                details = place_details(pid)
                name = details.get("name", r.get("name"))
                addr = details.get("formatted_address", r.get("vicinity"))
                loc = details.get("geometry", {}).get(
                    "location", r.get("geometry", {}).get("location", {})
                )
                lat, lng = loc.get("lat"), loc.get("lng")
                opening = details.get("current_opening_hours") or details.get("opening_hours")
                weekday_text = opening.get("weekday_text") if opening else None
                map_url = (build_maps_link_by_place_id(pid)
                           if pid else build_maps_link_by_latlng(lat, lng, name))
                rating = details.get("rating", r.get("rating"))
                total = details.get("user_ratings_total", r.get("user_ratings_total"))
                website = details.get("website")
                weather = get_weather(lat, lng) if (lat and lng) else None

                cats = categorize_place(details if details.get("types") else r)

                found.append({
                    "name": name,
                    "place_id": pid,
                    "address": addr,
                    "location": {"lat": lat, "lng": lng},
                    "rating": rating,
                    "user_ratings_total": total,
                    "website": website,
                    "opening_hours_text": weekday_text,
                    "map_url": map_url,
                    "weather": weather,
                    "detour_minutes_est": detour_min,
                    "categories": cats
                })

    # Sort by rating and reviews
    found.sort(key=lambda x: (
        -(int(x.get("user_ratings_total", 0) or 0)),
        -(float(x.get("rating", 0) or 0)), 
        x.get("detour_minutes_est") if isinstance(x.get("detour_minutes_est"), int) else 9999
    ))

    summary = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "distance_text": leg.get("distance", {}).get("text"),
        "duration_text": leg.get("duration", {}).get("text"),
        "polyline": route.get("overview_polyline", {}).get("points"),
    }
    

    return {"route": summary, "stops": found[:50]}
