# Wellnis Review — ระบบติดตามรีวิว Google Maps 9 สาขา

ระบบอัตโนมัติที่ดึงรีวิว Google Maps ของทุกสาขาทุกวัน, แจ้งเตือนทาง Telegram ทุกวัน 21:00 น.
(รีวิวใหม่วันนี้ทุกข้อความเต็ม + แจ้งด่วนถ้ามีรีวิว ≤ 3 ดาว), พร้อมหน้าเว็บแดชบอร์ดให้ทีมกดดูได้ทุกที่

> หมายเหตุ: ลิงก์ที่ให้มามี **9 สาขา** (บางปู, สะพานควาย, บางใหญ่, รังสิต, พัทยา, เชียงใหม่, พระราม 9, บางนา, ปิ่นเกล้า)
> ระบบนี้รองรับครบทั้ง 9 สาขาตามลิงก์ — ถ้าจริงๆ มีแค่ 8 สาขา ให้ลบรายการที่ไม่ต้องการออกจาก `branches.json`

## ระบบทำอะไรให้บ้าง

- 🔄 ดึงคะแนน + รีวิวล่าสุดของทุกสาขาจาก Google Places API ทุกวัน (เป็นภาษาไทยตามที่รีวิวเขียนไว้จริง)
- 📝 นับ "รีวิวใหม่วันนี้" ต่อสาขา โดยเช็คจาก**วันที่รีวิวถูกโพสต์จริง** (ไม่ใช่แค่ครั้งแรกที่ระบบเห็น) —
  ถ้ามีรีวิวใหม่วันนี้ จะแสดงข้อความเต็มของทุกรีวิววันนั้น ถ้าไม่มี จะบอกว่ารีวิวล่าสุดคือเมื่อไหร่ (ไว้ตามน้องๆ ที่สาขา)
- ⚠️ ทำเครื่องหมายรีวิวที่ได้ ≤ 3 ดาว (เฉพาะที่โพสต์วันนี้) ให้เห็นชัดว่าต้องติดตามด่วน
- 📲 ส่งสรุปเข้า Telegram ทุกวัน 21:00 น. (เวลาไทย) ผ่าน GitHub Actions
- 🌐 หน้าเว็บแดชบอร์ด (`docs/index.html`) ให้ทีมกดดูรายละเอียดแต่ละสาขาได้ทุกเมื่อ ผ่าน GitHub Pages

## ข้อจำกัดที่ควรรู้ (สำคัญ)

Google **ไม่มี API ทางการที่ดึงรีวิวได้ครบทุกรีวิว** — Places API (New) ให้ดึงได้แค่ **5 รายการต่อการเรียก 1 ครั้ง**
(ไม่มีการแบ่งหน้า/pagination) และ **Google เลือก 5 รายการนั้นตาม "ความเกี่ยวข้อง" (relevance) ของ Google เอง
ไม่ใช่ "5 รีวิวล่าสุด" เป๊ะๆ** — ไม่มีพารามิเตอร์ทางการให้สั่งเรียงตามวันที่ใหม่สุดได้ (ทดลองส่ง `reviewsSort` แล้ว
Google ตอบกลับว่าไม่มีฟิลด์นี้) ปกติ relevance กับความใหม่จะใกล้เคียงกัน แต่**อาจมีบางครั้งที่รีวิวใหม่จริงๆ
ไม่ติดโผ 5 อันดับนี้** ทำให้ระบบไม่เห็นรีวิวนั้นจนกว่าจะ "เกี่ยวข้อง" พอในสายตา Google — ถ้าต้องการความแม่นยำ
100% แบบเรียงตามวันที่ใหม่สุดจริง จะต้องใช้บริการบุคคลที่สาม (มีค่าใช้จ่าย) แทน

ระบบนี้นับ "รีวิวใหม่วันนี้" โดยเทียบ**วันที่โพสต์จริงของแต่ละรีวิว**กับวันที่ปัจจุบัน (เขตเวลา Asia/Bangkok)
ไม่ใช่การจำว่าเคยเห็นรีวิวนั้นมาก่อนหรือยัง — ตัวเลขจะแม่นยำตราบใดที่รีวิวใหม่ของวันนั้นติดอยู่ใน 5 อันดับที่ Google ส่งมาให้

## โครงสร้างโปรเจกต์

```
branches.json                 รายชื่อ 9 สาขา + place_id ของแต่ละสาขา
src/wellnis_review/           โค้ดหลัก (ดึงรีวิว, ส่ง Telegram, สร้างข้อมูลแดชบอร์ด)
scripts/resolve_place_ids.py  สคริปต์รันครั้งเดียว: แปลงลิงก์ Google Maps -> place_id
data/state.json               ฐานข้อมูลรีวิวสะสม (คอมมิตกลับเข้า repo ทุกวันโดย Action)
docs/                          หน้าเว็บแดชบอร์ด (GitHub Pages เสิร์ฟจากโฟลเดอร์นี้)
.github/workflows/            งานอัตโนมัติบน GitHub Actions
```

## ขั้นตอนติดตั้ง (ทำครั้งเดียว)

### 1) สร้าง Telegram Bot

1. เปิดแชทกับ [@BotFather](https://t.me/BotFather) ใน Telegram
2. พิมพ์ `/newbot` ตั้งชื่อบอท จะได้ **Bot Token** (รูปแบบ `123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
3. หา **Chat ID** ที่จะให้บอทส่งข้อความไปหา:
   - ถ้าจะส่งเข้า **กลุ่ม**: เพิ่มบอทเข้ากลุ่ม, ส่งข้อความอะไรก็ได้ในกลุ่ม, แล้วเปิด
     `https://api.telegram.org/bot<TOKEN>/getUpdates` ในเบราว์เซอร์ — จะเห็น `"chat":{"id": -100xxxxxxxxxx, ...}`
   - ถ้าจะส่งหา **ตัวเอง/แชทเดี่ยว**: ส่งข้อความหาบอทก่อน 1 ครั้ง แล้วเปิดลิงก์เดียวกันด้านบน จะเห็น `"chat":{"id": xxxxxxxx}`
   - หรือใช้บอทช่วยเช่น [@userinfobot](https://t.me/userinfobot) เพื่อดู chat id ของตัวเอง/กลุ่มได้ง่ายขึ้น

### 2) เปิดใช้งาน Google Places API

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/) สร้างโปรเจกต์ (หรือใช้โปรเจกต์เดิม)
2. เปิดใช้ **Places API (New)** ที่เมนู APIs & Services → Library
3. ผูก Billing account (Google ให้เครดิตใช้ฟรีรายเดือน — เพียงพอสำหรับ 9 สาขา ดึงวันละครั้ง)
4. สร้าง API Key ที่ Credentials → Create Credentials → API Key
   - แนะนำจำกัดสิทธิ์ Key ให้ใช้ได้เฉพาะ Places API (New) เพื่อความปลอดภัย

### 3) ตั้งค่า GitHub Secrets

ไปที่ repo → **Settings → Secrets and variables → Actions → New repository secret** เพิ่ม 3 ตัวนี้:

| Secret name | ค่า |
|---|---|
| `GOOGLE_MAPS_API_KEY` | API key จากขั้นตอนที่ 2 |
| `TELEGRAM_BOT_TOKEN` | Bot token จากขั้นตอนที่ 1 |
| `TELEGRAM_CHAT_ID` | Chat id จากขั้นตอนที่ 1 |

### 4) ผูก place_id ให้แต่ละสาขา (รันครั้งเดียว)

ไปที่ repo → tab **Actions** → เลือก workflow **"Resolve place IDs (one-time setup)"** → **Run workflow**

รอสักครู่ ระบบจะ:
1. ตามลิงก์ Google Maps ของแต่ละสาขา
2. ค้นหาใน Places API เพื่อหา `place_id` ที่ตรงกัน
3. commit ค่า `place_id` กลับเข้า `branches.json` ให้อัตโนมัติ

**⚠️ สำคัญ:** หลังรันเสร็จ เปิดไฟล์ `branches.json` (หรือดู Job Summary ของ workflow) ตรวจสอบว่าที่อยู่/ชื่อที่จับคู่ได้
ตรงกับแต่ละสาขาจริง ก่อนปล่อยให้ระบบรันอัตโนมัติทุกวัน — ถ้าสาขาไหนจับคู่ผิดหรือหาไม่เจอ ให้แก้ `place_id`
ในไฟล์ด้วยมือ (หา place_id ได้จาก [Place ID Finder](https://developers.google.com/maps/documentation/places/web-service/place-id))

### 5) เปิดใช้งาน GitHub Pages (สำหรับลิงก์แดชบอร์ด)

ไปที่ repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main` (หรือชื่อ default branch)
โฟลเดอร์: **/docs** → Save

หลังจากนั้นไม่กี่นาที จะได้ลิงก์แดชบอร์ดรูปแบบ:
`https://<github-username-หรือ-org>.github.io/<ชื่อ-repo>/`

ลิงก์นี้ **ทีมกดเข้าดูได้ทุกที่ทุกเวลา** ไม่ต้องล็อกอิน และจะอัปเดตข้อมูลอัตโนมัติทุกวันหลัง workflow รันเสร็จ

### 6) ทดสอบรันจริง

ไปที่ tab **Actions** → เลือก workflow **"Daily review sync"** → **Run workflow** เพื่อทดสอบทันที
(ไม่ต้องรอถึง 21:00 น.) ตรวจสอบว่า:
- ข้อความเข้า Telegram ครบทุกสาขา
- `docs/data.json` และ `data/state.json` ถูกคอมมิตกลับเข้า repo
- แดชบอร์ดที่ GitHub Pages แสดงข้อมูลถูกต้อง

หลังจากนั้นระบบจะรันอัตโนมัติทุกวัน **21:00 น. เวลาไทย** ผ่าน cron ใน `.github/workflows/daily-review-sync.yml`

## การดูแลรักษา

- **เพิ่ม/ลบ/แก้สาขา**: แก้ `branches.json` แล้ว push จากนั้นรัน workflow "Resolve place IDs" ใหม่ถ้าเพิ่มสาขาใหม่
- **ปรับเกณฑ์ดาวที่แจ้งเตือน**: แก้ `LOW_RATING_THRESHOLD` ใน `src/wellnis_review/config.py` (ปัจจุบัน = 3)
- **ปรับเวลาแจ้งเตือน**: แก้ cron ใน `.github/workflows/daily-review-sync.yml`
  (`cron: "0 14 * * *"` คือ 14:00 UTC = 21:00 ไทย — ถ้าจะเปลี่ยนเวลาต้องคำนวณเป็น UTC เอง)
- **รันทดสอบในเครื่องตัวเอง**: `cp .env.example .env` แล้วกรอกค่า, `pip install -r requirements.txt`,
  `export $(cat .env | xargs) && PYTHONPATH=src python -m wellnis_review.run_daily`

## ค่าใช้จ่ายโดยประมาณ

- **Google Places API**: เรียก Place Details วันละ 1 ครั้ง/สาขา (9 สาขา = 9 ครั้ง/วัน ≈ 270 ครั้ง/เดือน)
  อยู่ในเครดิตฟรีรายเดือนของ Google Cloud ในเกือบทุกกรณี — ตรวจสอบราคาปัจจุบันได้ที่
  [Places API Pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- **Telegram Bot API**: ฟรี
- **GitHub Actions + Pages**: ฟรีสำหรับ repo ปกติ (มี free minutes ต่อเดือน)
