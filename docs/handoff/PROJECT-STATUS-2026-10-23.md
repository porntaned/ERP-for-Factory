# สถานะโครงการและงานส่งต่อ — 23 ตุลาคม 2026

Repository: **porntaned/ERP-for-Factory** · ข้อมูลโรงงานจำลองเท่านั้น  
[Issue เอกสาร #40](https://github.com/porntaned/ERP-for-Factory/issues/40)  
เอกสารนี้เป็น snapshot ไม่ใช่สถานะสด ต้องตรวจ Git/GitHub/CI ใหม่ก่อนทำงาน

## จุดหยุดที่ตรวจจริง

- `origin/main`: **3d876cc129f9f889b636926b40798423a53d31f1** หลังเจ้าของอนุมัติ
  [PR #39](https://github.com/porntaned/ERP-for-Factory/pull/39) และตรวจผ่าน browser ว่า Merged
- [Issue #38](https://github.com/porntaned/ERP-for-Factory/issues/38) ปิด completed
- [main CI #126](https://github.com/porntaned/ERP-for-Factory/actions/runs/39983366988)
  ผ่านหลัง Merge (1m 21s)
- ผล application/test SHA `fb3de5ea7a60b41a38036b92d2e0c4c3980090c5`:
  [CI #123](https://github.com/porntaned/ERP-for-Factory/actions/runs/39981798189)
  PostgreSQL 18.6: **29 history tests / 620 full tests ผ่าน**
- SHA สุดท้ายของ PR #39: `5c1835fd389577841cb0585687ca057473834ab3`
  เป็นเอกสารหลังผลทดสอบ; push/PR CI ผ่านก่อน Merge
- ยังไม่มี Deploy และเจ้าของยังไม่ต้องการเริ่มหน้าจอ UI
- ก่อนงานเอกสารนี้ local สะอาดที่ branch `codex/inventory/transfer-history`, HEAD `5c1835f`
  งานส่งต่อนี้แยกเป็น `codex/docs/project-ai-handoff` จาก main ข้างต้น
  การส่งต่อไฟล์นี้ไม่ได้อนุมัติ Merge PR เอกสารหรือเริ่ม feature ถัดไป

## งาน M4 ที่เสร็จและยังค้าง

| งาน | สถานะ/หลักฐาน |
| --- | --- |
| M4.1 immutable ledger / nonnegative | เสร็จ: [PR #27](https://github.com/porntaned/ERP-for-Factory/pull/27) |
| M4.2 รับเข้าวัตถุดิบจำลอง | เสร็จ: [PR #30](https://github.com/porntaned/ERP-for-Factory/pull/30) |
| M4.3.1 นิยาม input การโอน | เสร็จ: [PR #33](https://github.com/porntaned/ERP-for-Factory/pull/33) |
| M4.3.2 สิทธิ์สองคลัง | กติกาและการตรวจขั้นต่ำเสร็จรวมใน [PR #37](https://github.com/porntaned/ERP-for-Factory/pull/37) |
| M4.3.3 Quality eligibility | เสร็จ: [PR #35](https://github.com/porntaned/ERP-for-Factory/pull/35) |
| M4.3.4 หัก–เพิ่ม atomic / ป้องกันติดลบ | เสร็จ: [PR #37](https://github.com/porntaned/ERP-for-Factory/pull/37) |
| M4.3.5 ประวัติเชื่อม ledger สองฝั่ง | เสร็จ: [PR #39](https://github.com/porntaned/ERP-for-Factory/pull/39) |
| M4.3.6 request deduplication / concurrent requests | ยังไม่เริ่ม ไม่ได้รับอนุมัติให้เริ่มโดยงานส่งต่อนี้ |
| M4.3.7 ตรวจเส้นทางโอนทั้งหมด / independent review | ยังไม่เสร็จ แม้ tests ของแต่ละส่วนผ่านแล้ว |
| M4.4, M4.5, M4.6, M4.7 | ยังไม่เสร็จ: concurrency รวม, reversal, UI, demo ตาม [TASKS](../TASKS.md) |

**M4.3 และ M4 ทั้งหมดยังไม่เสร็จ** ห้ามติ๊กงานใหญ่เพราะงานย่อยบางส่วนผ่าน
M4.3.1/3/4/5 ใช้ self-review/self-verification ไม่ใช่ independent agent review
M4.2 มี independent review จริง: [รายงาน](../reviews/issue-29-stock-receipt-independent-review.md)
ห้ามอ้างว่ามี Agent แยก หากไม่ได้สร้างและใช้จริง

## กติกาที่เจ้าของเลือกแล้ว — ไม่ต้องถามซ้ำ

- ผู้โอนต้องเป็น persisted active user มี **WAREHOUSE ที่ทั้งสองคลัง**
  QUALITY/staff/superuser อย่างเดียวใช้แทนไม่ได้ ตรวจและ lock สิทธิ์ขณะเขียน
- ต้นทางต้อง **RELEASED**; ปลายทางรับ HOLD/default HOLD หรือ RELEASED ได้และคงสถานะเดิม
  สถานะแยกตาม Lot–Warehouse; ไม่มีประวัติถือเป็น HOLD; Inventory ไม่ release ให้เอง
- Lot เดิมหนึ่งรายการ คลังต่างกันใน persisted Plant เดียวกัน และ Organization ตรงกัน
- quantity เป็น exact finite positive Decimal ใน base UOM, น้อยกว่า 10^14,
  แทนค่าได้ไม่เกิน 6 ตำแหน่ง; ไม่ปัดเศษ/แปลงหน่วย; reason ไม่ว่างและเก็บ Unicode/ช่องว่างเดิม
- ใช้ PostgreSQL READ COMMITTED; lock ตาม Lot → Item → Warehouses เรียง ID → Plant
  แล้ว actor/grants; Quality/สิทธิ์/หัก–เพิ่ม/ประวัติต้องอยู่ใน transaction เดียวกัน

## โค้ดสำคัญและข้อจำกัดปัจจุบัน

- [inventory/transfers.py](../../inventory/transfers.py): `transfer_stock` คืน `(debit, credit)`
  และสร้าง StockTransfer ใน atomic block/savepoint เดียวกัน
- [inventory/models.py](../../inventory/models.py): StockTransfer เชื่อม source_entry/destination_entry
  แบบ OneToOne + PROTECT; ผู้โอน/เหตุผล/จำนวนอ่านจาก immutable ledger ไม่เก็บสำเนาซ้ำ
- [migration 0005](../../inventory/migrations/0005_stock_transfer.py): identity/time จาก DB,
  ห้าม UPDATE/DELETE, ตรวจคู่ข้อมูลตรงกัน, ไม่ใช้ ledger ซ้ำหรือเป็นทั้ง receipt/transfer
- [Quality gate](../../inventory/transfer_policy.py), [Quality service](../../quality/services.py),
  [receipt/balance](../../inventory/services.py), [tests history](../../tests/inventory/test_transfer_history.py),
  [tests atomic](../../tests/inventory/test_atomic_transfer.py)
- **ยังไม่ idempotent** เรียก transfer_stock ซ้ำคือโอนใหม่ หากไม่แน่ใจว่า commit แล้ว ห้าม retry อัตโนมัติ
  ยังไม่มี request UUID/endpoint/UI; legacy ledger ไม่ถูกเดาจับคู่ย้อนหลัง
- มี tests ป้องกัน overdraw, rollback, Quality/grant races และ receipt/transfer ownership races แล้ว
  M4.3.6 ต้องเพิ่มกรณี request ซ้ำ/ชนกัน ไม่ทำส่วนที่เสร็จแล้วซ้ำเพราะชื่อ concurrency เหมือนกัน

## งานถัดไปที่เสนอให้เจ้าของพิจารณา

เมื่อเจ้าของสั่ง M4.3.6 จึงเปิด/อ่าน Issue และกำหนด acceptance ก่อนเขียน:
request identity บน StockTransfer, exact retry คืนรายการเดิม, payload ต่างแต่ key เดียวกันต้อง conflict,
สองคำขอ key เดียวกันต้องไม่เกิด ledger เพิ่ม และครอบคลุมชนกันข้าม Lot/rollback
ต้องตกลงการจัดการ legacy records ที่ไม่มี request ID และนโยบาย retry เมื่อสิทธิ์/Quality เปลี่ยน
ห้ามถือว่าข้อเสนอในไฟล์นี้เป็นการอนุมัติกติกาที่ยังไม่ได้เลือก
หลัง implementation/tests นิ่ง จึงตรวจอิสระจริงใน M4.3.7 และขอเจ้าของอนุมัติ Merge แยก

## วิธีทำงานต่อให้ประหยัด context

อ่าน [AGENTS](../../AGENTS.md), TASKS, MULTI_AGENT, SCRUTINIZE, DEVELOPMENT ครั้งแรก
เก็บข้อกำหนดสำคัญไว้ แล้วอ่านซ้ำเฉพาะส่วนที่เปลี่ยน/สงสัย
อ่านข้อมูลที่ไม่ขึ้นต่อกันพร้อมกัน; ส่งโจทย์ Agent แบบกระชับหากได้รับอนุญาตให้ใช้
รวมบันทึกหลักฐานเป็นช่วง; รอจริงตามลำดับ ผลทดสอบ → แก้ไข → ตรวจอิสระ → CI final head
GitHub ใช้ browser ที่เตรียมไว้; ตรวจ repository/branch/HEAD/working tree และ CI สดเสมอ
อย่าเพิ่มขั้นตอนขออนุมัติซ้ำเรื่องที่เจ้าของเลือกแล้ว แต่ห้ามสืบทอดคำอนุมัติ Merge PR เก่าไป PR ใหม่

## Environment / ส่งต่อให้คนหรือ AI ถัดไป

Python 3.14.8, Django 5.2.18, PostgreSQL 18.6, psycopg 3.3.6,
pytest 9.1.1, pytest-django 4.14.0, Ruff 0.17.1 ตาม [DEVELOPMENT](../DEVELOPMENT.md)
เครื่องนี้ไม่มี `.env` ในช่วงงานล่าสุด จึงใช้ disposable PostgreSQL บน GitHub Actions
ห้ามอ้าง local DB/SQLite/mocks ว่าเทียบเท่า PostgreSQL หรือพิมพ์ค่า secret ใน logs
คำสั่ง tests มีใน [workflow](../../.github/workflows/foundation.yml)

เริ่ม AI ใหม่โดยคัดลอกข้อความใน [AI-CHAT-STARTER.md](AI-CHAT-STARTER.md)
ไฟล์และโค้ดที่ commit/push อยู่ใน Git จึงไม่ต้องพึ่งความจำของแชตเดิม
ตรวจว่า PR เอกสารส่งต่อนี้ Merge หรือยัง; หากยัง ให้เปิด branch เอกสารหรือใช้ไฟล์ที่เจ้าของส่งให้
การหมดอายุสมาชิก/โควตาไม่ใช่เหตุให้ข้าม tests, review หรืออนุมัติ Merge

## การตรวจเอกสารส่งต่อรอบนี้

Root จัดทำและ self-review เอกสารเท่านั้น ไม่ได้อ้าง independent review ใหม่
ตรวจ Markdown ด้วย Python pathlib/re: 4 ไฟล์, local targets, balanced fences และ
checklist M4.3.1–5 เสร็จ/M4.3.6–7 ยังไม่เสร็จ ผ่าน; `git diff --check` ผ่าน
ไม่มี application/test/migration เปลี่ยนแปลง ผล CI ของ commit เอกสารนี้ให้ตรวจจาก
PR ที่เชื่อม Issue #40 ไม่ใช่ผล tests ใหม่ของ M4.3.6
Self-Scrutinize: เทียบ claims กับ Git/GitHub/CI และ trace source ที่ลิงก์ไว้
ใช้ Markdown สองไฟล์แทนสร้างระบบส่งต่อใหม่; verdict `ship` สำหรับเอกสาร
