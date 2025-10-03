from linebot.v3.messaging import (
    MessagingApi, ReplyMessageRequest, TextMessage,
    QuickReply, QuickReplyItem, MessageAction,
    FlexMessage, FlexContainer, URIAction  # เพิ่ม URIAction
)
from linebot.v3.messaging.configuration import Configuration
from linebot.v3.messaging.api_client import ApiClient
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent
from linebot.v3.exceptions import InvalidSignatureError
import os
import random
import json
from flask import Flask, render_template, request, abort, jsonify, session
from flask_session import Session
import urllib.parse  # เพิ่ม import urllib.parse
from prompt import PROMPT_FLOW
from google import genai
import re
import logging
import google.generativeai as genai

# Assuming these files exist with the necessary functions/variables
from config import SECRET_KEY, SESSION_TYPE
from utils.maps_utils import directions
from utils.common import build_maps_link_by_latlng, validate_province_in_thailand
from services.route_service import route_suggestions
from services.province_service import search_by_province  
from routes.api import api_bp
from services.gemini_service import summarize_place_reviews, generate_place_summary
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_TYPE"] = SESSION_TYPE
Session(app)

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)         
messaging_api = MessagingApi(api_client)       
handler = WebhookHandler(CHANNEL_SECRET)

app.register_blueprint(api_bp, url_prefix="/api")
@app.route("/")
def home():
    return render_template("index.html")

@app.route('/liff/map')
def liff_map():
    return render_template('liff-map.html')

# จำนวนสถานที่สูงสุดที่จะแสดง
MAX_PLACES = 5

# ข้อมูลหมวดหมู่
CATEGORIES = {
    "ธรรมชาติ": {"emoji": "🏞️", "description": "อุทยาน น้ำตก ภูเขา"},
    "วัด": {"emoji": "🛕", "description": "วัด โบสถ์ สถานที่ศักดิ์สิทธิ์"},
    "คาเฟ่": {"emoji": "☕", "description": "คาเฟ่ เบเกอรี่"},
    "ร้านอาหาร": {"emoji": "🍽️", "description": "ร้านอาหาร อาหารท้องถิ่น"},
    "แหล่งเรียนรู้": {"emoji": "📚", "description": "พิพิธภัณฑ์ หอศิลป์"},
    "จุดชมวิว": {"emoji": "🌅", "description": "จุดชมวิว ทิวทัศน์"},
    "ชุมชน/ตลาด": {"emoji": "🏪", "description": "ตลาด ชุมชน ห้าง"}
}

GREETINGS = [
    "สวัสดีครับ! 😊",
    "หวัดดีครับ! 👋",  
    "ยินดีต้อนรับครับ! 🤗"
]

# User session เก็บข้อมูลชั่วคราว
user_sessions = {}

# --- START: เพิ่มฟังก์ชันใหม่สำหรับเรียก Gemini โดยตรง ---
def ask_gemini_general(prompt):
    """ส่ง Prompt ทั่วไปไปยังโมเดล Gemini"""
    if not gemini_chat:
        return "ขออภัยครับ ฟังก์ชัน AI ทั่วไปไม่พร้อมใช้งานในขณะนี้"
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        full_prompt = (
            "You are a helpful and friendly travel assistant in Thailand. "
            "Please answer the following user query concisely in Thai language.\n\n"
            f"User Query: {prompt}"
        )
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini general query error: {e}")
        return f"ขออภัยครับ เกิดข้อผิดพลาดในการสื่อสารกับ AI: {str(e)}"
# --- END ---


def get_user_session(user_id):
    """ดึงข้อมูล session ของ user"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "mode": None,
            "origin": None,
            "destination": None,
            "province": None,
            "selected_categories": [],
            "last_search_results": [],
            "waiting_for_review": False,
            "current_place": None  # เก็บสถานที่ปัจจุบันสำหรับ "ไปต่อไหนดี"
        }
    return user_sessions[user_id]

# --- START: เพิ่มฟังก์ชันใหม่สำหรับเรียก Gemini โดยตรง ---


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_place_name(name: str) -> str:
    """ทำความสะอาดชื่อสถานที่โดยลบเฉพาะคำถาม/หมวดหมู่ที่ท้ายข้อความ"""
    if not name:
        return ""
    # ลบคำถามทั่วไปที่อยู่ท้ายสุด
    name = re.sub(r'\s*(แวะไหนดี\??|แวะ\s*ไหนดี|ไหนดี)\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\?\s*$', '', name)
    
    # ลบหมวดหมู่ที่อยู่ท้ายสุด (แต่ไม่ลบถ้าเป็นส่วนหนึ่งของชื่อสถานที่)
    categories_pattern = r'\s+(ธรรมชาติ|คาเฟ่|ร้านอาหาร|วัด|ตลาด|จุดชมวิว)\s*$'
    name = re.sub(categories_pattern, '', name, flags=re.IGNORECASE)
    
    return name.strip()

def parse_route_message(msg: str):
    """
    แยกข้อความผู้ใช้ เช่น "ชลบุรี ไป ปราจีนบุรี แวะไหนดี ธรรมชาติ คาเฟ่"
    คืนค่า: origin, destination, categories
    """
    msg = msg.strip()
    categories = []

    # ตัดส่วนหมวดหมู่
    known_cats = ["ธรรมชาติ", "คาเฟ่", "ร้านอาหาร", "วัด", "ตลาด"]
    for cat in known_cats:
        if cat in msg:
            categories.append(cat)
            msg = msg.replace(cat, "")

    # ตัดคำถามทั่วไป
    msg = msg.replace("แวะไหนดี", "").replace("แวะ", "").replace("ไหนดี", "").replace("?", "")

    # แยกจังหวัด
    if "ไป" in msg:
        parts = msg.split("ไป")
        origin = parts[0].strip()
        destination = parts[1].strip()
    else:
        origin, destination = "", ""

    return origin, destination, categories


def ensure_country_hint(name: str) -> str:
    """เติมคำว่า ', ประเทศไทย' ถ้าไม่มี เพื่อช่วย geocoder"""
    if not name:
        return name
    if "ไทย" in name or "ประเทศไทย" in name:
        return name
    return f"{name}, ประเทศไทย"

def create_category_quick_reply():
    """สร้าง Quick Reply สำหรับเลือกหมวดหมู่"""
    quick_reply_items = []
    
    for category, info in CATEGORIES.items():
        quick_reply_items.append(
            QuickReplyItem(
                action=MessageAction(
                    label=f"{info['emoji']} {category}",
                    text=f"เลือก {category}"
                )
            )
        )
    
    quick_reply_items.extend([
        QuickReplyItem(
            action=MessageAction(
                label="🎯 ทั้งหมด",
                text="เลือก ทั้งหมด"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="✅ เสร็จแล้ว",
                text="เสร็จแล้ว"
            )
        )
    ])
    
    return QuickReply(items=quick_reply_items)

def create_mode_quick_reply():
    """สร้าง Quick Reply สำหรับเลือกโหมด"""
    quick_reply_items = [
        QuickReplyItem(
            action=MessageAction(
                label="🗺️ เส้นทาง + สถานที่แวะ",
                text="โหมด เส้นทางแวะ"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="🏞️ สถานที่ในจังหวัด",
                text="โหมด สถานที่"
            )
        )
    ]
    
    return QuickReply(items=quick_reply_items)

def create_review_quick_reply():
    """สร้าง Quick Reply สำหรับถามรีวิว (เหลือแค่ปุ่มค้นหาใหม่)"""
    items = [
        QuickReplyItem(
            action=MessageAction(
                label="🔄 ค้นหาใหม่",
                text="เริ่ม"
            )
        )
    ]
    return QuickReply(items=items)


def get_distance_category(distance_text):
    """จำแนกระยะทางเพื่อใช้ตอบสนองที่เหมาะสม"""
    if not distance_text:
        return "medium"
    
    import re
    numbers = re.findall(r'\d+\.?\d*', distance_text.replace(',', ''))
    if not numbers:
        return "medium"
    
    distance_km = float(numbers[0])
    
    if distance_km < 50:
        return "very_short"
    elif distance_km < 150:
        return "short"
    elif distance_km < 300:
        return "medium"
    elif distance_km < 500:
        return "long"
    else:
        return "very_long"

def create_natural_response(origin, destination, route_info):
    """สร้างการตอบแบบธรรมชาติ"""
    distance = route_info.get("distance", {}).get("text", "?")
    duration = route_info.get("duration", {}).get("text", "?")
    end_location = route_info.get("end_location", {})
    
    maps_link = build_maps_link_by_latlng(
        end_location.get("lat"),
        end_location.get("lng"),
        destination
    )
    
    distance_reactions = {
        "very_short": ["ใกล้มากเลย!", "แป๊บเดียวถึงแล้ว!"],
        "short": ["ไม่ไกลเลย", "ระยะทางกำลังดี"],
        "medium": ["ระยะทางปานกลาง", "เดินทางเพลินๆ"],
        "long": ["ไกลหน่อยนะครับ", "เตรียมตัวดีๆ"],
        "very_long": ["ไกลมากเลย!", "ต้องแวะพักบ้างนะ"]
    }
    
    distance_category = get_distance_category(distance)
    distance_reaction = random.choice(distance_reactions[distance_category])
    
    response = f"🛣️ เส้นทาง {origin} ➜ {destination}\n\n"
    response += f"📏 ระยะทาง: {distance} ({distance_reaction})\n"
    response += f"⏰ เวลาเดินทาง: {duration}\n\n"
    response += f"🗺️ ดูแผนที่: {maps_link}"
    
    return response

def handle_route_with_categories(origin, destination, categories=None):
    """
    จัดการการค้นหาเส้นทางและสถานที่แวะพัก
    """
    # ไม่ต้อง clean ชื่อที่นี่ ให้ route_service.py จัดการเอง
    origin_raw = origin or ""
    dest_raw = destination or ""

    logger.info(f"[route] origin='{origin_raw}' destination='{dest_raw}'")
    logger.info(f"[route] categories={categories}")

    # เรียกใช้ route_suggestions โดยส่งชื่อเต็มไป
    result = route_suggestions(origin_raw, dest_raw, categories_th=categories)
    
    if "error" in result:
        error_msg = result["error"]
        return f"เกิดข้อผิดพลาดครับ: {error_msg}\n\nลองตรวจสอบชื่อสถานที่อีกครั้งนะครับ", []
    
    route_info = result.get("route", {})
    stops = result.get("stops", [])
    
    distance = route_info.get("distance_text", "?")
    duration = route_info.get("duration_text", "?")
    
    # ใช้ชื่อจาก Google Maps API (แม่นยำกว่า)
    origin_display = route_info.get("origin", origin)
    destination_display = route_info.get("destination", destination)
    
    response = f"เส้นทาง {origin_display} ➜ {destination_display}\n\n"
    response += f"ระยะทาง: {distance}\n"
    response += f"เวลา: {duration}\n\n"
    
    if categories:
        category_text = ", ".join(categories)
        response += f"กรองตาม: {category_text}\n\n"
    
    if stops:
        displayed_stops = stops[:MAX_PLACES]
        response += f"สถานที่แนะนำ (ท็อป {len(displayed_stops)} แห่ง):\n\n"
        
        for i, stop in enumerate(displayed_stops, 1):
            name = stop.get("name", "ไม่ระบุชื่อ")
            rating = stop.get("rating")
            detour = stop.get("detour_minutes_est")
            stop_categories = stop.get("categories", [])
            map_url = stop.get("map_url", "")
            weather = stop.get("weather", {})
            
            rating_text = f"⭐{rating}" if rating else "⭐-"
            detour_text = f"(+{detour}นาที)" if detour else ""
            
            response += f"{i}. {name} {rating_text} {detour_text}\n"
            
            if stop_categories:
                cat_emojis = [f"{CATEGORIES[cat]['emoji']} {cat}" for cat in stop_categories[:2] if cat in CATEGORIES]
                if cat_emojis:
                    response += f"   {' • '.join(cat_emojis)}\n"
            
            if weather and weather.get("temp_c"):
                temp = weather.get("temp_c")
                condition = weather.get("condition", "")
                response += f"   {temp}°C {condition}\n"
            
            if map_url:
                response += f"   {map_url}\n"
            
            response += "\n"
        
        response += "พิมพ์ 'รีวิว [ชื่อสถานที่]' หรือพิมพ์แค่ตัวเลข (1-5) เพื่อดูรายละเอียดเพิ่มเติมได้เลยครับ"
        return response, displayed_stops
    else:
        response += "ไม่มีสถานที่แวะตามหมวดหมู่ที่เลือก\nลองเปลี่ยนหมวดหมู่ดูมั้ยครับ?"
        return response, []

def handle_province_with_categories(province, categories=None):
    """จัดการการค้นหาสถานที่ในจังหวัด"""
    result = search_by_province(province, categories_th=categories, limit=10)
    
    if "error" in result:
        return f"ขอโทษครับ หาข้อมูล {province} ไม่เจอเลย 😅", []
    
    items = result.get("items", [])
    if not items:
        return f"ไม่เจอสถานที่ตามหมวดหมู่ที่เลือกใน {province} ครับ 😢", []
    
    response = f"🏞️ สถานที่ใน {province}"
    if categories:
        category_text = ", ".join(categories)
        response += f" (หมวด: {category_text})"
    response += f":\n\n"
    
    displayed_items = items[:MAX_PLACES]
    
    for i, item in enumerate(displayed_items, 1):
        name = item.get("name", "ไม่ระบุชื่อ")
        rating = item.get("rating")
        item_categories = item.get("categories", [])
        map_url = item.get("map_url", "")
        weather = item.get("weather", {})
        
        rating_text = f"⭐{rating}" if rating else "⭐-"
        
        response += f"{i}. {name} {rating_text}\n"
        
        if item_categories:
            cat_emojis = [f"{CATEGORIES[cat]['emoji']} {cat}" for cat in item_categories[:2] if cat in CATEGORIES]
            if cat_emojis:
                response += f"   {' • '.join(cat_emojis)}\n"
        
        if weather and weather.get("temp_c"):
            temp = weather.get("temp_c")
            condition = weather.get("condition", "")
            response += f"   🌡️ {temp}°C {condition}\n"
        
        if map_url:
            response += f"   🗺️ {map_url}\n"
        
        response += "\n"
    
    # if len(items) > MAX_PLACES:
    #     remaining = len(items) - MAX_PLACES
    # try:
    #     ai_summary = generate_place_summary(displayed_items, "province")
    #     response += f"🤖 สรุปจาก AI:\n{ai_summary}\n\n"
    # except Exception:
    #     response += "🤖 AI กำลังวิเคราะห์ข้อมูล...\n\n"
    
    # # *** MODIFIED PART ***
    response += "📝 พิมพ์ 'รีวิว [ชื่อสถานที่]' หรือพิมพ์แค่ตัวเลข (1-5) เพื่อดูรายละเอียดเพิ่มเติมได้เลยครับ"
    return response, displayed_items

def handle_place_review(place_index_str, places_data, user_session=None):
    """จัดการการขอรีวิวสถานที่เฉพาะ (รับ index เป็น string)"""
    try:
        idx = int(place_index_str) - 1
        
        if not (0 <= idx < len(places_data)):
            return "ขอโทษครับ หมายเลขสถานที่ไม่ถูกต้อง"
        
        place = places_data[idx]
        place_name = place.get("name", "ไม่ระบุชื่อ")
        rating = place.get("rating")
        categories = place.get("categories", [])
        reviews = place.get("reviews", [])
        
        # บันทึกสถานที่ปัจจุบันลง session เพื่อใช้กับ "ไปต่อไหนดี"
        if user_session is not None:
            user_session["current_place"] = place_name
        
        ai_review = summarize_place_reviews(
            place_name=place_name,
            reviews=reviews if reviews else None,
            rating=rating,
            categories=categories
        )
        
        response = f"📝 รีวิว: {place_name}\n"
        response += f"⭐ คะแนน: {rating if rating else 'ไม่มีข้อมูล'}\n"
        if categories:
            response += f"🏷️ ประเภท: {', '.join(categories[:3])}\n"
        response += f"\n🤖 วิเคราะห์จาก AI:\n{ai_review}\n\n"
        response += "💡 ต้องการรีวิวสถานที่อื่นไหมครับ? (พิมพ์ '1', '2',.. หรือ 'รีวิว [ชื่อสถานที่]') หรือ 'เริ่ม' เพื่อค้นหาใหม่"
        
        return response
    except ValueError:
        return "ขอโทษครับ กรุณาระบุหมายเลขสถานที่ที่ถูกต้อง"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการสร้างรีวิว: {str(e)}"


def get_gemini_response(user_message: str):
    """ฟังก์ชันเรียก Gemini API"""
    prompt = PROMPT_FLOW + f"\n\nผู้ใช้: {user_message}\nผู้ช่วย:"
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text.strip()
    
@app.route("/api/gemini_chat", methods=["POST"])
def gemini_chat():
    """API endpoint สำหรับ frontend"""
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"reply": "⚠️ ไม่พบข้อความจากผู้ใช้"}), 400

        reply = get_gemini_response(user_message)
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"❌ เกิดข้อผิดพลาด: {str(e)}"}), 500
    
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text.strip()
    session = get_user_session(user_id)
    
    reply_text = ""
    quick_reply = None

    if any(greeting in user_text.lower() for greeting in ["สวัสดี", "หวัดดี", "ดี", "hello", "hi", "start", "เริ่ม"]):
        # reset session (แต่ยังเก็บ user session object เดิมไว้)
        user_sessions[user_id] = get_user_session(user_id)
        session = get_user_session(user_id)
        session["waiting_for_review"] = False
        
        reply_text = f"{random.choice(GREETINGS)}\nผมช่วยแนะนำเส้นทางและสถานที่ท่องเที่ยวได้ครับ!\n\nเลือกโหมดที่ต้องการ:"
        quick_reply = create_mode_quick_reply()
    
    # --- START: เพิ่มเงื่อนไขสำหรับ "ถาม AI:" ---
    elif user_text.lower().startswith("ถาม ai:"):
        # ดึง Prompt ของผู้ใช้ออกจากข้อความเต็ม
        prompt = user_text[len("ถาม AI:"):].strip()
        
        if not prompt:
            reply_text = "กรุณาพิมพ์คำถามหลัง 'ถาม AI:' ด้วยครับ\nเช่น: ถาม AI: ฤดูฝนเที่ยวทะเลภาคไหนดีที่สุด"
        else:
            # เรียกฟังก์ชันที่สร้างขึ้นใหม่เพื่อรับคำตอบจาก Gemini
            reply_text = ask_gemini_general(prompt)
    # --- END: เพิ่มเงื่อนไข ---

    # --- START: เพิ่ม Integration กับ PROMPT ที่คุณต้องการ ---
    elif any(keyword in user_text for keyword in ["ไปไหนดี", "ไปไหนดีไหม", "แนะนำที่ไป", "แนะนำที่เที่ยว"]):
        # ถามว่าไปไหนดี — ตอบ 1 สถานที่สั้น <=40 ตัวอักษร ตาม PROMPT_WHERE_TO_GO
        if session.get("province"):
            prompt = PROMPT_FLOW.format(province=session["province"])
            reply_text = ask_gemini_general(prompt)
        else:
            reply_text = "กรุณาพิมพ์ชื่อจังหวัดก่อนครับ เช่น: นครนายก"

    elif any(keyword in user_text for keyword in ["รีวิวสถานที่", "แนะนำสถานที่", "รีวิว สถานที่", "แนะนำ สถานที่"]):
        # ขอรีวิวหลายสถานที่ (list)
        if session.get("province"):
            prompt = PROMPT_FLOW.format(province=session["province"])
            reply_text = ask_gemini_general(prompt)
        else:
            reply_text = "กรุณาระบุจังหวัดก่อนครับ เช่น: เชียงใหม่"

    elif "ไปต่อไหนดี" in user_text:
        # แนะนำที่ควรไปต่อ โดยอ้างอิงจากสถานที่ปัจจุบันใน session
        current_place = session.get("current_place")
        if not current_place and session.get("last_search_results"):
            # fallback: เอาสถานที่แรกจากผลการค้นหา
            try:
                current_place = session["last_search_results"][0].get("name")
            except Exception:
                current_place = None

        if session.get("province") and current_place:
            prompt = PROMPT_FLOW.format(province=session["province"], place=current_place)
            reply_text = ask_gemini_general(prompt)
        else:
            reply_text = "กรุณาค้นหาจังหวัดหรือเลือกสถานที่ก่อนครับ (เช่น 'รีวิว 1' หรือค้นหาจังหวัด)"
    # --- END: Integration ---

    # *** NEW LOGIC: Handle number input for review ***
    elif user_text.isdigit() and session.get("waiting_for_review"):
        reply_text = handle_place_review(user_text, session["last_search_results"], user_session=session)
        quick_reply = create_review_quick_reply()

    elif user_text.startswith("รีวิว") and session.get("waiting_for_review"):
        place_name_to_find = user_text.replace("รีวิว", "").strip()

        if not place_name_to_find:
            reply_text = "กรุณาพิมพ์ชื่อสถานที่หลังคำว่า 'รีวิว' ด้วยครับ\nเช่น: รีวิว วัดอรุณราชวราราม"
            quick_reply = create_review_quick_reply()
        else:
            found_place_index = -1
            # ค้นหาสถานที่จากชื่อที่ผู้ใช้พิมพ์มา (แบบไม่สนตัวพิมพ์เล็ก/ใหญ่)
            for i, place in enumerate(session["last_search_results"]):
                if place_name_to_find.lower() in place.get("name", "").lower():
                    found_place_index = i
                    break
            
            if found_place_index != -1:
                # บันทึก current_place แล้วเรียกรีวิวโดยใช้ index ที่เจอ
                session["current_place"] = session["last_search_results"][found_place_index].get("name")
                reply_text = handle_place_review(str(found_place_index + 1), session["last_search_results"], user_session=session)
                quick_reply = create_review_quick_reply()
            else:
                # ถ้าไม่เจอ ก็แจ้งผู้ใช้
                reply_text = f"ขอโทษครับ ไม่พบสถานที่ชื่อ '{place_name_to_find}' ในผลการค้นหาล่าสุด\n\nกรุณาตรวจสอบชื่อและลองอีกครั้ง หรือคัดลอกชื่อจากรายการมาวางได้เลยครับ"
                quick_reply = create_review_quick_reply()

    elif user_text.startswith("โหมด"):
        mode = user_text.replace("โหมด", "").strip()
        session["waiting_for_review"] = False
        if "เส้นทางแวะ" in mode:
            session["mode"] = "route_with_stops"
            reply_text = "📍 พิมพ์จุดเริ่มต้นและจุดหมายปลายทาง\nเช่น: กรุงเทพ ไป เชียงใหม่"
        elif "สถานที่" in mode:
            session["mode"] = "province_search"
            reply_text = "🏞️ พิมพ์ชื่อจังหวัดที่ต้องการค้นหา\nเช่น: เชียงใหม่"
        else:
            reply_text = "กรุณาเลือกโหมดที่ถูกต้องครับ"
            quick_reply = create_mode_quick_reply()

    elif session.get("mode") == "route_with_stops":
        if "ไป" in user_text and not user_text.startswith("เลือก"):
            parts = user_text.split("ไป")
            if len(parts) >= 2:
                origin_raw = parts[0].strip()
                dest_raw = parts[1].strip()
                # ทำความสะอาดก่อนเก็บ
                origin_clean = clean_place_name(origin_raw)
                dest_clean = clean_place_name(dest_raw)
                session["origin"] = origin_clean
                session["destination"] = dest_clean
                session["selected_categories"] = []
                reply_text = f"📍 เส้นทาง: {session['origin']} ➜ {session['destination']}\n\nเลือกหมวดหมู่สถานที่ที่สนใจ (เลือกได้หลายอัน):"
                quick_reply = create_category_quick_reply()
            else:
                reply_text = "กรุณาพิมพ์ในรูปแบบ: จุดเริ่มต้น ไป จุดหมายปลายทาง"
        elif user_text.startswith("เลือก"):
            category = user_text.replace("เลือก", "").strip()
            if category == "ทั้งหมด":
                session["selected_categories"] = list(CATEGORIES.keys())
            elif category in CATEGORIES and category not in session["selected_categories"]:
                session["selected_categories"].append(category)
            selected_text = "ทั้งหมด" if len(session["selected_categories"]) == len(CATEGORIES) else ", ".join(session["selected_categories"])
            reply_text = f"✅ เลือกแล้ว: {selected_text}\n\nเลือกเพิ่มเติมหรือกด 'เสร็จแล้ว':"
            quick_reply = create_category_quick_reply()
        elif user_text == "เสร็จแล้ว":
            if session.get("origin") and session.get("destination"):
                categories = session["selected_categories"] or None
                text, data = handle_route_with_categories(session["origin"], session["destination"], categories)
                reply_text = text
                if data:
                    session["last_search_results"] = data
                    session["waiting_for_review"] = True
                    quick_reply = create_review_quick_reply()
            else:
                reply_text = "กรุณาระบุจุดเริ่มต้นและจุดหมายก่อนครับ"
            session["mode"] = None
            session["selected_categories"] = []

    elif session.get("mode") == "province_search":
        if validate_province_in_thailand(user_text) and not user_text.startswith("เลือก"):
            session["province"] = user_text
            session["selected_categories"] = []
            reply_text = f"🏞️ จังหวัด: {user_text}\n\nเลือกหมวดหมู่สถานที่ที่สนใจ:"
            quick_reply = create_category_quick_reply()
        elif user_text.startswith("เลือก"):
            category = user_text.replace("เลือก", "").strip()
            if category == "ทั้งหมด":
                session["selected_categories"] = list(CATEGORIES.keys())
            elif category in CATEGORIES and category not in session["selected_categories"]:
                session["selected_categories"].append(category)
            selected_text = "ทั้งหมด" if len(session["selected_categories"]) == len(CATEGORIES) else ", ".join(session["selected_categories"])
            reply_text = f"✅ เลือกแล้ว: {selected_text}\n\nเลือกเพิ่มเติมหรือกด 'เสร็จแล้ว':"
            quick_reply = create_category_quick_reply()
        elif user_text == "เสร็จแล้ว":
            if session.get("province"):
                categories = session["selected_categories"] or None
                text, data = handle_province_with_categories(session["province"], categories)
                reply_text = text
                if data:
                    session["last_search_results"] = data
                    session["waiting_for_review"] = True
                    quick_reply = create_review_quick_reply()
            else:
                reply_text = "กรุณาระบุจังหวัดก่อนครับ"
            session["mode"] = None
            session["selected_categories"] = []
        else:
            reply_text = "กรุณาพิมพ์ชื่อจังหวัดที่ถูกต้องในประเทศไทยครับ"
    
    # --- START: อัปเดตข้อความช่วยเหลือ ---
    elif any(help_word in user_text.lower() for help_word in ["ช่วย", "help", "วิธี", "ยังไง"]):
        reply_text = (
            "🤖 **วิธีใช้งาน:**\n\n"
            "1️⃣ **เริ่มต้น:** พิมพ์ 'สวัสดี' เพื่อเริ่ม\n"
            "2️⃣ **เลือกโหมด:** เส้นทาง หรือ สถานที่\n"
            "3️⃣ **ใส่ข้อมูล:** เช่น 'กรุงเทพ ไป เชียงใหม่' หรือ 'นครนายก'\n"
            "4️⃣ **เลือกหมวดหมู่:** เลือกสถานที่ที่สนใจ\n"
            "5️⃣ **ดูรีวิว:** พิมพ์ 'รีวิว 1' หรือ 'รีวิว [ชื่อสถานที่]'\n\n"
            "✨ **ใหม่!** ถามคำถามทั่วไปกับ AI ได้เลย!\n"
            "ตัวอย่าง: `ถาม AI: ฤดูฝนเที่ยวทะเลภาคไหนดีที่สุด`"
        )
    # --- END: อัปเดตข้อความช่วยเหลือ ---
    
    else:
        if session.get("waiting_for_review"):
            reply_text = "📝 คุณสามารถขอรีวิวสถานที่ได้ครับ!\n\nพิมพ์ตัวเลข (1-5) หรือ 'รีวิว [ชื่อสถานที่]' ที่ต้องการ\nหรือพิมพ์ 'เริ่ม' เพื่อค้นหาใหม่"
            quick_reply = create_review_quick_reply()
        else:
            reply_text = "ผมไม่เข้าใจครับ 🤔\n\nพิมพ์ 'เริ่ม' เพื่อเลือกโหมดการใช้งาน\nหรือ 'ช่วย' เพื่อดูวิธีใช้งาน\n\n😊 ยินดีช่วยเหลือครับ!"

    if not reply_text:
        return

    if len(reply_text) > 4800:
        reply_text = reply_text[:4750] + "\n\n... (ข้อความยาวเกินไป ถูกตัดทอน)"

    reply_message = TextMessage(text=reply_text)
    if quick_reply:
        reply_message.quick_reply = quick_reply

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[reply_message]
        )
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)