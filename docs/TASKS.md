# Project checklist — รายการงานโครงการ

อัปเดตล่าสุด: 2026-10-23

`[x]` หมายถึงงานเสร็จและมีหลักฐานที่ลิงก์ไว้ ส่วนงานที่กำลังทำ ติดขัด หรือยังไม่ได้ตรวจรับใช้ `[ ]` งานใหญ่เสร็จเมื่อทุกงานย่อยและเกณฑ์ตรวจรับเสร็จเท่านั้น

## สถานะปัจจุบัน

[PR #12](https://github.com/porntaned/ERP-for-Factory/pull/12) Merge เข้า main ที่ `9b1d182eb6867b70f076e95a63dc03f1814f00ec` แล้ว; Issue #11 ปิด ผล [Audit หลัง Merge](https://github.com/porntaned/ERP-for-Factory/blob/codex/project-audit-after-pr12/docs/reviews/project-audit-after-pr12.md) ทั้ง 5 Finding แก้และ Merge แล้วตามหลักฐานด้านล่าง การตรวจรับ M3 ก่อน Inventory ยังเป็นขั้นตอนแยก

Finding 1 เสร็จแล้ว: เจ้าของ Merge [PR #14](https://github.com/porntaned/ERP-for-Factory/pull/14) เข้า `main` ที่ `eba63622495c6b065ad0abcd8e652676f9189d20` และ [Issue #13](https://github.com/porntaned/ERP-for-Factory/issues/13) ปิดแล้ว

Finding 2 เสร็จแล้ว: เจ้าของอนุญาตให้ Merge [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16) เข้า `main` ที่ `c62687b7ed60515de9424e69fe22ef43bbdfe81e`; [Issue #15](https://github.com/porntaned/ERP-for-Factory/issues/15) ปิดเป็น completed — [หลักฐาน Merge](evidence/issue-15-unsaved-user-policy.md#owner-authorized-merge), [Independent review](reviews/issue-15-unsaved-user-policy-independent-review.md) และ [PR #17](https://github.com/porntaned/ERP-for-Factory/pull/17) บันทึกสถานะ Merge แล้ว ไม่มีการ Deploy

Finding 3 เสร็จแล้ว: เจ้าของตรวจและอนุญาตให้ Merge [PR #19](https://github.com/porntaned/ERP-for-Factory/pull/19) เข้า `main` ที่ `95d612bc41b4bda184598ba30f7072c4896f976d`; [Issue #18](https://github.com/porntaned/ERP-for-Factory/issues/18) ปิดเป็น completed — [หลักฐาน Merge](evidence/issue-18-event-identity.md#owner-authorized-merge), [Independent review](reviews/issue-18-event-identity-independent-review.md) ไม่มีการ Deploy

Finding 4 เสร็จแล้ว: เจ้าของอนุญาตให้ Merge [PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21) เข้า `main` ที่ `a294080133cc31ee6ce0b0e1fc808280d669f203`; [Issue #20](https://github.com/porntaned/ERP-for-Factory/issues/20) ปิดเป็น completed และ [actual main push CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39724957324) ผ่าน PostgreSQL 18.6 / 281 tests — [หลักฐาน](evidence/issue-20-ci-triggers.md#owner-authorized-merge-and-main-push) ไม่มีการ Deploy

Finding 5 เสร็จแล้ว: เจ้าของอนุญาตให้ Merge [PR #23](https://github.com/porntaned/ERP-for-Factory/pull/23) เข้า `main` ที่ `e6cd22c9bddd533b40d293dbad509076ae41172c`; [Issue #22](https://github.com/porntaned/ERP-for-Factory/issues/22) ปิดเป็น completed — [หลักฐาน Merge](evidence/issue-22-readme-status.md#owner-authorized-merge), [main CI 281 passed](https://github.com/porntaned/ERP-for-Factory/actions/runs/39754340827) ไม่มีการ Deploy

เจ้าของตรวจรับ M3 และอนุมัติ Merge [PR #25](https://github.com/porntaned/ERP-for-Factory/pull/25) ที่ `e806b6491d962f8124cc17d902eca2a692485ad1`; [Issue #24](https://github.com/porntaned/ERP-for-Factory/issues/24) ปิด completed แล้ว — [Matrix/ข้อจำกัด](evidence/issue-24-m3-readiness.md), [Independent review](reviews/issue-24-m3-readiness-independent-review.md), [Merge addendum](evidence/issue-24-m3-readiness.md#owner-authorized-merge).

M4.1 เสร็จและเจ้าของ Merge [PR #27](https://github.com/porntaned/ERP-for-Factory/pull/27) เข้า `main` ที่ `a8c93fc461ab4115b69b4c5082f7f31e657ca865`; [Issue #26](https://github.com/porntaned/ERP-for-Factory/issues/26) ปิด completed — [หลักฐานหลัง Merge](evidence/issue-26-stock-ledger.md#owner-merge-and-main-push-ci), [Independent source review](reviews/issue-26-stock-ledger-independent-review.md), [main CI: 121 targeted / 402 full passed](https://github.com/porntaned/ERP-for-Factory/actions/runs/39892983263) M4.2 เสร็จและเจ้าของอนุมัติ Merge [PR #30](https://github.com/porntaned/ERP-for-Factory/pull/30) ที่ `5701d51dfe48558c6dab21e1e3525de3291b452e`; [Issue #29](https://github.com/porntaned/ERP-for-Factory/issues/29) ปิด completed — [หลักฐานหลัง Merge](evidence/issue-29-stock-receipt.md#owner-authorized-merge-and-main-push), [main CI: 87 receipt / 489 full passed](https://github.com/porntaned/ERP-for-Factory/actions/runs/39910705968); ส่งมอบนิยามข้อมูล M4.3.1 ใน [Issue #32](https://github.com/porntaned/ERP-for-Factory/issues/32) — [สัญญา](assignments/issue-32-transfer-definition.md); main มีคำสั่งโอนภายในแล้วหลัง PR #37; ส่งมอบ Quality gate M4.3.3 ใน [Issue #34](https://github.com/porntaned/ERP-for-Factory/issues/34); ส่งมอบ M4.3.4 และสิทธิ์ขั้นต่ำ M4.3.2 ใน [Issue #36](https://github.com/porntaned/ERP-for-Factory/issues/36); M4.3.5 และ M4.3.6 Merge แล้วใน [PR #39](https://github.com/porntaned/ERP-for-Factory/pull/39) และ [PR #43](https://github.com/porntaned/ERP-for-Factory/pull/43); กำลังตรวจรับ M4.3.7; M4.4–M4.7 ยังไม่เสร็จ และไม่มีการ Deploy

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

- [x] **M3 — ข้อมูลหลักพร้อมสำหรับ Inventory** — เจ้าของตรวจรับและ Merge [PR #25](https://github.com/porntaned/ERP-for-Factory/pull/25), [หลักฐาน/ขอบเขต](evidence/issue-24-m3-readiness.md#owner-authorized-merge)
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
  - [x] M3.4 แยก Issue, Test, Review และ PR สำหรับแต่ละส่วน — [Matrix ของงานที่ส่งมอบแล้ว](evidence/issue-24-m3-readiness.md#m3-acceptance-matrix); ตรวจจากหลักฐานเดิม ไม่ทำ implementation ซ้ำ

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
- [x] PA.5 Finding 3: explicit high event ID — [PR #19 Merge แล้ว](https://github.com/porntaned/ERP-for-Factory/pull/19), [หลักฐาน](evidence/issue-18-event-identity.md#owner-authorized-merge)
  - [x] เปิด Issue และล็อก Scope — [Issue #18](https://github.com/porntaned/ERP-for-Factory/issues/18), [Assignment](assignments/issue-18-event-identity.md)
  - [x] พิสูจน์ PostgreSQL RED/GREEN รวม migration upgrade/reverse/reapply และ regression — [หลักฐาน](evidence/issue-18-event-identity.md)
  - [x] Independent Scrutinize — [Review](reviews/issue-18-event-identity-independent-review.md), verdict `ship` ที่ `1c19981778b2f1cd45279de1b30945523d5827e0`
  - [x] เปิด PR ให้เจ้าของตรวจ — [PR #19](https://github.com/porntaned/ERP-for-Factory/pull/19), [ภาพหลักฐาน](evidence/issue-18-pr.jpg)
  - [x] เจ้าของตรวจรับและ Merge Finding 3 — [Commit `95d612b`](https://github.com/porntaned/ERP-for-Factory/commit/95d612bc41b4bda184598ba30f7072c4896f976d), [Issue #18 ปิด](https://github.com/porntaned/ERP-for-Factory/issues/18)
- [x] PA.6 Finding 4: CI trigger ทั่วไป — [Issue #20 ปิด](https://github.com/porntaned/ERP-for-Factory/issues/20), [หลักฐาน Merge/main push](evidence/issue-20-ci-triggers.md#owner-authorized-merge-and-main-push)
  - [x] เปลี่ยน push filter และพิสูจน์ nested codex/feat events — [หลักฐาน](evidence/issue-20-ci-triggers.md)
  - [x] Independent Scrutinize ก่อน PR — [Review](reviews/issue-20-ci-triggers-independent-review.md), `ship` ที่ `56a0d80f05250751b3e5025b1c28ec5f6137d60c`
  - [x] เปิด PR และตรวจ actual pull_request event — [PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21), [หลักฐาน](evidence/issue-20-ci-triggers.md#owner-review-pr-and-actual-pr-event)
  - [x] เจ้าของตรวจรับและ Merge; ตรวจ actual main push หลัง Merge — [PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21), [main CI 281 passed](https://github.com/porntaned/ERP-for-Factory/actions/runs/39724957324)
- [x] PA.7 Finding 5: README status — [Issue #22 ปิด](https://github.com/porntaned/ERP-for-Factory/issues/22), [หลักฐาน Merge](evidence/issue-22-readme-status.md#owner-authorized-merge)
  - [x] แก้สถานะ README และตรวจ Markdown/rendered links — [หลักฐาน](evidence/issue-22-readme-status.md)
  - [x] Independent Scrutinize — [Review](reviews/issue-22-readme-status-independent-review.md), `ship` ที่ `cf9f010d212261ddc2e2c8a23bc60dfdc18ebf7b`
  - [x] เปิด PR ให้เจ้าของตรวจ — [PR #23](https://github.com/porntaned/ERP-for-Factory/pull/23), [ภาพหลักฐาน](evidence/issue-22-pr.jpg)
  - [x] เจ้าของตรวจรับและ Merge Finding 5 — [PR #23](https://github.com/porntaned/ERP-for-Factory/pull/23), [main CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39754340827)

## M4 — Inventory MVP

- [ ] **M4 — รับเข้า โอน และดูประวัติผ่านหน้าจอได้**
  - [x] M4.1 สร้าง Stock ledger และกฎป้องกันยอดติดลบ — [PR #27 Merge แล้ว](https://github.com/porntaned/ERP-for-Factory/pull/27), [Issue #26 completed](https://github.com/porntaned/ERP-for-Factory/issues/26), [หลักฐานหลัง Merge](evidence/issue-26-stock-ledger.md#owner-merge-and-main-push-ci)
  - [x] M4.2 รับวัตถุดิบจำลองพร้อม Lot, สิทธิ์และ Audit — [PR #30 Merge แล้ว](https://github.com/porntaned/ERP-for-Factory/pull/30), [Issue #29 completed](https://github.com/porntaned/ERP-for-Factory/issues/29), [หลักฐานหลัง Merge](evidence/issue-29-stock-receipt.md#owner-authorized-merge-and-main-push), [Independent source review: ship](reviews/issue-29-stock-receipt-independent-review.md)
  - [ ] M4.3 โอนระหว่างคลังใน Plant เดียวกัน
    - [x] M4.3.1 กำหนด Lot, คลังต้นทาง–ปลายทาง, จำนวนและเหตุผล ห้ามคลังเดิม/ข้าม Plant — [Issue #32](https://github.com/porntaned/ERP-for-Factory/issues/32), [สัญญาและตัวอย่าง](assignments/issue-32-transfer-definition.md); ส่งมอบเอกสารใน [PR #33](https://github.com/porntaned/ERP-for-Factory/pull/33) เจ้าของอนุมัติ Merge แล้ว (ไม่ใช่ระบบโอนที่ทำงานได้)
    - [x] M4.3.2 กำหนดและตรวจสิทธิ์สำหรับคลังทั้งสอง — เจ้าของเลือก active actor + WAREHOUSE ทั้งสองคลัง; รวมการตรวจขั้นต่ำใน [Issue #36](https://github.com/porntaned/ERP-for-Factory/issues/36); [66 targeted / 591 full ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39979297426); เจ้าของอนุมัติ Merge [PR #37](https://github.com/porntaned/ERP-for-Factory/pull/37); [main CI ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39980301308)
    - [x] M4.3.3 กำหนดและบังคับ Quality eligibility ต้นทาง/ปลายทาง — เจ้าของเลือกต้นทาง RELEASED และคงสถานะปลายทาง; [Issue #34](https://github.com/porntaned/ERP-for-Factory/issues/34), [ขอบเขต/หลักฐาน](assignments/m433-transfer-quality-policy.md); [PostgreSQL: 36 targeted / 525 full ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39975578596); เจ้าของอนุมัติ Merge [PR #35](https://github.com/porntaned/ERP-for-Factory/pull/35) ที่ `b4b44579352a490e1432783e1a34d571b6bf37ac`; [main CI ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39976575083)
    - [x] M4.3.4 หักต้นทางและเพิ่มปลายทางแบบ atomic พร้อมป้องกันยอดติดลบ — [Issue #36](https://github.com/porntaned/ERP-for-Factory/issues/36), [ขอบเขต/หลักฐาน](assignments/m434-atomic-transfer.md); [PostgreSQL: 66 targeted / 591 full ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39979297426); เจ้าของอนุมัติ Merge [PR #37](https://github.com/porntaned/ERP-for-Factory/pull/37) ที่ `0df0923b293a889dc2ca5316062d5350f7e60a9a`; [main CI ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39980301308)
    - [x] M4.3.5 เก็บประวัติและเชื่อม ledger ทั้งสองฝั่งกับรายการโอน — [Issue #38](https://github.com/porntaned/ERP-for-Factory/issues/38), [ขอบเขต/หลักฐาน](assignments/m435-transfer-history.md); [PostgreSQL: 29 targeted / 620 full ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39981798189); เจ้าของอนุมัติ Merge [PR #39](https://github.com/porntaned/ERP-for-Factory/pull/39) ที่ `3d876cc129f9f889b636926b40798423a53d31f1`; [main CI ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/39983366988)
    - [x] M4.3.6 ป้องกันคำขอโอนซ้ำและรายการโอนชนกัน — [Issue #42](https://github.com/porntaned/ERP-for-Factory/issues/42), [ขอบเขต/หลักฐาน](assignments/m436-transfer-requests.md); เจ้าของเลือก UUID + exact replay/current authorization; [PostgreSQL: 22 targeted / 642 full ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/40066789351); เจ้าของอนุมัติ Merge [PR #43](https://github.com/porntaned/ERP-for-Factory/pull/43) ที่ `e8ad707b86f7c613c3db291fd6dcabd3f491a569`; [main CI ผ่าน](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067226064); ไม่ถือว่า M4.4 เสร็จ
    - [ ] M4.3.7 ทดสอบเส้นทางโอนจริงบน PostgreSQL และ independent review ก่อน PR — [Issue #44](https://github.com/porntaned/ERP-for-Factory/issues/44); [ขอบเขต/หลักฐาน](assignments/m437-transfer-readiness.md); [PostgreSQL CI #133](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067756440) ผ่าน 2 workflow / 644 full; [Independent source review: ship](reviews/m437-transfer-independent-review.md); รอ owner acceptance/Merge
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

- 2026-10-24: M4.3.7 เพิ่มเฉพาะ integration test รับเข้า → Quality release → โอน → ประวัติ/UUID replay/current authorization; [commit ที่ทดสอบ](https://github.com/porntaned/ERP-for-Factory/commit/c62dc81a9cf4a2a19b2975582dcbd49a3565eec6) ผ่าน [PostgreSQL CI #133](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067756440) 2 workflow / 644 full — [หลักฐานและสถานะตรวจอิสระ](assignments/m437-transfer-readiness.md); แก้สถานะ M4.3.5/M4.3.6 ตาม Merge PR #39/#43 แล้ว ไม่มี Merge PR #41, M4.4, UI หรือ Deploy

- 2026-10-24: M4.3.6 ใน [Issue #42](https://github.com/porntaned/ERP-for-Factory/issues/42) เพิ่ม UUID request identity, exact replay/current authorization, conflict และ losing-write rollback ตามเจ้าของอนุมัติ; [commit ที่ทดสอบ](https://github.com/porntaned/ERP-for-Factory/commit/1cddc7a461bb7a51cf84e1841db225f12b77e6c6) ผ่าน [PostgreSQL CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/40066789351) 22 targeted / 642 full — [หลักฐาน/self-review](assignments/m436-transfer-requests.md) รอ owner review; ไม่ Merge PR #41, ไม่เริ่ม UI/M4.3.7 และไม่มี Deploy


- 2026-10-23: M4.3.5 ใน [Issue #38](https://github.com/porntaned/ERP-for-Factory/issues/38) เพิ่ม StockTransfer เชื่อม immutable ledger สองฝั่งพร้อม DB identity/time; [commit ที่ทดสอบ](https://github.com/porntaned/ERP-for-Factory/commit/fb3de5ea7a60b41a38036b92d2e0c4c3980090c5) ผ่าน [PostgreSQL CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39981798189) 29 targeted / 620 full — [หลักฐาน/self-review/ข้อจำกัด](assignments/m435-transfer-history.md) รอ owner review; ไม่เดาคู่รายการเก่า ไม่เริ่ม idempotency/UI และไม่มี Merge/Deploy
- 2026-10-23: เจ้าของอนุมัติ Merge M4.3.4 และสิทธิ์ขั้นต่ำ M4.3.2 ใน [PR #37](https://github.com/porntaned/ERP-for-Factory/pull/37) ที่ `0df0923b293a889dc2ca5316062d5350f7e60a9a`; Issue #36 completed และ [main CI #120](https://github.com/porntaned/ERP-for-Factory/actions/runs/39980301308) ผ่าน จึงปรับ checklist ตามหลักฐานจริง


- 2026-10-23: M4.3.4 และสิทธิ์ขั้นต่ำ M4.3.2 ใน [Issue #36](https://github.com/porntaned/ERP-for-Factory/issues/36) ใช้ active actor + WAREHOUSE ทั้งสองคลังตามเจ้าของเลือก; [application commit](https://github.com/porntaned/ERP-for-Factory/commit/99f96d7c7a0b266400e53a3bc12847ffa8774312) ผ่าน [PostgreSQL CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39979297426) 66 targeted / 591 full — [หลักฐาน/self-review/ข้อจำกัด](assignments/m434-atomic-transfer.md) รอ owner review; ยังไม่มี persistent transfer linkage, idempotency, UI, Merge หรือ Deploy
- 2026-10-23: เจ้าของอนุมัติ Merge M4.3.3 ใน [PR #35](https://github.com/porntaned/ERP-for-Factory/pull/35) ที่ `b4b44579352a490e1432783e1a34d571b6bf37ac`; Issue #34 completed และ [main CI #116](https://github.com/porntaned/ERP-for-Factory/actions/runs/39976575083) ผ่าน จึงปรับ checklist M4.3.3 ตามหลักฐานจริง


- 2026-10-23: ทำเฉพาะ Quality gate M4.3.3 ตามนโยบายที่เจ้าของเลือกใน [Issue #34](https://github.com/porntaned/ERP-for-Factory/issues/34): ต้นทาง RELEASED, ปลายทางคงสถานะเดิม; [CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39975578596) ผ่าน 36 targeted / 525 full บน PostgreSQL 18.6 — [ขอบเขต/หลักฐาน/self-review](assignments/m433-transfer-quality-policy.md) รอตรวจรับ ไม่มีคำสั่งโอนจริง, Merge หรือ Deploy


- 2026-10-23: เจ้าของสั่งเฉพาะ M4.3.1 เปิด [Issue #32](https://github.com/porntaned/ERP-for-Factory/issues/32) เพื่อกำหนดข้อมูลการโอนและตัวอย่างตรวจรับ — [สัญญา/ขอบเขต](assignments/issue-32-transfer-definition.md) เอกสารเท่านั้น [commit หลักฐาน](https://github.com/porntaned/ERP-for-Factory/commit/99486ddd7dbb94ff31735a223db1f6a02c520e82) / [PR #33](https://github.com/porntaned/ERP-for-Factory/pull/33); เจ้าของอนุมัติส่งมอบและ Merge โดยรอ CI ผ่าน ไม่เริ่มกฎสิทธิ์/Quality, implementation, UI หรือ Deploy
- 2026-10-23: เจ้าของอนุมัติ Merge [PR #30](https://github.com/porntaned/ERP-for-Factory/pull/30) ที่ `5701d51dfe48558c6dab21e1e3525de3291b452e`; Issue #29 ปิด completed ตรวจ [main CI หลัง Merge](https://github.com/porntaned/ERP-for-Factory/actions/runs/39910705968) ผ่าน PostgreSQL 18.6: 87 receipt / 489 full tests และปรับ M4.2 เป็นเสร็จตาม [หลักฐานจริง](evidence/issue-29-stock-receipt.md#owner-authorized-merge-and-main-push) งานรอบนี้ปรับเอกสารเท่านั้น ไม่เริ่ม M4.3 และไม่มี Deploy
- 2026-10-23: เจ้าของอนุมัติ M4.2 และกฎ 3 ข้อ เปิด [Issue #29](https://github.com/porntaned/ERP-for-Factory/issues/29); ใช้ Agent ตรวจสัญญา/เขียน tests/ตรวจ source อิสระ [CI implementation](https://github.com/porntaned/ERP-for-Factory/actions/runs/39909020029) ที่ `0a96eda` ผ่าน PostgreSQL 18.6: 87 receipt / 489 full tests และ Independent source review ให้ ship — [หลักฐาน](evidence/issue-29-stock-receipt.md) M4.2 ยังไม่เช็กเสร็จจนกว่าเจ้าของ Merge ไม่มี UI/การโอน/Deploy
- 2026-10-23: ตรวจ Git/GitHub/CI จริงหลังเจ้าของ Merge PR #27 ที่ `a8c93fc461ab4115b69b4c5082f7f31e657ca865`; Issue #26 ปิด completed และปรับ checklist 5 ข้อตามหลักฐานแล้ว [main push CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39892983263/job/120216811092) ผ่าน PostgreSQL 18.6: 121 targeted / 402 full tests ปรับเฉพาะเอกสารสถานะและหลักฐาน พร้อมข้อเสนอ M4.2 ที่ยังไม่อนุมัติ ไม่ทำ implementation ซ้ำ ไม่มีการ Merge หรือ Deploy ในรอบนี้
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
