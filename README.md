# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

โครงการมีผลลัพธ์หลักสองส่วน: ระบบ ERP ที่ทำงานได้ตาม Scope และหลักฐานว่า Multi-Agent สามารถแบ่งงาน ส่งต่องาน ตรวจสอบอิสระ และควบคุมคุณภาพได้จริง

> **สถานะ:** ดูที่ [Checklist — สถานะปัจจุบัน](docs/TASKS.md#สถานะปัจจุบัน) ซึ่งเป็นแหล่งเดียวของสถานะงาน (README ไม่ระบุ commit SHA เพื่อไม่ให้ล้าสมัย)
>
> **ส่งมอบแล้ว:** Foundation, Item/UOM, Lot, สิทธิ์ตามบทบาท/คลัง, Quality Hold/Release และ Inventory M4.1–M4.4 (ledger, รับเข้า, โอนใน Plant เดียวกัน, กันคำขอซ้ำ/concurrency และทะเบียน request key ข้ามคำสั่ง) ทั้งหมดเป็นคำสั่งภายใน
>
> **ยังไม่ส่งมอบ:** Reversal (M4.5), หน้าจอ Inventory (M4.6), เดโม (M4.7), Manufacturing (M5), Inspection/Traceability (M6), Portfolio delivery (M7) และไม่มีการ Deploy

## Stack

- Django 5.2 LTS modular monolith (`facilities`, `catalog`, `access_control`, `inventory`, `quality`)
- PostgreSQL 18.6 เป็นฐานข้อมูลหลัก กฎสำคัญบังคับด้วย constraint และ trigger
- pytest, pytest-django และ Ruff บน GitHub Actions
- หน้าจอ: Django Templates และ Bootstrap (ยังไม่ส่งมอบ ดู M4.6)

## Run locally

ต้องมี PostgreSQL 18.6 และ [uv](https://docs.astral.sh/uv/) ขั้นตอนเต็ม เวอร์ชัน และค่าตั้งค่าอยู่ใน [Development and test environment](docs/DEVELOPMENT.md)

```bash
cp .env.example .env   # แก้ทุกค่าใน .env ก่อน
uv sync --locked --all-groups
uv run --env-file .env python manage.py migrate
uv run --env-file .env pytest
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
