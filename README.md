# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

โครงการมีผลลัพธ์หลักสองส่วน: ระบบ ERP ที่ทำงานได้ตาม Scope และหลักฐานว่า Multi-Agent สามารถแบ่งงาน ส่งต่องาน ตรวจสอบอิสระ และควบคุมคุณภาพได้จริง

> สถานะอ้างอิง `main` วันที่ 2026-10-24 ที่ `1e8df0bbf9fb4b19be02fb9145f8ec5e8dff3ecc`: Foundation, Item/UOM, Lot identity, สิทธิ์ตามบทบาท/คลัง, ประวัติ Quality Hold/Release, Audit Findings 1–5 และ M3 ตรวจรับแล้ว Inventory ส่งมอบ [M4.1 Stock ledger](https://github.com/porntaned/ERP-for-Factory/pull/27), [M4.2 รับวัตถุดิบจำลอง](https://github.com/porntaned/ERP-for-Factory/pull/30) และ M4.3 โอนระหว่างคลังใน Plant เดียวกันครบ M4.3.1–M4.3.7 (สิทธิ์ทั้งสองคลัง, Quality gate ต้นทาง RELEASED, หักและเพิ่มแบบ atomic, ประวัติ ledger สองฝั่ง, UUID กันคำขอซ้ำ และเทสต์เส้นทางรับเข้า→ปล่อย→โอน; Merge ล่าสุดคือ [PR #45](https://github.com/porntaned/ERP-for-Factory/pull/45)) หลักฐานทดสอบล่าสุดคือ [PostgreSQL CI #133](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067756440) ผ่าน 644 full tests บน PostgreSQL 18.6 — [หลักฐาน M4.3.7](docs/assignments/m437-transfer-readiness.md), [Checklist](docs/TASKS.md) ทั้งหมดเป็นคำสั่งภายใน ยังไม่มี UI/API กลับรายการ (M4.5) การป้องกันซ้ำและ concurrency ระดับรวม (M4.4) หน้าจอ Inventory (M4.6) เดโม (M4.7) และการตรวจคุณภาพเต็มรูปแบบยังไม่ส่งมอบ และไม่มีการ Deploy

## First issue

[Issue #1 — Organization, Plant and Warehouse constraints](https://github.com/porntaned/ERP-for-Factory/issues/1) ส่งมอบฐานข้อมูล `Organization → Plant → Warehouse` ด้วย Django และ PostgreSQL พร้อมหลักฐานข้อจำกัดระดับฐานข้อมูลก่อนเริ่ม Stock movement

## Planned stack

- Django modular monolith
- PostgreSQL
- Django Templates and Bootstrap for the first UI
- pytest, pytest-django and Ruff
- GitHub Actions

## Project evidence

- [Project brief and outcomes](docs/PROJECT.md)
- [Multi-Agent execution contract](docs/MULTI_AGENT.md)
- [Project checklist / สถานะงาน](docs/TASKS.md)
- [Scrutinize review method](docs/SCRUTINIZE.md)
- [Agent and repository rules](AGENTS.md)

## Safety and scope

Repository นี้เป็น Public และใช้ข้อมูลจำลองเท่านั้น ห้ามเพิ่ม Password, Token, Personal data หรือข้อมูลโรงงานจริง การผ่าน Foundation หมายถึงพิสูจน์เฉพาะ Schema ที่ระบุ ไม่ได้หมายถึงพร้อมใช้งานจริงในโรงงาน

การเปลี่ยน `main` ต้องผ่าน Pull Request เจ้าของ Repository เป็นผู้ตรวจและตัดสินใจ Merge หรือ Deploy
