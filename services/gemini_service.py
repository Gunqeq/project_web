import os
import google.generativeai as genai

# โหลด API Key จาก ENV
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY is not configured")

genai.configure(api_key=GEMINI_API_KEY)

# Configuration สำหรับ Gemini
def get_gemini_model():
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 800,
    }
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        safety_settings=safety_settings
    )

def summarize_place_reviews(place_name, reviews, rating=None, categories=None):
    """สรุปรีวิวสถานที่โดย Gemini AI"""
    model = get_gemini_model()
    
    # ถ้ามีรีวิวจริง
    if reviews and len(reviews) > 0:
        reviews_text = "\n".join(reviews[:5])  # ใช้แค่ 5 รีวิวแรก
        prompt = f"""
        วิเคราะห์รีวิวของสถานที่ "{place_name}" ในประเทศไทย

        รีวิวจากผู้ใช้:
        {reviews_text}

        กรุณาสรุปเป็น:
        ✅ ข้อดี (2-3 ข้อ)
        ❌ ข้อเสีย (1-2 ข้อ)  
        💡 คำแนะนำสำหรับนักท่องเที่ยว

        ใช้ภาษาไทยที่เป็นกันเอง ความยาวไม่เกิน 200 คำ
        """
    else:
        # ถ้าไม่มีรีวิว → ให้ Gemini generate จาก rating + category
        cat_text = ", ".join(categories) if categories else "สถานที่ทั่วไป"
        rating_text = f"เรตติ้ง {rating}/5.0 ดาว" if rating else "ไม่มีเรตติ้ง"

        prompt = f"""
        สถานที่ "{place_name}" ในประเทศไทย
        ประเภท: {cat_text}
        คะแนน: {rating_text}

        ยังไม่มีรีวิวจากผู้ใช้ กรุณาคาดการณ์:
        ✅ ข้อดีที่น่าจะพบ (2-3 ข้อ)
        ❌ ข้อเสียที่ควรระวัง (1-2 ข้อ)
        💡 คำแนะนำสำหรับนักท่องเที่ยว

        อ้างอิงจากประเภทสถานที่และคะแนน ใช้ภาษาไทยเป็นกันเอง ไม่เกิน 200 คำ
        """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"⚠️ เกิดข้อผิดพลาดในการวิเคราะห์รีวิว: {str(e)[:50]}..."

def answer_travel_question(question, context=""):
    """ตอบคำถามเรื่องการท่องเที่ยวด้วย Gemini AI"""
    model = get_gemini_model()
    
    system_prompt = """คุณเป็นผู้ช่วยท่องเที่ยวประเทศไทยที่เป็นมิตรและมีความรู้ดี
    ตอบคำถามด้วยภาษาไทยที่เป็นกันเองและใช้อีโมจิประกอบให้เหมาะสม
    หากเป็นคำถามเรื่องสถานที่ท่องเที่ยว อาหาร วัฒนธรรม หรือการเดินทางในไทย ให้ตอบอย่างละเอียด
    หากเป็นคำถามนอกเรื่อง ให้สั้นๆ และหันเหความสนใจมาที่การท่องเที่ยว
    ความยาวไม่เกิน 300 คำ"""
    
    full_prompt = f"{system_prompt}\n\n{context}\n\nคำถาม: {question}"
    
    try:
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "ขอโทษครับ เกิดข้อผิดพลาดในการตอบคำถาม กรุณาลองใหม่อีกครั้งนะครับ 😅"

def generate_place_summary(places_data, search_type="route"):
    """สร้างสรุปสถานที่ด้วย AI"""
    model = get_gemini_model()
    
    places_info = []
    for place in places_data[:3]:  # ใช้แค่ 3 สถานที่แรก
        name = place.get('name', '')
        categories = place.get('categories', [])
        rating = place.get('rating', '')
        places_info.append(f"- {name} ({', '.join(categories[:2])}) {rating}⭐")
    
    places_text = "\n".join(places_info)
    
    if search_type == "route":
        prompt = f"""
        นี่คือสถานที่แนะนำในเส้นทาง:
        {places_text}

        ช่วยเขียนข้อความกระตุ้นให้นักท่องเที่ยวสนใจไปเที่ยว (1-2 ประโยค)
        และเสนอให้ขอรีวิวเพิ่มเติม ใช้ภาษาไทยเป็นกันเอง
        """
    else:
        prompt = f"""
        นี่คือสถานที่น่าสนใจในจังหวัด:
        {places_text}

        ช่วยเขียนข้อความกระตุ้นความสนใจ (1-2 ประโยค)
        และแนะนำให้ขอรีวิวเพิ่มเติม ใช้ภาษาไทยเป็นกันเอง
        """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "💡 อยากทราบรายละเอียดเพิ่มเติมของสถานที่ไหนมั้ยครับ? ถามมาได้เลย! 😊"