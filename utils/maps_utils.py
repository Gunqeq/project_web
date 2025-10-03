import requests
from config import GOOGLE_MAPS_API_KEY

def place_details(place_id, fields=("name","opening_hours","current_opening_hours","formatted_address","geometry","rating","user_ratings_total","international_phone_number","website","types","reviews")):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": ",".join(fields),
        "language": "th",
        "region": "th",
        "key": GOOGLE_MAPS_API_KEY,
    }
    r = requests.get(url, params=params, timeout=10)
    return r.json().get("result", {})


def text_search(query, pagetoken=None):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "language": "th", "region": "th", "key": GOOGLE_MAPS_API_KEY}
    if pagetoken:
        params["pagetoken"] = pagetoken
    r = requests.get(url, params=params, timeout=10)
    return r.json()

def nearby_search(lat, lng, radius_m=1500, type_filters=None, keyword=None):
    """ปรับปรุงให้ค้นหาแม่นยำขึ้น"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius_m,
        "language": "th",
        "region": "th",
        "key": GOOGLE_MAPS_API_KEY,
    }
    if keyword:
        params["keyword"] = keyword
    if type_filters:
        # Use first type (API supports one 'type')
        params["type"] = type_filters[0]
    r = requests.get(url, params=params, timeout=10)
    return r.json()

def directions(origin, destination, mode="driving"):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "language": "th",
        "region": "th",
        "alternatives": "false",
        "key": GOOGLE_MAPS_API_KEY,
    }
    r = requests.get(url, params=params, timeout=10)
    return r.json()
