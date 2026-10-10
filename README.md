# THAI MACD SCANNER — SET + mai

เว็บภาษาไทยใช้งานบน iPhone ฟรี พร้อมตัวสแกน MACD รายวัน (12,26,9) และ Export CSV

## เปิดเว็บฟรีด้วย GitHub Pages

1. สร้าง repository ใหม่บน GitHub เช่น `thai-macd-scanner` และตั้งเป็น **Public** (GitHub Pages ฟรีสำหรับ public repo)
2. อัปโหลดไฟล์ทั้งหมด **รวมโฟลเดอร์ `.github/workflows/`** ไปที่ root ของ repository สาขา `main` (แนะนำอัปโหลดผ่านคอมพิวเตอร์หรือแอป GitHub)
3. ไปที่ `Settings → Pages → Build and deployment → Source` เลือก **GitHub Actions**
4. ไปที่ `Actions → Scan MACD and deploy → Run workflow` รอจนงานสำเร็จ (หุ้นหลายร้อยตัวอาจใช้เวลาหลายนาที)
5. เปิด `https://YOUR-USERNAME.github.io/thai-macd-scanner/` (เปลี่ยนเป็นชื่อบัญชีและ repo ของคุณ)
6. ระบบตั้งให้สแกนอัตโนมัติ จันทร์–ศุกร์ เวลา 19:15 น. ประเทศไทย (GitHub scheduled workflows อาจล่าช้าหรือถูกระงับเมื่อ repo ไม่มี activity นาน)

**สำคัญ:** `data/latest.json` ที่ให้มาเป็นไฟล์ว่างอย่างตั้งใจ ไม่มีผลหุ้นปลอม เมื่อ Actions ทำงานจะสร้างข้อมูลจริงแล้ว deploy ขึ้นเว็บใหม่ทุกครั้ง

## แหล่งข้อมูลและข้อจำกัด

- รายชื่อหุ้น: TradingView public Thailand scanner (unofficial endpoint) พร้อม `universe.csv` สำหรับเพิ่ม/แก้ตลาดด้วยตนเอง
- ราคาปิดรายวัน: Yahoo Finance chart API (`SYMBOL.BK`, unofficial endpoint)
- ฟรี ไม่ต้องมี TradingView แบบจ่ายเงินหรือ API key แต่ API อาจบล็อก, rate-limit, เปลี่ยน schema หรือให้ข้อมูลไม่ครบ
- **ไม่รับประกันครอบคลุม SET + mai ทั้งหมด**: ถ้า discovery ใช้งานไม่ได้ โปรแกรมจะ fallback ไปที่ `universe.csv` ซึ่งมีเพียงตัวอย่าง 11 ตัวและแสดงคำเตือน; เพิ่มรายชื่อหุ้นทั้งหมดลง CSV ได้เพื่อเพิ่มความครอบคลุม
- การจัดประเภท mai จาก TradingView อาจไม่ครบถ้าผู้ให้บริการใช้ชื่อ exchange เป็น SET เหมือนกัน; ใช้ `universe.csv` override ได้
- หุ้นที่ราคาย้อนหลังไม่พอ 80 วันหรือวันที่ราคาปิดเก่ากว่ารอบล่าสุดจะถูกระบุว่าไม่ผ่านการตรวจสอบ ไม่ปนกับหุ้น MACD > 0
- Yahoo Finance มีโอกาสปรับปรุงราคาย้อนหลัง; MACD จากราคาปิดอาจต่างจาก TradingView เล็กน้อย
- สัญญาณ 'เพิ่งตัดขึ้น 0' = MACD วันก่อน <= 0 และวันล่าสุด > 0; 'เหนือ 0' = MACD > 0 ไม่เกี่ยวกับการตัด Signal
- **ไม่มีข้อมูลราคาตลาดสด (real-time)** และไม่ใช่คำแนะนำซื้อขาย

## รันเองบนเครื่อง

```bash
pip install -r requirements.txt
python scan.py
python -m http.server 8000
```

เปิด `http://localhost:8000` และดู `data/latest.json` สำหรับผลตรวจสอบ/ข้อผิดพลาดรายตัว

## ถ้าอยาก deploy ไป Cloudflare Pages

สร้าง Pages project เชื่อม GitHub repo นี้ แล้วเลือก Build command ว่าง, Output directory `.` แต่ **ต้องเปิด GitHub Actions เพื่อสร้างและเผยแพร่ข้อมูล**; GitHub Pages workflow นี้ deploy ไป GitHub Pages เท่านั้นและไม่ได้ commit ผลสแกนกลับ repository จึงไม่อัปเดต Cloudflare Pages โดยอัตโนมัติ หากต้องการ Cloudflare โดยตรงให้เพิ่มขั้นตอน `wrangler pages deploy` และ API token เป็น secret ของ GitHub แทน
