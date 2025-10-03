# --- START OF FILE common.py ---

import math
from urllib.parse import quote_plus

# ==== CATEGORY MAP (EN+TH) - REFINED VERSION ====
# ปรับปรุงให้แต่ละหมวดหมู่มีความเฉพาะเจาะจงมากขึ้น ลดการทับซ้อน
CATEGORY_MAP = {
    "ธรรมชาติ": ["park", "natural_feature", "campground", "rv_park", "zoo"],
    "วัด": ["place_of_worship", "hindu_temple", "mosque", "church"],
    "คาเฟ่": ["cafe", "bakery"],
    "ร้านอาหาร": ["restaurant", "meal_takeaway", "food"],
    "แหล่งเรียนรู้": ["museum", "library", "art_gallery", "book_store", "university"],
    "จุดชมวิว": ["tourist_attraction"], # ให้ tourist_attraction เป็นของจุดชมวิวเป็นหลัก
    "ชุมชน/ตลาด": ["market", "shopping_mall", "store", "supermarket"],
}

CATEGORY_KEYWORDS = {
    "ธรรมชาติ": ["national park", "waterfall", "mountain", "beach", "forest", "nature", "อุทยาน", "น้ำตก", "ภูเขา", "ป่า", "ชายหาด", "สวนสัตว์"],
    "วัด": ["temple", "wat", "mosque", "church", "วัด", "โบสถ์", "มัสยิด", "ศาลเจ้า"],
    "คาเฟ่": ["cafe", "coffee", "bakery", "คาเฟ่", "กาแฟ", "เบเกอรี่"],
    "ร้านอาหาร": ["restaurant", "food", "ร้านอาหาร", "อาหาร", "โรงแรม"],
    "แหล่งเรียนรู้": ["museum", "library", "gallery", "พิพิธภัณฑ์", "ห้องสมุด", "หอศิลป์"],
    "จุดชมวิว": ["viewpoint", "scenic", "skywalk", "จุดชมวิว", "ทิวทัศน์", "สกายวอล์ค"],
    "ชุมชน/ตลาด": ["market", "shopping", "mall", "ตลาด", "ห้าง", "ชุมชน"],
}

THAI_PROVINCES = [
    "กรุงเทพมหานคร", "สมุทรปราการ", "นนทบุรี", "ปทุมธานี", "พระนครศรีอยุธยา",
    "อ่างทอง", "ลพบุรี", "สิงห์บุรี", "ชัยนาท", "สระบุรี",
    "ชลบุรี", "ระยอง", "จันทบุรี", "ตราด",
    "ฉะเชิงเทรา", "ปราจีนบุรี", "นครนายก", "สระแก้ว",
    "นครราชสีมา", "บุรีรัมย์", "สุรินทร์", "ศรีสะเกษ", "อุบลราชธานี", "ยโสธร", "ชัยภูมิ", "อำนาจเจริญ",
    "หนองบัวลำภู", "ขอนแก่น", "อุดรธานี", "เลย", "หนองคาย", "มหาสารคาม", "ร้อยเอ็ด", "กาฬสินธุ์", "สกลนคร", "นครพนม", "มุกดาหาร",
    "เชียงใหม่", "ลำพูน", "ลำปาง", "อุตรดิตถ์", "แพร่", "น่าน", "พะเยา", "เชียงราย", "แม่ฮ่องสอน",
    "นครสวรรค์", "อุทัยธานี", "กำแพงเพชร", "ตาก", "สุโขทัย", "พิษณุโลก", "พิจิตร", "เพชรบูรณ์",
    "ราชบุรี", "กาญจนบุรี", "สุพรรณบุรี", "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "เพชรบุรี", "ประจวบคีรีขันธ์",
    "นครศรีธรรมราช", "กระบี่", "พังงา", "ภูเก็ต", "สุราษฎร์ธานี", "ระนอง", "ชุมพร",
    "สงขลา", "สตูล", "ตรัง", "พัทลุง", "ปัตตานี", "ยะลา", "นราธิวาส"
]

def validate_province_in_thailand(name: str) -> bool:
    return True


def km_between(p1, p2):
    R = 6371.0
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def build_maps_link_by_place_id(place_id):
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}"

def build_maps_link_by_latlng(lat, lng, name=""):
    label = quote_plus(name) if name else f"{lat},{lng}"
    return f"https://www.google.com/maps/search/?api=1&query={lat}%2C{lng}&query_place_id=&query={label}"

def estimate_detour_minutes(route_points, place_lat, place_lng):
    if not route_points:
        return None
    min_km = min(km_between((place_lat, place_lng), (p["lat"], p["lng"])) for p in route_points)
    minutes = (2 * min_km / 40.0) * 60.0
    return round(minutes)

def categorize_place(place_data):
    place_types = place_data.get("types", [])
    place_name = (place_data.get("name", "") or "").lower()
    categories = []

    # จาก types
    for th_cat, type_list in CATEGORY_MAP.items():
        if any(place_type in type_list for place_type in place_types):
            if th_cat not in categories:
                categories.append(th_cat)

    # จาก keywords ในชื่อสถานที่
    for th_cat, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword.lower() in place_name for keyword in keywords):
            if th_cat not in categories:
                categories.append(th_cat)

    # ถ้ายังไม่มีหมวดหมู่เลย แต่เป็น tourist_attraction ให้เป็น "จุดชมวิว"
    if not categories and "tourist_attraction" in place_types:
        categories.append("จุดชมวิว")
        
    return categories

def filter_places_by_categories(places, selected_categories):
    if not selected_categories:
        return places

    filtered_places = []
    for place in places:
        place_categories = categorize_place(place)
        if any(cat in selected_categories for cat in place_categories):
            filtered_places.append(place)

    return filtered_places