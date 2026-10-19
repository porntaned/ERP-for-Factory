# Project checklist — รายการงานโครงการ

อัปเดตล่าสุด: 2026-10-19

`[x]` หมายถึงงานเสร็จและมีหลักฐานที่ลิงก์ไว้ ส่วนงานที่กำลังทำ ติดขัด หรือยังไม่ได้ตรวจรับใช้ `[ ]` งานใหญ่เสร็จเมื่อทุกงานย่อยและเกณฑ์ตรวจรับเสร็จเท่านั้น

## สถานะปัจจุบัน

เอกสารเริ่มต้น, GitHub Issue #1 และ Branch สำหรับทำงานถูกสร้างแล้ว ยังไม่มี Application code, Migration, Test, CI หรือ Pull Request

## M0 — กำหนดโครงการและวิธีทำงาน

- [x] **M0 — เอกสารตั้งต้นอยู่บน GitHub Branch**
  - [x] M0.1 กำหนดเป้าหมาย Portfolio และโรงงานจำลอง — [Project brief](PROJECT.md)
  - [x] M0.2 กำหนดขอบเขตและกฎ Agent — [AGENTS.md](../AGENTS.md)
  - [x] M0.3 กำหนดวิธีตรวจด้วย Scrutinize — [Scrutinize](SCRUTINIZE.md)
  - [x] M0.4 สร้าง Checklist กลางพร้อมหลักฐาน — ไฟล์นี้

## M1 — เตรียม Foundation Issue และสภาพแวดล้อม

- [ ] **M1 — พร้อมเริ่มพัฒนา Foundation**
  - [x] M1.1 สร้าง GitHub Issue จริง — [Issue #1](https://github.com/porntaned/ERP-for-Factory/issues/1)
  - [x] M1.2 สร้าง Branch `chore/project-foundation` จาก `main`
  - [x] M1.3 เผยแพร่ Project brief, กฎ Agent, Scrutinize และ Checklist บน Branch
  - [ ] M1.4 ยืนยันเวอร์ชัน Python, Django, PostgreSQL และ Dependencies
  - [ ] M1.5 เตรียมสภาพทดสอบ PostgreSQL ที่ใช้งานได้
  - [ ] M1.6 กำหนด Development/Test configuration และวิธีเก็บค่าลับนอก Source

## M2 — Organization → Plant → Warehouse Foundation

ขอบเขตและเกณฑ์ตรวจรับหลักอยู่ใน [Issue #1](https://github.com/porntaned/ERP-for-Factory/issues/1)

- [ ] **M2 — Foundation ผ่านการตรวจและเปิด PR**
  - [ ] M2.1 เขียน Test และบันทึก TDD RED
  - [ ] M2.2 สร้าง Django project และโมดูล Organization, Plant, Warehouse
  - [ ] M2.3 เพิ่ม Migration และ Database constraints
  - [ ] M2.4 พิสูจน์ uniqueness, invalid parents, deletion protection และ concurrent writes บน PostgreSQL
  - [ ] M2.5 รัน Tests, Django checks และ Ruff
  - [ ] M2.6 ตั้ง GitHub Actions CI และตรวจผลบน Commit ล่าสุด
  - [ ] M2.7 ทำ Scrutinize และ Independent review ตามหลักฐานจริง
  - [ ] M2.8 เปิด PR พร้อม Scope, ผลตรวจและข้อจำกัดให้เจ้าของตัดสินใจ Merge

## M3 — Item, Lot, สิทธิ์ และ Audit

- [ ] **M3 — ข้อมูลหลักพร้อมสำหรับ Inventory**
  - [ ] M3.1 กำหนด Item, หน่วยนับ และ Lot identity
  - [ ] M3.2 กำหนดผู้ใช้จำลองและสิทธิ์ตามบทบาท/คลัง
  - [ ] M3.3 กำหนด Audit และสถานะ Released/Hold ขั้นต่ำ
  - [ ] M3.4 แยก Issue, Test, Review และ PR สำหรับแต่ละส่วน

## M4 — Inventory MVP

- [ ] **M4 — รับเข้า โอน และดูประวัติผ่านหน้าจอได้**
  - [ ] M4.1 สร้าง Stock ledger และกฎป้องกันยอดติดลบ
  - [ ] M4.2 รับวัตถุดิบจำลองพร้อม Lot, สิทธิ์และ Audit
  - [ ] M4.3 โอนระหว่างคลังใน Plant เดียวกัน
  - [ ] M4.4 ป้องกันคำขอซ้ำและทดสอบ Concurrent transactions
  - [ ] M4.5 เพิ่ม Reversal ที่อ้างรายการต้นฉบับ
  - [ ] M4.6 เพิ่มหน้ารับเข้า โอน ยอดคงเหลือและประวัติ
  - [ ] M4.7 สาธิต 100 → โอน 30 → คงเหลือ 70/30 พร้อมหลักฐาน

## M5 — Manufacturing ขั้นต้น

- [ ] **M5 — ผลิตสินค้าจำลองหนึ่งรุ่นได้**
  - [ ] M5.1 BOM แบบมีเวอร์ชันและ Production order
  - [ ] M5.2 เบิก คืน ใช้วัตถุดิบและรับผลผลิตผ่าน Inventory
  - [ ] M5.3 เชื่อม Lot วัตถุดิบกับ Lot ผลผลิต
  - [ ] M5.4 ทดสอบและ Scrutinize เส้นทางการผลิตจริง

## M6 — Quality และ Traceability

- [ ] **M6 — ตรวจคุณภาพและค้นย้อน Lot ได้**
  - [ ] M6.1 Incoming/Final inspection และสิทธิ์ผู้ตัดสินใจ
  - [ ] M6.2 บังคับ Hold/Release ร่วมกับ Inventory
  - [ ] M6.3 ค้นย้อนวัตถุดิบ ↔ ผลผลิต
  - [ ] M6.4 ทดสอบจำนวน, concurrency และ Audit ของ QC

## M7 — Portfolio delivery

- [ ] **M7 — Portfolio ทดลองและประเมินซ้ำได้**
  - [ ] M7.1 ข้อมูลจำลองและวิธี Reset demo
  - [ ] M7.2 คู่มือติดตั้งที่ตรวจจากสภาพใหม่
  - [ ] M7.3 Architecture และ Domain diagrams ที่ตรงกับโค้ด
  - [ ] M7.4 ภาพหรือวิดีโอ Demo พร้อม Issue/PR/CI evidence
  - [ ] M7.5 Final Scrutinize จากข้อมูลจำลองถึงผลที่ผู้ชมเห็น

## Deferred

- [ ] Procurement และ Sales
- [ ] Accounting/Costing เต็มรูปแบบ
- [ ] Advanced planning, MES และ WMS
- [ ] Maintenance, HR/Payroll และ CRM
- [ ] External hardware/PLC integration
- [ ] Hosting/Deployment — ต้องอนุมัติวิธีและค่าใช้จ่ายก่อน

## Progress log

- 2026-10-19: สร้าง Issue #1, Branch และเอกสารเริ่มต้นบน GitHub โดยยังไม่เริ่ม Application code
