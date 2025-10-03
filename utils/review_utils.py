def summarize_reviews(reviews, max_reviews=5):
    """สรุปข้อดี/ข้อเสียจากรีวิวของผู้ใช้"""
    if not reviews:
        return {
            "pros": ["ยังไม่มีรีวิวจากผู้ใช้"],
            "cons": []
        }

    pros, cons = [], []
    for r in reviews[:max_reviews]:
        text = r.get("text", "")
        rating = r.get("rating", 0)

        if rating >= 4:
            pros.append(text.strip())
        elif rating <= 2:
            cons.append(text.strip())
        else:
            # คะแนนกลางๆ อาจใส่ได้ทั้ง 2 ฝั่ง
            if "ดี" in text or "สวย" in text or "ชอบ" in text:
                pros.append(text.strip())
            else:
                cons.append(text.strip())

    if not pros:
        pros = ["- ไม่มีข้อมูลรีวิวเชิงบวกชัดเจน"]
    if not cons:
        cons = ["- ไม่มีข้อมูลรีวิวเชิงลบชัดเจน"]

    return {"pros": pros, "cons": cons}
