# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

โครงการมีผลลัพธ์หลักสองส่วน: ระบบ ERP ที่ทำงานได้ตาม Scope และหลักฐานว่า Multi-Agent สามารถแบ่งงาน ส่งต่องาน ตรวจสอบอิสระ และควบคุมคุณภาพได้จริง

> **สถานะ:** ดูที่ [Checklist — สถานะปัจจุบัน](docs/TASKS.md#สถานะปัจจุบัน) ซึ่งเป็นแหล่งเดียวของสถานะงาน (README ไม่ระบุ commit SHA เพื่อไม่ให้ล้าสมัย)
>
> **ส่งมอบแล้ว:** Foundation, Item/UOM, Lot, สิทธิ์ตามบทบาท/คลัง, Quality Hold/Release และ Inventory M4.1–M4.5 (ledger, รับเข้า, โอนใน Plant เดียวกัน, กันคำขอซ้ำ/concurrency, ทะเบียน request key ข้ามคำสั่ง และ Reversal ที่อ้างรายการต้นฉบับ) และหน้าจอ M4.6 สำหรับรับเข้า โอน ประวัติ และกลับรายการ ตามสิทธิ์ผู้ใช้ พร้อม admin อ่านอย่างเดียวและข้อมูลจำลอง `seed_demo` (M7.1) และเดโม M4.7 รับเข้า 100 → โอน 30 → คงเหลือ 70/30 ([วิธีเดินเดโม](docs/DEVELOPMENT.md#inventory-demo-walkthrough-m47))
>
> **ยังไม่ส่งมอบ:** Manufacturing (M5), Inspection/Traceability (M6), Portfolio delivery (M7) และไม่มีการ Deploy

## Stack

- Django 5.2 LTS modular monolith (`facilities`, `catalog`, `access_control`, `inventory`, `quality`)
- PostgreSQL 18.6 เป็นฐานข้อมูลหลัก กฎสำคัญบังคับด้วย constraint และ trigger
- pytest, pytest-django และ Ruff บน GitHub Actions
- หน้าจอ: Django Templates และ Bootstrap — login ที่ `/accounts/login/`, ยอดคงเหลือ, รับเข้า, โอน, ประวัติและกลับรายการ แสดงตามสิทธิ์ของผู้ใช้; admin อ่านอย่างเดียว (superuser สร้างเองด้วย `createsuperuser`)

## Run locally

ต้องมี PostgreSQL 18.6 และ [uv](https://docs.astral.sh/uv/) ขั้นตอนเต็ม เวอร์ชัน และค่าตั้งค่าอยู่ใน [Development and test environment](docs/DEVELOPMENT.md)

```bash
cp .env.example .env   # แก้ทุกค่าใน .env ก่อน
uv sync --locked --all-groups
uv run --env-file .env python manage.py migrate
uv run --env-file .env pytest
uv run --env-file .env python manage.py seed_demo      # ข้อมูลจำลอง
uv run --env-file .env python manage.py set_demo_passwords  # รหัสผ่านของ demo-warehouse / demo-quality / demo-approver / demo-production
DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver  # http://127.0.0.1:8000/
```

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
