"""AI summary of "ลูกค้าชื่นชมอะไรบ่อยๆ" per branch, via the Claude API.

Runs once per branch per day over the locally-accumulated review corpus
(state_store keeps up to MAX_REVIEWS_KEPT_PER_BRANCH reviews per branch).
"""
from __future__ import annotations

import json

import anthropic

MODEL = "claude-opus-5"

SYSTEM_PROMPT = (
    "คุณคือผู้ช่วยวิเคราะห์รีวิวลูกค้าให้กับคลินิกความงาม/เวลนิส "
    "อ่านรีวิว Google Maps ของสาขาหนึ่ง แล้วสรุปเป็นภาษาไทยว่าลูกค้าชื่นชมเรื่องอะไรบ่อยที่สุด "
    "(เช่น พนักงานคนไหน, บริการจุดไหน, ความสะอาด, ราคา, ผลลัพธ์) "
    "และถ้ามีคำติที่เกิดซ้ำก็ให้สรุปแยกไว้สั้นๆ ด้วย "
    "ตอบเป็น bullet สั้นกระชับ ไม่เกิน 5 bullet ต่อหัวข้อ ไม่ต้องทักทายหรือใส่คำนำ"
)


def summarize_branch_reviews(
    api_key: str, branch_name: str, reviews: list[dict], max_reviews: int = 120
) -> str:
    """Return a short Thai-language markdown summary, or a fallback string
    when there isn't enough review text to summarize yet."""
    texted = [r for r in reviews if (r.get("text") or "").strip()][:max_reviews]
    if not texted:
        return "_ยังไม่มีข้อความรีวิวเพียงพอให้สรุป (Google Places API ให้ดึงได้แค่รีวิวล่าสุดสูงสุด 5 รายการต่อครั้ง ระบบจะสะสมเพิ่มขึ้นทุกวัน)_"

    payload = [
        {"rating": r.get("rating"), "text": r.get("text"), "author": r.get("author")}
        for r in texted
    ]

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"รีวิวสะสมของ {branch_name} จำนวน {len(payload)} รายการ (ใหม่สุดก่อน) "
                    f"อยู่ใน JSON ด้านล่าง:\n\n{json.dumps(payload, ensure_ascii=False)}\n\n"
                    "โปรดสรุปตามหัวข้อ:\n"
                    "**ชื่นชมบ่อย:**\n- ...\n\n**คำติที่เจอซ้ำ (ถ้ามี):**\n- ..."
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return "_สรุปไม่สำเร็จ (ไม่มีข้อความตอบกลับ)_"
