# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

> สถานะปัจจุบัน: เอกสารตั้งต้นและ Foundation Issue พร้อมแล้ว ยังไม่มี Application code หรือฟังก์ชัน Stock ที่ผ่านการตรวจรับ

## First issue

[Issue #1 — Organization, Plant and Warehouse constraints](https://github.com/porntaned/ERP-for-Factory/issues/1) จะสร้างฐานข้อมูล `Organization → Plant → Warehouse` ด้วย Django และ PostgreSQL พร้อมพิสูจน์ข้อจำกัดที่ระดับฐานข้อมูลก่อนเริ่ม Stock movement

## Planned stack

- Django modular monolith
- PostgreSQL
- Django Templates and Bootstrap for the first UI
- pytest, pytest-django and Ruff
- GitHub Actions

## Project evidence

- [Project brief](docs/PROJECT.md)
- [Project checklist / สถานะงาน](docs/TASKS.md)
- [Scrutinize review method](docs/SCRUTINIZE.md)
- [Agent and repository rules](AGENTS.md)

## Safety and scope

Repository นี้เป็น Public และใช้ข้อมูลจำลองเท่านั้น ห้ามเพิ่ม Password, Token, Personal data หรือข้อมูลโรงงานจริง การผ่าน Foundation หมายถึงพิสูจน์เฉพาะ Schema ที่ระบุ ไม่ได้หมายถึงพร้อมใช้งานจริงในโรงงาน

เจ้าของ Repository เป็นผู้ตรวจและตัดสินใจ Merge หรือ Deploy
