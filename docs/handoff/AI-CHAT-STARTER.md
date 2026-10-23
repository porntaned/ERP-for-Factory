# ข้อความเริ่มแชตสำหรับ AI ตัวอื่น

คัดลอกข้อความในกรอบด้านล่างไปวางในแชตใหม่ แล้วส่งคำสั่งงานเพิ่มเติมแยกต่างหาก
ใช้ได้ทั้ง AI ที่เข้าถึง repository ได้และ AI ที่ช่วยวิเคราะห์จากไฟล์ แต่ต้องบอกข้อจำกัดตามจริง

```text
คุณกำลังรับงานต่อใน repository porntaned/ERP-for-Factory: ERP โรงงานประกอบ LED
แบบ Django modular monolith + PostgreSQL ใช้ข้อมูลจำลอง เป็น public portfolio
ตอบภาษาไทย กระชับ ทำเฉพาะงานที่ฉันสั่ง ไม่อ้างว่าเป็น Agent เดิมหรือมีความทรงจำจากแชตเก่า

เริ่มจากตรวจ Git repository/remote, branch, HEAD และ working tree จริง
อ่าน AGENTS.md, docs/TASKS.md, docs/MULTI_AGENT.md, docs/SCRUTINIZE.md,
docs/DEVELOPMENT.md และ docs/handoff/PROJECT-STATUS-2026-10-23.md ครั้งแรก
จากนั้นอ่านซ้ำเฉพาะจุดที่เปลี่ยนหรือมีข้อสงสัย ตรวจ GitHub ผ่าน browser ที่ฉันเตรียมไว้
ตรวจ PR/Issue/main/CI ปัจจุบันก่อนทำงาน ห้ามเชื่อ snapshot นี้อย่างเดียว

Snapshot ที่ต้องตรวจใหม่: main 3d876cc129f9f889b636926b40798423a53d31f1
PR #39 Merge แล้ว; Issue #38 completed; main CI #126 ผ่าน:
https://github.com/porntaned/ERP-for-Factory/pull/39
https://github.com/porntaned/ERP-for-Factory/issues/38
https://github.com/porntaned/ERP-for-Factory/actions/runs/39983366988
application/test SHA fb3de5ea7a60b41a38036b92d2e0c4c3980090c5
ผ่าน PostgreSQL 18.6: 29 targeted history / 620 full tests ใน CI #123

M4.1, M4.2 และ M4.3.1–M4.3.5 เสร็จ โดย M4.3.2 สิทธิ์ขั้นต่ำรวมใน PR #37
M4.3.6 ยังไม่เริ่ม และ M4.3.7 independent review ทั้งเส้นทางยังไม่เสร็จ
M4.3 และ M4 ทั้งหมดยังไม่เสร็จ ไม่มี Deploy และฉันยังไม่ให้เริ่ม UI
อย่าทำส่วนที่ Merge แล้วซ้ำ อย่าถือ tests บางส่วนที่ผ่านเป็นหลักฐานว่า feature ถัดไปเสร็จ

กติกาที่ฉันเลือกแล้ว:
- ผู้โอนเป็น persisted active user มี WAREHOUSE ทั้งต้นทางและปลายทาง ไม่มี superuser bypass
- ต้นทาง RELEASED; ปลายทาง HOLD/default HOLD หรือ RELEASED ได้และคงสถานะเดิม
- หนึ่ง saved Lot คลังต่างกันใน persisted Plant เดียวกัน/Organization ตรงกัน
- exact positive finite base-UOM Decimal <10^14 แทนค่าได้ 6 ตำแหน่ง ไม่ปัดเศษ
  reason ไม่ว่าง เก็บ Unicode/ช่องว่างเดิม
- Quality/สิทธิ์/ledger สองฝั่ง/StockTransfer อยู่ใน transaction เดียวกัน

โค้ดหลัก: inventory/transfers.py, transfer_policy.py, models.py,
inventory/migrations/0005_stock_transfer.py และ tests/inventory/test_transfer_history.py
transfer_stock คืน (debit, credit); debit.transfer_out / credit.transfer_in คือ StockTransfer เดียวกัน
ยังไม่มี request UUID/idempotency เรียกซ้ำคือโอนใหม่ ห้าม retry อัตโนมัติหรือเปิด endpoint ก่อนทำส่วนนี้
ข้อมูล ledger เก่าไม่ถูกเดาจับคู่ย้อนหลัง

ทำงานบน feature branch codex/... เท่านั้น ห้าม force-push, Merge หรือ Deploy เอง
คำอนุมัติ Merge PR #39 ไม่ใช่คำอนุมัติ PR ใหม่ ห้ามใช้ secret/ข้อมูลจริงหรือเพิ่ม dependency นอกขอบเขต
อ่านข้อมูลอิสระพร้อมกัน รวมหลักฐานเป็นช่วง ทดสอบเฉพาะจุดก่อนแล้ว regression ที่เกี่ยวข้อง
รอผลทดสอบ → แก้ไข → ตรวจอิสระ; แยก self-review กับ independent review ตามผู้ทำจริง
สร้าง/ใช้ Agent เฉพาะเมื่อฉันหรือคำสั่งที่มีผลอนุญาต อย่าอ้างว่ามี independent Agent หากไม่ได้ใช้จริง
PostgreSQL claims ต้องตรวจ PostgreSQL พร้อม SHA/คำสั่ง/ผลจริง เครื่องเดิมไม่มี .env
ห้ามนำ SQLite/mocks มาแทนหลักฐาน PostgreSQL หรือพิมพ์ secrets ออกมา

ไฟล์ส่งต่อจัดทำใน branch codex/docs/project-ai-handoff / Issue #40
https://github.com/porntaned/ERP-for-Factory/issues/40
ตรวจว่าเอกสารส่งต่อเข้า main หรือยัง; หากยังให้ดู branch นี้ ไม่สร้างไฟล์ซ้ำเพราะหาใน main ไม่พบ

หากคุณไม่มี Git/browser/terminal ให้บอกตรง ๆ ว่าตรวจอะไรไม่ได้
อย่าอ้างผล tests/CI/การบันทึกไฟล์ที่ไม่ได้ทำ ให้ช่วยวิเคราะห์เฉพาะหลักฐานที่ฉันให้

คำสั่งแรกของแชตนี้: ตรวจและสรุปสถานะล่าสุดกับงานค้างแบบกระชับเท่านั้น
ยังไม่เริ่ม M4.3.6, ไม่สร้าง feature ใหม่ และไม่ Merge/Deploy จนกว่าฉันจะสั่งเพิ่มเติม
```

ถ้าจะทำ M4.3.6 จริง ให้เจ้าของส่งคำสั่งใหม่ชัดเจน เช่น:
“เริ่ม M4.3.6 โดยเสนอขอบเขตและกติกา retry/legacy request ID ให้ตรวจ ก่อนลงมือส่วนที่ต้องเลือกนโยบาย”
ข้อความตัวอย่างนี้ไม่ใช่คำสั่งให้เริ่มโดยอัตโนมัติ
