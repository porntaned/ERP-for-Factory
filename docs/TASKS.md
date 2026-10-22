# Project checklist — รายการงานโครงการ

อัปเดตล่าสุด: 2026-10-22

`[x]` หมายถึงงานเสร็จและมีหลักฐานที่ลิงก์ไว้ ส่วนงานที่กำลังทำ ติดขัด หรือยังไม่ได้ตรวจรับใช้ `[ ]` งานใหญ่เสร็จเมื่อทุกงานย่อยและเกณฑ์ตรวจรับเสร็จเท่านั้น

## สถานะปัจจุบัน

[PR #12](https://github.com/porntaned/ERP-for-Factory/pull/12) Merge เข้า main ที่ `9b1d182eb6867b70f076e95a63dc03f1814f00ec` แล้ว; Issue #11 ปิด ส่วนผล [Audit หลัง Merge](https://github.com/porntaned/ERP-for-Factory/blob/codex/project-audit-after-pr12/docs/reviews/project-audit-after-pr12.md) ยังมีงานแก้ก่อนเริ่ม Inventory

Finding 1 เสร็จแล้ว: เจ้าของ Merge [PR #14](https://github.com/porntaned/ERP-for-Factory/pull/14) เข้า `main` ที่ `eba63622495c6b065ad0abcd8e652676f9189d20` และ [Issue #13](https://github.com/porntaned/ERP-for-Factory/issues/13) ปิดแล้ว

Finding 2 เสร็จแล้ว: เจ้าของอนุญาตให้ Merge [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16) เข้า `main` ที่ `c62687b7ed60515de9424e69fe22ef43bbdfe81e`; [Issue #15](https://github.com/porntaned/ERP-for-Factory/issues/15) ปิดเป็น completed — [หลักฐาน Merge](evidence/issue-15-unsaved-user-policy.md#owner-authorized-merge), [Independent review](reviews/issue-15-unsaved-user-policy-independent-review.md) และ [PR #17](https://github.com/porntaned/ERP-for-Factory/pull/17) บันทึกสถานะ Merge แล้ว ไม่มีการ Deploy

รอบนี้ส่งมอบเฉพาะ Finding 3 ใน [Issue #18](https://github.com/porntaned/ERP-for-Factory/issues/18): PostgreSQL RED 4 failed/270 passed → GREEN targeted 11 passed/full 281 passed ที่ `1c19981778b2f1cd45279de1b30945523d5827e0`; Independent Scrutinize `ship` — [หลักฐาน](evidence/issue-18-event-identity.md), [Review](reviews/issue-18-event-identity-independent-review.md) รอเปิด PR ให้เจ้าของตรวจ; Findings 4–5 ยังไม่ได้แก้ ไม่มีการ Merge หรือ Deploy ในงานนี้

## M0 — กำหนดโครงการและวิธีทำงาน

- [x] **M0 — เอกสารตั้งต้นอยู่บน GitHub Branch**
  - [x] M0.1 กำหนดเป้าหมาย Portfolio และโรงงานจำลอง — [Project brief](PROJECT.md)
  - [x] M0.2 กำหนดขอบเขตและกฎ Agent — [AGENTS.md](../AGENTS.md)
  - [x] M0.3 กำหนดวิธีตรวจด้วย Scrutinize — [Scrutinize](SCRUTINIZE.md)
  - [x] M0.4 สร้าง Checklist กลางพร้อมหลักฐาน — ไฟล์นี้
  - [x] M0.5 กำหนดบทบาท Agent, การส่งต่องาน, หลักฐาน, เพดานแก้ไขและจุดหยุด — [Multi-Agent execution contract](MULTI_AGENT.md)

## MA — หลักฐานการทำงานแบบ Multi-Agent

- [x] **MA — มีหลักฐานครบว่าหลาย Agent ทำงานและตรวจสอบกันจริง**
  - [x] MA.1 เผยแพร่ Execution contract — [Multi-Agent execution contract](MULTI_AGENT.md)
  - [x] MA.2 บันทึกบทบาทและ Assignment ของแต่ละ Issue — [Issue #1 assignment](assignments/issue-1-foundation.md)
  - [x] MA.3 บันทึก Handoff พร้อมไฟล์ คำสั่ง ผลลัพธ์ และ Commit SHA — [Issue #1 handoff](assignments/issue-1-foundation.md#handoff-evidence)
  - [x] MA.4 บันทึกผล Independent review ที่ระบุ Agent และ Commit ที่ตรวจ — [Bootstrap review](reviews/bootstrap-independent-review.md), [Issue #1 TDD RED review](reviews/issue-1-tdd-red-independent-review.md), [Issue #1 implementation review](reviews/issue-1-foundation-independent-review.md)
  - [x] MA.5 บันทึกรอบแก้ไข จุดหยุด หรือการส่งต่อให้เจ้าของเมื่อเกิดขึ้น — [TDD RED repairs](reviews/issue-1-tdd-red-independent-review.md#findings-and-repair), [Implementation repair](reviews/issue-1-foundation-independent-review.md#finding-and-repair)
  - [x] MA.6 สรุปหลักฐาน Agent, Issue, PR และ CI สำหรับ Portfolio — [Issue #1 handoff](assignments/issue-1-foundation.md#handoff-evidence), [PR #3](https://github.com/porntaned/ERP-for-Factory/pull/3), [Latest branch CI](https://github.com/porntaned/ERP-for-Factory/actions/workflows/foundation.yml?query=branch%3Afeat%2Fwarehouse-foundation)

## M1 — เตรียม Foundation Issue และสภาพแวดล้อม

- [x] **M1 — พร้อมเริ่มพัฒนา Foundation**
  - [x] M1.1 สร้าง GitHub Issue จริง — [Issue #1](https://github.com/porntaned/ERP-for-Factory/issues/1)
  - [x] M1.2 สร้าง Branch `chore/project-foundation` จาก `main`
  - [x] M1.3 เผยแพร่ Project brief, กฎ Agent, Scrutinize, Multi-Agent contract และ Checklist บน Branch
  - [x] M1.4 เปิด Email privacy สำหรับ Commit ใหม่ — [Commit ที่ใช้ Metadata แบบไม่เปิดเผยอีเมล](https://github.com/porntaned/ERP-for-Factory/commit/e6a5dbc633872188551c30198f005c2f127d6890)
  - [x] M1.5 เปิดกฎป้องกัน `main` — [Ruleset: Protect main](https://github.com/porntaned/ERP-for-Factory/rules/25390359)
  - [x] M1.6 ยืนยันเวอร์ชัน Python, Django, PostgreSQL และ Dependencies — [Development contract](DEVELOPMENT.md#version-contract)
  - [x] M1.7 เตรียมสภาพทดสอบ PostgreSQL ที่ใช้งานได้ — [PostgreSQL TDD RED evidence](evidence/issue-1-tdd-red.md)
  - [x] M1.8 กำหนด Development/Test configuration และวิธีเก็บค่าลับนอก Source — [Configuration boundary](DEVELOPMENT.md#configuration-boundary)
  - [x] M1.9 เปิด PR สำหรับ Governance/Project bootstrap โดยไม่ปิด Issue #1 — [PR #2](https://github.com/porntaned/ERP-for-Factory/pull/2)

M1.9 ตรวจรับเฉพาะเอกสารและกลไกกำกับงาน ไม่ทำให้ M2 หรือ Acceptance Criteria ของ Issue #1 เสร็จ

## M2 — Organization → Plant → Warehouse Foundation

ขอบเขตและเกณฑ์ตรวจรับหลักอยู่ใน [Issue #1](https://github.com/porntaned/ERP-for-Factory/issues/1)

- [x] **M2 — Foundation ผ่านการตรวจและ Merge เข้า `main`**
  - [x] M2.1 เขียน Test และบันทึก TDD RED — [PostgreSQL TDD RED evidence](evidence/issue-1-tdd-red.md)
  - [x] M2.2 สร้าง Django project และโมดูล Organization, Plant, Warehouse — [Implementation](../facilities/models.py)
  - [x] M2.3 เพิ่ม Migration และ Database constraints — [Initial migration](../facilities/migrations/0001_initial.py)
  - [x] M2.4 พิสูจน์ uniqueness, invalid parents, deletion protection และ concurrent writes บน PostgreSQL — [GREEN evidence](evidence/issue-1-green.md#acceptance-evidence)
  - [x] M2.5 รัน Tests, Django checks และ Ruff — [GREEN evidence](evidence/issue-1-green.md#verified-path)
  - [x] M2.6 ตั้ง GitHub Actions CI และตรวจผลบน Commit ล่าสุด — [Latest branch CI](https://github.com/porntaned/ERP-for-Factory/actions/workflows/foundation.yml?query=branch%3Afeat%2Fwarehouse-foundation), [Implementation run #4](https://github.com/porntaned/ERP-for-Factory/actions/runs/39369435238)
  - [x] M2.7 ทำ Scrutinize และ Independent review ตามหลักฐานจริง — [Independent review](reviews/issue-1-foundation-independent-review.md)
  - [x] M2.8 เปิด PR พร้อม Scope, ผลตรวจและข้อจำกัดให้เจ้าของตัดสินใจ Merge — [PR #3](https://github.com/porntaned/ERP-for-Factory/pull/3)
  - [x] M2.9 Merge Foundation และปิด Issue #1 — [Merge commit `1f7acc6`](https://github.com/porntaned/ERP-for-Factory/commit/1f7acc61d446e581d89588b96b80f7d4f25609f8), [Issue #1](https://github.com/porntaned/ERP-for-Factory/issues/1)

## M3 — Item, Lot, สิทธิ์ และ Audit

- [ ] **M3 — ข้อมูลหลักพร้อมสำหรับ Inventory**
  - [x] M3.1 กำหนด Item, หน่วยนับ และ Lot identity — [Item/UOM PR #6](https://github.com/porntaned/ERP-for-Factory/pull/6), [Lot PR #8](https://github.com/porntaned/ERP-for-Factory/pull/8), [merge commit](https://github.com/porntaned/ERP-for-Factory/commit/b7a9bddd87d258c343d17abbc76e53de9a436dcd)
    - [x] M3.1.1 สร้าง Issue แยกสำหรับ Item และหน่วยนับ — [Issue #5](https://github.com/porntaned/ERP-for-Factory/issues/5)
    - [x] M3.1.2 บันทึก Assignment และ TDD RED บน PostgreSQL — [Assignment](assignments/issue-5-item-uom.md), [RED evidence](evidence/issue-5-tdd-red.md), [Independent review](reviews/issue-5-tdd-red-independent-review.md), [Foundation #9](https://github.com/porntaned/ERP-for-Factory/actions/runs/39390285346)
    - [x] M3.1.3 สร้าง Item และ Unit of Measure พร้อม Migration — [Implementation](../catalog/models.py), [Migration](../catalog/migrations/0001_initial.py)
    - [x] M3.1.4 พิสูจน์ Constraints, Concurrent writes และ Regression suite — [GREEN evidence](evidence/issue-5-green.md), [Foundation #11](https://github.com/porntaned/ERP-for-Factory/actions/runs/39390768062)
    - [x] M3.1.5 ทำ Independent Scrutinize และเปิด PR ให้เจ้าของตรวจ — [Independent review](reviews/issue-5-item-uom-independent-review.md), [PR #6](https://github.com/porntaned/ERP-for-Factory/pull/6)
    - [x] M3.1.6 เปิด Issue สำหรับ Lot identity — [Issue #7](https://github.com/porntaned/ERP-for-Factory/issues/7), [Assignment](assignments/issue-7-lot-identity.md)
    - [x] M3.1.7 เขียน PostgreSQL tests และบันทึก TDD RED ที่ตรวจสอบอิสระแล้ว — [RED evidence](evidence/issue-7-tdd-red.md), [Independent review](reviews/issue-7-tdd-red-independent-review.md), [Foundation #16](https://github.com/porntaned/ERP-for-Factory/actions/runs/39394726202)
    - [x] M3.1.8 สร้าง `inventory.Lot` และ Migration ตาม Contract ที่ล็อกไว้ — [Implementation](../inventory/models.py), [Migration](../inventory/migrations/0001_initial.py)
    - [x] M3.1.9 พิสูจน์ Constraints, Concurrent writes และ Regression suite เป็น GREEN — [GREEN evidence](evidence/issue-7-green.md), [Foundation #18](https://github.com/porntaned/ERP-for-Factory/actions/runs/39395440223), [Independent review](reviews/issue-7-lot-independent-review.md)
    - [x] M3.1.10 ทำ Independent Scrutinize และเปิด PR ให้เจ้าของตรวจ — [Independent review](reviews/issue-7-lot-independent-review.md), [PR #8](https://github.com/porntaned/ERP-for-Factory/pull/8)
  - [x] M3.2 กำหนดผู้ใช้จำลองและสิทธิ์ตามบทบาท/คลัง — [PR #10](https://github.com/porntaned/ERP-for-Factory/pull/10)
    - [x] M3.2.1 เปิด Issue และล็อกขอบเขต Warehouse role assignment — [Issue #9](https://github.com/porntaned/ERP-for-Factory/issues/9)
    - [x] M3.2.2 บันทึก Assignment และ TDD RED บน PostgreSQL — [Assignment](assignments/issue-9-warehouse-role-grants.md), [RED evidence](evidence/issue-9-tdd-red.md), [Foundation #26](https://github.com/porntaned/ERP-for-Factory/actions/runs/39435149544)
    - [x] M3.2.3 เพิ่ม Django Auth, Warehouse role assignment และ permission interface — [Implementation](../access_control/models.py), [Policies](../access_control/policies.py), [Migration](../access_control/migrations/0001_initial.py)
    - [x] M3.2.4 พิสูจน์ Constraints, Concurrent writes และ Regression suite เป็น GREEN — [GREEN evidence](evidence/issue-9-green.md), [Foundation #28](https://github.com/porntaned/ERP-for-Factory/actions/runs/39444111594)
    - [x] M3.2.5 ทำ Independent Scrutinize และเปิด PR ให้เจ้าของตรวจ — [Independent review](reviews/issue-9-warehouse-role-independent-review.md), [PR #10](https://github.com/porntaned/ERP-for-Factory/pull/10)
  - [x] M3.3 ส่งมอบ Audit และสถานะ Released/Hold ขั้นต่ำผ่าน PR #12; follow-up อยู่ใน PA — [Issue #11](https://github.com/porntaned/ERP-for-Factory/issues/11)
    - [x] M3.3.1 เปิด Issue และล็อกขอบเขต Warehouse-scoped Lot disposition — [Issue #11](https://github.com/porntaned/ERP-for-Factory/issues/11), [Scope review](reviews/issue-11-scope-independent-review.md)
    - [x] M3.3.2 บันทึก Assignment และ TDD RED บน PostgreSQL — [Assignment](assignments/issue-11-lot-disposition-audit.md), [RED evidence](evidence/issue-11-tdd-red.md), [Independent review](reviews/issue-11-tdd-red-independent-review.md), [Foundation #35](https://github.com/porntaned/ERP-for-Factory/actions/runs/39452581694)
    - [x] M3.3.3 เพิ่ม Quality disposition history, transition interface และ Migration — [Implementation](../quality/models.py), [Services](../quality/services.py), [Migration](../quality/migrations/0001_initial.py), [Handoff](assignments/issue-11-lot-disposition-audit.md#m333-implementation-handoff), [Commit `825b34f`](https://github.com/porntaned/ERP-for-Factory/commit/825b34fea7ad16605210ef4760a41627f0965c06)
    - [x] M3.3.4 พิสูจน์ Authorization, Constraints, Immutability, Retry, Concurrency และ Regression suite เป็น GREEN — [GREEN evidence](evidence/issue-11-green.md), [Foundation #39](https://github.com/porntaned/ERP-for-Factory/actions/runs/39526993055) ที่ `7ce4ef84570628234d4097e0b95643bbf38880db`
    - [x] M3.3.5 ทำ Independent Scrutinize และเปิด PR ให้เจ้าของตรวจ — [Independent review](reviews/issue-11-lot-disposition-independent-review.md) verdict `ship`, [PR #12](https://github.com/porntaned/ERP-for-Factory/pull/12)
  - [ ] M3.4 แยก Issue, Test, Review และ PR สำหรับแต่ละส่วน

## PA — งานแก้จาก Audit หลัง PR #12

- [x] PA.4 แก้ shared policies ครบ Findings 1–2 — [PR #14](https://github.com/porntaned/ERP-for-Factory/pull/14), [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16)
  - [x] PA.4.1 เปิด Issue และกำหนดขอบเขตเฉพาะ Finding 1 — [Issue #13](https://github.com/porntaned/ERP-for-Factory/issues/13), [Assignment](assignments/issue-13-policy-deactivation.md)
  - [x] PA.4.2 พิสูจน์ RED และแก้ persisted-active filtering ผ่าน PostgreSQL GREEN — [หลักฐาน](evidence/issue-13-policy-deactivation.md)
  - [x] PA.4.3 Independent Scrutinize และเปิด PR สำหรับ Finding 1 — [Review](reviews/issue-13-policy-deactivation-independent-review.md), [PR #14](https://github.com/porntaned/ERP-for-Factory/pull/14)
  - [x] PA.4.4 เจ้าของตรวจรับและ Merge Finding 1 — [PR #14](https://github.com/porntaned/ERP-for-Factory/pull/14), [Merge commit](https://github.com/porntaned/ERP-for-Factory/commit/eba63622495c6b065ad0abcd8e652676f9189d20), [Issue #13 ปิด](https://github.com/porntaned/ERP-for-Factory/issues/13)
  - [x] PA.4.5 Finding 2: unsaved User ที่ใส่ PK มาเอง — [PR #16 Merge แล้ว](https://github.com/porntaned/ERP-for-Factory/pull/16), [หลักฐาน](evidence/issue-15-unsaved-user-policy.md#owner-authorized-merge)
    - [x] เปิด Issue และกำหนด Scope — [Issue #15](https://github.com/porntaned/ERP-for-Factory/issues/15), [Assignment](assignments/issue-15-unsaved-user-policy.md)
    - [x] พิสูจน์ PostgreSQL RED/GREEN และ Regression — [หลักฐาน](evidence/issue-15-unsaved-user-policy.md)
    - [x] Independent Scrutinize — [Review](reviews/issue-15-unsaved-user-policy-independent-review.md), verdict `ship` ที่ `d132237211c5abdc509679da91b7b12566dff38c`
    - [x] เปิด PR ให้เจ้าของตรวจ — [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16), [ภาพหลักฐาน](evidence/issue-15-pr.jpg)
    - [x] เจ้าของอนุญาตให้ Merge Finding 2 — [Commit `c62687b`](https://github.com/porntaned/ERP-for-Factory/commit/c62687b7ed60515de9424e69fe22ef43bbdfe81e), [Issue #15 ปิด](https://github.com/porntaned/ERP-for-Factory/issues/15)
- [ ] PA.5 Finding 3: explicit high event ID — แก้และตรวจแล้ว รอ PR และเจ้าของตรวจรับ
  - [x] เปิด Issue และล็อก Scope — [Issue #18](https://github.com/porntaned/ERP-for-Factory/issues/18), [Assignment](assignments/issue-18-event-identity.md)
  - [x] พิสูจน์ PostgreSQL RED/GREEN รวม migration upgrade/reverse/reapply และ regression — [หลักฐาน](evidence/issue-18-event-identity.md)
  - [x] Independent Scrutinize — [Review](reviews/issue-18-event-identity-independent-review.md), verdict `ship` ที่ `1c19981778b2f1cd45279de1b30945523d5827e0`
  - [ ] เปิด PR ให้เจ้าของตรวจ
  - [ ] เจ้าของตรวจรับและ Merge Finding 3
- [ ] PA.6 Finding 4: CI trigger ทั่วไป — ยังไม่เริ่ม; Issue #13 เพิ่มเฉพาะ branch ที่ใช้พิสูจน์งานนี้
- [ ] PA.7 Finding 5: README status — ยังไม่เริ่ม

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
- 2026-10-20: กู้สถานะจากรอบที่ติดลิมิตโดยเก็บงานเดิมไว้ใน `stash@{0}` และแยก branch สำรอง `backup/local-planning-draft-20261019`; ไม่ลบหรือเขียนทับงานเดิม
- 2026-10-20: ยืนยัน stack และ configuration โดย pytest รวบรวมได้ 43 tests; Independent Scrutinize พบรอบแก้ FK transaction, deletion graph และ publishing target แล้ว re-review ผ่าน
- 2026-10-20: Push Commit [`31ba6be`](https://github.com/porntaned/ERP-for-Factory/commit/31ba6be9cf94f50f28267734f7040a4592db3545) ไป `feat/warehouse-foundation`; [Actions run #1](https://github.com/porntaned/ERP-for-Factory/actions/runs/39355731564) ผ่าน PostgreSQL setup/check และล้มด้วย expected TDD RED ก่อนเริ่ม M2.2
- 2026-10-20: เพิ่ม `facilities` models, Migration และ constraints ที่ Commit [`7db1db9`](https://github.com/porntaned/ERP-for-Factory/commit/7db1db96f810603650807abce5f0999c53bfa388); PostgreSQL suite เปลี่ยนเป็น GREEN
- 2026-10-20: Independent Scrutinize พบช่องว่างการทดสอบ NOT NULL โดยตรง จึงเพิ่ม 8 regression cases ที่ Commit [`8fdb446`](https://github.com/porntaned/ERP-for-Factory/commit/8fdb446669c47f892774c2fba2c2093ba4d1c1e8); [Foundation #4](https://github.com/porntaned/ERP-for-Factory/actions/runs/39369435238) ผ่าน 51 tests และ re-review ได้ verdict `ship`
- 2026-10-20: บันทึก GREEN/Independent review และเปิด [PR #3](https://github.com/porntaned/ERP-for-Factory/pull/3) แบบ stacked บน Governance PR #2; เจ้าของยังเป็นผู้ตัดสินใจ Merge และไม่มีการ Deploy
- 2026-10-20: Scrutinize Governance diff แล้ว Merge [PR #2](https://github.com/porntaned/ERP-for-Factory/pull/2) เข้า `main` ที่ [`ec79831`](https://github.com/porntaned/ERP-for-Factory/commit/ec79831bf0cd3b58ec8f204cdb9b74c3fdf3f0a7); ไม่มีการ Deploy
- 2026-10-20: เปลี่ยน Base ของ [PR #3](https://github.com/porntaned/ERP-for-Factory/pull/3) เป็น `main`, ยืนยัน Diff 6 Commits/25 ไฟล์, ไม่มี Conflict และ Check ของ Head `7d527ce` ผ่าน แล้ว Merge ที่ [`1f7acc6`](https://github.com/porntaned/ERP-for-Factory/commit/1f7acc61d446e581d89588b96b80f7d4f25609f8); Issue #1 ปิดเป็น `completed` และไม่มีการ Deploy
- 2026-10-20: เปิด [Issue #5](https://github.com/porntaned/ERP-for-Factory/issues/5) สำหรับ Item/UOM แยกจาก Lot, Push RED commit [`ca4dacb`](https://github.com/porntaned/ERP-for-Factory/commit/ca4dacbdc349ff7b4fcf5a3be10035c02e6f2c28) และ [Foundation #8](https://github.com/porntaned/ERP-for-Factory/actions/runs/39389877487) ยืนยัน PostgreSQL 18.6, 51 regression tests ผ่าน และ catalog tests ล้มเพราะ Model ยังไม่มีตาม TDD
- 2026-10-20: Independent RED review พบช่องว่าง empty-name contract จึงเพิ่ม 2 cases ที่ [`139eb14`](https://github.com/porntaned/ERP-for-Factory/commit/139eb14a1d99ab2a31fb940cdcd093b93f6602c7); [Foundation #9](https://github.com/porntaned/ERP-for-Factory/actions/runs/39390285346) ยืนยัน 45 catalog cases เป็น RED และ re-review ได้ verdict `ship`
- 2026-10-20: Implementer เพิ่ม Item/UOM และ Migration ที่ [`05b7eff`](https://github.com/porntaned/ERP-for-Factory/commit/05b7effe3eaba8a3b60b04aeee4542bd747c9308); [Foundation #11](https://github.com/porntaned/ERP-for-Factory/actions/runs/39390768062) ผ่าน PostgreSQL 18.6, fresh migration, Ruff และ 96 tests; รอ Independent implementation review ก่อนเปิด PR
- 2026-10-20: Independent Agent ตรวจ implementation commit `05b7eff` แบบ read-only ครบเส้นทาง Model → Migration → PostgreSQL constraints → Tests และได้ verdict `ship` โดยไม่พบ blocker, major หรือ minor — [รายงาน](reviews/issue-5-item-uom-independent-review.md)
- 2026-10-20: เปิด owner-review [PR #6](https://github.com/porntaned/ERP-for-Factory/pull/6) จาก `feat/item-uom-foundation` ไป `main`; Issue #5 จะปิดเมื่อเจ้าของ Merge เท่านั้น และไม่มีการ Deploy
- 2026-10-20: เจ้าของ Merge [PR #6](https://github.com/porntaned/ERP-for-Factory/pull/6) ที่ [`d31ac7a`](https://github.com/porntaned/ERP-for-Factory/commit/d31ac7a9f5286353ed05a46ccc6ce3be3c1678e1) และ Issue #5 ปิดเป็น `completed`; ไม่มีการ Deploy
- 2026-10-20: เปิด [Issue #7](https://github.com/porntaned/ERP-for-Factory/issues/7) สำหรับ Lot identity และ Push RED commit [`dab4b46`](https://github.com/porntaned/ERP-for-Factory/commit/dab4b460bb5f0fea476a72d8c609746e02c708d1); [Foundation #16](https://github.com/porntaned/ERP-for-Factory/actions/runs/39394726202) ยืนยัน PostgreSQL 18.6, 96 regression tests ผ่าน และ 19 Lot tests ล้มเฉพาะเพราะยังไม่มี `inventory.Lot` ตาม TDD
- 2026-10-20: Implementer เพิ่ม `inventory.Lot` และ Migration ที่ [`c66cab6`](https://github.com/porntaned/ERP-for-Factory/commit/c66cab65bb0f1dcb7dd1131514446651fecc47cf); [Foundation #18](https://github.com/porntaned/ERP-for-Factory/actions/runs/39395440223) ผ่าน PostgreSQL 18.6, fresh migration, Ruff และ 115 tests และ Independent Scrutinize ได้ verdict `ship`
- 2026-10-20: เปิด owner-review [PR #8](https://github.com/porntaned/ERP-for-Factory/pull/8) จาก `feat/lot-identity` ไป `main`; Issue #7 จะปิดเมื่อเจ้าของ Merge เท่านั้น และไม่มีการ Deploy
- 2026-10-20: เจ้าของ Merge [PR #8](https://github.com/porntaned/ERP-for-Factory/pull/8) ที่ [`b7a9bdd`](https://github.com/porntaned/ERP-for-Factory/commit/b7a9bddd87d258c343d17abbc76e53de9a436dcd) และ Issue #7 ปิดเป็น `completed`; ไม่มีการ Deploy
- 2026-10-20: เปิด [Issue #9](https://github.com/porntaned/ERP-for-Factory/issues/9) และ owner-review [PR #10](https://github.com/porntaned/ERP-for-Factory/pull/10) สำหรับ Warehouse-scoped role grants; [Foundation #28](https://github.com/porntaned/ERP-for-Factory/actions/runs/39444111594) ผ่าน PostgreSQL 18.6, fresh migrations, Ruff และ 174 tests และ Independent Scrutinize ได้ verdict `ship`; PR ยังเปิดรอเจ้าของตรวจและไม่มีการ Merge หรือ Deploy
- 2026-10-20: เจ้าของตรวจและอนุมัติ Merge [PR #10](https://github.com/porntaned/ERP-for-Factory/pull/10) เข้า `main` ที่ [`6f6e06b`](https://github.com/porntaned/ERP-for-Factory/commit/6f6e06b); [Issue #9](https://github.com/porntaned/ERP-for-Factory/issues/9) ปิดเป็น `completed` และไม่มีการ Deploy
- 2026-10-20: เริ่ม M3.3 ด้วย [Issue #11](https://github.com/porntaned/ERP-for-Factory/issues/11) และ branch `codex/audit-release-hold`; Independent scope agents พบว่าห้ามใช้สถานะกลางบน Lot เพราะสิทธิ์เป็น Warehouse-scoped จึงล็อก Contract เป็น typed append-only HOLD/RELEASED history ต่อคู่ Lot–Warehouse — [Scope review](reviews/issue-11-scope-independent-review.md)
- 2026-10-20: [Foundation #35](https://github.com/porntaned/ERP-for-Factory/actions/runs/39452581694) ที่ [`78b2a8a`](https://github.com/porntaned/ERP-for-Factory/commit/78b2a8a8a00537ba70b9894e7443ddf792d91ee8) ยืนยัน PostgreSQL 18.6, checks, migrations และ Ruff ผ่าน; 174 regression tests ผ่านและ 70 Quality tests เป็น controlled RED หลัง Independent Agent ตรวจและยืนยัน verdict `ship` — [หลักฐาน](evidence/issue-11-tdd-red.md)
- 2026-10-21: ปิดงานส่งมอบเฉพาะ M3.3.3 โดยยืนยันโค้ดที่ [`825b34f`](https://github.com/porntaned/ERP-for-Factory/commit/825b34fea7ad16605210ef4760a41627f0965c06), บันทึก Implementer/Handoff และเชื่อม CI เดิม [Foundation #38](https://github.com/porntaned/ERP-for-Factory/actions/runs/39454155496); Ruff และ Django check ในเครื่องผ่าน — [Handoff](assignments/issue-11-lot-disposition-audit.md#m333-implementation-handoff) ส่วน M3.3.4–M3.3.5 คงค้างตามขอบเขตที่เจ้าของกำหนด
- 2026-10-21: เจ้าของอนุมัติทำ M3.3.4; ตรวจ checkout SHA, environment, commands และ logs ของ [Foundation #39](https://github.com/porntaned/ERP-for-Factory/actions/runs/39526993055) ที่ `7ce4ef84570628234d4097e0b95643bbf38880db`: PostgreSQL 18.6, fresh migrations, Django checks, Ruff และ `244 passed in 2.71s`; บันทึก [GREEN evidence](evidence/issue-11-green.md) และเช็กเฉพาะ M3.3.4 ส่วน M3.3.5 ยังไม่เริ่ม
- 2026-10-21: เริ่ม M3.3.5 ด้วย Agent อิสระ `/root/m335_independent_review`; พบ event order, stale authorization และ parent reassignment จึงแก้ที่ `6253fd2` พร้อม 17 regressions และแก้ fixture ที่ `44b466f`; [Foundation #42](https://github.com/porntaned/ERP-for-Factory/actions/runs/39528381765) ผ่าน `261 passed in 4.54s` บน PostgreSQL 18.6, re-review exact SHA ได้ verdict `ship` — [Review](reviews/issue-11-lot-disposition-independent-review.md); รอเปิด PR
- 2026-10-21: เปิด owner-review [PR #12](https://github.com/porntaned/ERP-for-Factory/pull/12) จาก `codex/audit-release-hold` ไป `main` ผ่าน GitHub UI หลัง connector ไม่มีสิทธิ์สร้าง PR; เช็ก M3.3.5 และบันทึก [ภาพหลักฐาน](evidence/issue-11-pr.jpg); Issue #11 ยังเปิดและยังไม่มีการ Merge/Deploy
