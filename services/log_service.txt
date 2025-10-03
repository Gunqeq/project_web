from datetime import datetime, timezone
from utils.firebase_client import get_db

def log_user_event(user_id: str, message: str, mode: str | None,
                   intent: str | None = None, meta: dict | None = None):
    """
    บันทึก 1 event ลง Firestore
    โครงสร้างคอลเลกชัน: user_logs/{auto_doc_id}
    """
    db = get_db()
    data = {
        "user_id": user_id,
        "message": message,
        "mode": mode,             # เช่น route_only / route_with_stops / province_search / None
        "intent": intent,         # เช่น greeting / select_category / help / free_talk
        "meta": meta or {},       # payload เพิ่มเติม เช่น {origin, destination, categories}
        "timestamp": datetime.now(timezone.utc),
        # เพิ่มฟิลด์นี้ถ้าจะใช้ TTL auto-delete
        "ttl_at": datetime.now(timezone.utc), 
    }
    db.collection("user_logs").add(data)