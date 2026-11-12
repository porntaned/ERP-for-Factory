# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

โครงการมีผลลัพธ์หลักสองส่วน: ระบบ ERP ที่ทำงานได้ตาม Scope และหลักฐานว่า Multi-Agent สามารถแบ่งงาน ส่งต่องาน ตรวจสอบอิสระ และควบคุมคุณภาพได้จริง

> **สถานะ:** ดูที่ [Checklist — สถานะปัจจุบัน](docs/TASKS.md#สถานะปัจจุบัน) ซึ่งเป็นแหล่งเดียวของสถานะงาน (README ไม่ระบุ commit SHA เพื่อไม่ให้ล้าสมัย)
>
> **ส่งมอบแล้ว:** Foundation, Item/UOM, Lot, สิทธิ์ตามบทบาท/คลัง, Quality Hold/Release (inspection M6.1 และห้ามใช้ Lot ที่ REJECTED ทุกคลัง M6.2), ค้นย้อน Lot ทุกชั้น (M6.3), ทดสอบจำนวน/concurrency และหน้าประวัติ QC `/quality/audit/` (M6.4) และ Inventory M4.1–M4.5 (ledger, รับเข้า, โอนใน Plant เดียวกัน, กันคำขอซ้ำ/concurrency, ทะเบียน request key ข้ามคำสั่ง และ Reversal ที่อ้างรายการต้นฉบับ) และหน้าจอ M4.6 สำหรับรับเข้า โอน ประวัติ และกลับรายการ ตามสิทธิ์ผู้ใช้ พร้อม admin อ่านอย่างเดียวและข้อมูลจำลอง `seed_demo` (M7.1) และเดโม M4.7 รับเข้า 100 → โอน 30 → คงเหลือ 70/30 ([วิธีเดินเดโม](docs/DEVELOPMENT.md#inventory-demo-walkthrough-m47)) และ Manufacturing M5 (M5.1–M5.5): BOM แบบมีเวอร์ชันที่ต้องอนุมัติ, Production order, เบิก/คืน/ใช้วัตถุดิบ, scrap, รับผลผลิตเข้า FG (HOLD) และปิด order ผ่านคำสั่ง Inventory พร้อมความเชื่อมโยง Lot วัตถุดิบ ↔ ผลผลิต, การกลับรายการผลิต (M5.2c) และเหตุผลเมื่อปิด order ที่ผลผลิตขาด และเดโมการผลิตครบเส้นทาง `seed_production_demo` (M5.4), หน้าจอการผลิตบนเว็บ (M5.5) และกฎยกเลิก order ได้เฉพาะเมื่อยังไม่มีผลผลิตสุทธิ; Quality M6.1 (คำสั่งและหน้าเว็บ `/quality/`): บันทึกตรวจ Lot (INCOMING/FINAL) เป็นทางเดียวที่ปล่อย (RELEASED) หรือปฏิเสธ (REJECTED) และ APPROVER ส่ง Lot ที่ REJECTED กลับ HOLD (ข้อความเดิม "หน้าเว็บการตรวจยังไม่ส่งมอบ" ผิดตั้งแต่ M6.1 PR 2 [PR #101](https://github.com/porntaned/ERP-for-Factory/pull/101) — historical, แก้ 2026-11-11)
>
> **ยังไม่ส่งมอบ:** Portfolio delivery (M7.2–M7.5) และไม่มีการ Deploy

## Stack

- Django 5.2 LTS modular monolith (`facilities`, `catalog`, `access_control`, `inventory`, `quality`, `manufacturing`, `demo`)
- PostgreSQL 18.6 เป็นฐานข้อมูลหลัก กฎสำคัญบังคับด้วย constraint และ trigger
- pytest, pytest-django และ Ruff บน GitHub Actions
- หน้าจอ: Django Templates และ Bootstrap — login ที่ `/accounts/login/`, ยอดคงเหลือ, รับเข้า, โอน, ประวัติและกลับรายการ แสดงตามสิทธิ์ของผู้ใช้; การผลิต `/production/` (รายการ order, หน้า order, genealogy และฟอร์มสร้าง order / เบิก / คืน / ใช้ / scrap / ผลผลิต / กลับรายการ / ปิด / ยกเลิก order ตามสิทธิ์); Quality `/quality/` (บันทึกตรวจ Lot และส่ง Lot ที่ REJECTED กลับ HOLD ตามสิทธิ์) และประวัติ QC `/quality/audit/` (อ่านอย่างเดียว เฉพาะ QUALITY/APPROVER); ค้นหา Lot `/lots/search/` และค้นย้อน Lot ทุกชั้น `/lots/<id>/trace/` (ผู้ใช้ที่ login); admin อ่านอย่างเดียว (superuser สร้างเองด้วย `createsuperuser`)

## Run locally

ขั้นตอนเต็มอยู่ใน [Install guide](docs/INSTALL.md) (bash): ติดตั้ง Git, uv และ PostgreSQL 18.6 → สร้าง role และ database ด้วย `psql` (role ต้องมี `CREATEDB` เพื่อให้ pytest-django สร้าง test database ได้) → clone → เขียน `.env` จาก `.env.example` → `uv sync --locked --all-groups` → `check` / `migrate` / `pytest` → `seed_demo` / `seed_production_demo` / `set_demo_passwords` → `runserver` แล้ว login เป็นผู้ใช้ `demo-*` ทุกคำสั่งใน guide ถูกรันซ้ำใน CI job `install-guide` บน PostgreSQL 18.6 ยังไม่ได้ทดสอบบน Windows

(ชุดคำสั่งเดิมในส่วนนี้ไม่มี `seed_production_demo` และไม่บอกวิธีสร้าง role/database ที่สร้าง test database ได้ — historical, ย้ายไป [docs/INSTALL.md](docs/INSTALL.md) 2026-11-12)

## Project evidence

- [Project brief and outcomes](docs/PROJECT.md)
- [Multi-Agent execution contract](docs/MULTI_AGENT.md)
- [Project checklist / สถานะงาน](docs/TASKS.md)
- [Scrutinize review method](docs/SCRUTINIZE.md)
- [Agent and repository rules](AGENTS.md) — รวมกติกาการอัปเดตเอกสารหลัง Merge
- [Development and test environment](docs/DEVELOPMENT.md)

## Safety and scope

Repository นี้เป็น Public และใช้ข้อมูลจำลองเท่านั้น ห้ามเพิ่ม Password, Token, Personal data หรือข้อมูลโรงงานจริง การผ่าน Foundation หมายถึงพิสูจน์เฉพาะ Schema ที่ระบุ ไม่ได้หมายถึงพร้อมใช้งานจริงในโรงงาน

การเปลี่ยน `main` ต้องผ่าน Pull Request เจ้าของ Repository เป็นผู้ตรวจและตัดสินใจ Merge หรือ Deploy
