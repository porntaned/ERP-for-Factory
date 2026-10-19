# Project checklist — รายการงานโครงการ

อัปเดตล่าสุด: 2026-10-19

`[x]` หมายถึงงานเสร็จและมีหลักฐานที่ลิงก์ไว้ ส่วนงานที่กำลังทำ ติดขัด หรือยังไม่ได้ตรวจรับใช้ `[ ]` งานใหญ่เสร็จเมื่อทุกงานย่อยและเกณฑ์ตรวจรับเสร็จเท่านั้น

## สถานะปัจจุบัน

เอกสารเริ่มต้น, Multi-Agent execution contract, GitHub Issue #1, Branch สำหรับทำงาน, Email privacy สำหรับ Commit ใหม่, กฎป้องกัน `main` และรายงาน Independent review สำหรับ Bootstrap ถูกบันทึกแล้ว [Governance PR #2](https://github.com/porntaned/ERP-for-Factory/pull/2) เปิดให้เจ้าของตรวจ โดยยังไม่มี Application code, Migration, Test หรือ CI และยังไม่มีการ Merge หรือ Deploy

## M0 — กำหนดโครงการและวิธีทำงาน

- [x] **M0 — เอกสารตั้งต้นอยู่บน GitHub Branch**
  - [x] M0.1 กำหนดเป้าหมาย Portfolio และโรงงานจำลอง — [Project brief](PROJECT.md)
  - [x] M0.2 กำหนดขอบเขตและกฎ Agent — [AGENTS.md](../AGENTS.md)
  - [x] M0.3 กำหนดวิธีตรวจด้วย Scrutinize — [Scrutinize](SCRUTINIZE.md)
  - [x] M0.4 สร้าง Checklist กลางพร้อมหลักฐาน — ไฟล์นี้
  - [x] M0.5 กำหนดบทบาท Agent, การส่งต่องาน, หลักฐาน, เพดานแก้ไขและจุดหยุด — [Multi-Agent execution contract](MULTI_AGENT.md)

## MA — หลักฐานการทำงานแบบ Multi-Agent

- [ ] **MA — มีหลักฐานครบว่าหลาย Agent ทำงานและตรวจสอบกันจริง**
  - [x] MA.1 เผยแพร่ Execution contract — [Multi-Agent execution contract](MULTI_AGENT.md)
  - [ ] MA.2 บันทึกบทบาทและ Assignment ของแต่ละ Issue
  - [ ] MA.3 บันทึก Handoff พร้อมไฟล์ คำสั่ง ผลลัพธ์ และ Commit SHA
  - [x] MA.4 บันทึกผล Independent review ที่ระบุ Agent และ Commit ที่ตรวจ — [Bootstrap independent review](reviews/bootstrap-independent-review.md)
  - [ ] MA.5 บันทึกรอบแก้ไข จุดหยุด หรือการส่งต่อให้เจ้าของเมื่อเกิดขึ้น
  - [ ] MA.6 สรุปหลักฐาน Agent, Issue, PR และ CI สำหรับ Portfolio

## M1 — เตรียม Foundation Issue และสภาพแวดล้อม

- [ ] **M1 — พร้อมเริ่มพัฒนา Foundation**
  - [x] M1.1 สร้าง GitHub Issue จริง — [Issue #1](https://github.com/porntaned/ERP-for-Factory/issues/1)
  - [x] M1.2 สร้าง Branch `chore/project-foundation` จาก `main`
  - [x] M1.3 เผยแพร่ Project brief, กฎ Agent, Scrutinize, Multi-Agent contract และ Checklist บน Branch
  - [x] M1.4 เปิด Email privacy สำหรับ Commit ใหม่ — [Commit ที่ใช้ Metadata แบบไม่เปิดเผยอีเมล](https://github.com/porntaned/ERP-for-Factory/commit/e6a5dbc633872188551c30198f005c2f127d6890)
  - [x] M1.5 เปิดกฎป้องกัน `main` — [Ruleset: Protect main](https://github.com/porntaned/ERP-for-Factory/rules/25390359)
  - [ ] M1.6 ยืนยันเวอร์ชัน Python, Django, PostgreSQL และ Dependencies
  - [ ] M1.7 เตรียมสภาพทดสอบ PostgreSQL ที่ใช้งานได้
  - [ ] M1.8 กำหนด Development/Test configuration และวิธีเก็บค่าลับนอก Source
  - [x] M1.9 เปิด PR สำหรับ Governance/Project bootstrap โดยไม่ปิด Issue #1 — [PR #2](https://github.com/porntaned/ERP-for-Factory/pull/2)

M1.9 ตรวจรับเฉพาะเอกสารและกลไกกำกับงาน ไม่ทำให้ M2 หรือ Acceptance Criteria ของ Issue #1 เสร็จ

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
- 2026-10-19: เพิ่ม Multi-Agent execution contract, เปิด Email privacy สำหรับ Commit ใหม่ และเปิด Ruleset `Protect main`; เก็บประวัติ Commit เดิมไว้ตามการตัดสินใจของเจ้าของ
- 2026-10-19: Independent Agent ตรวจ Bootstrap ที่ SHA `e6a5dbc633872188551c30198f005c2f127d6890`; verdict `fix-then-ship` — [รายงาน](reviews/bootstrap-independent-review.md)
- 2026-10-19: แก้รอบที่ 1 โดยบันทึกรายงาน แยกหลักฐาน Email privacy/Ruleset และเพิ่มงาน Governance PR; M2.7 ยังคงไม่เสร็จเพราะเป็นงานตรวจการพัฒนา Foundation
- 2026-10-19: Independent re-review ที่ SHA `49fcd39f4b8efdf37ac4f197cd166cd96fc80349` ได้ verdict `ship` และบันทึกผลไว้ใน [PR #2](https://github.com/porntaned/ERP-for-Factory/pull/2)
- 2026-10-19: เปิด Governance-only [PR #2](https://github.com/porntaned/ERP-for-Factory/pull/2); Issue #1 และ M2 ยังไม่เสร็จ และเจ้าของเป็นผู้ตัดสินใจ Merge
