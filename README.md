# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

โครงการมีผลลัพธ์หลักสองส่วน: ระบบ ERP ที่ทำงานได้ตาม Scope และหลักฐานว่า Multi-Agent สามารถแบ่งงาน ส่งต่องาน ตรวจสอบอิสระ และควบคุมคุณภาพได้จริง

> สถานะอ้างอิง `main` วันที่ 2026-10-23: Foundation `Organization → Plant → Warehouse`, Item/UOM, Lot identity, สิทธิ์ตามบทบาท/คลัง และประวัติ Quality Hold/Release Merge แล้ว รวมถึง Audit Findings 1–5 และ [การตรวจรับ M3](https://github.com/porntaned/ERP-for-Factory/pull/25) ล่าสุด [M4.1 Stock ledger](https://github.com/porntaned/ERP-for-Factory/pull/27) Merge ที่ `a8c93fc461ab4115b69b4c5082f7f31e657ca865` และ [Issue #26](https://github.com/porntaned/ERP-for-Factory/issues/26) ปิด completed; [main CI หลัง Merge](https://github.com/porntaned/ERP-for-Factory/actions/runs/39892983263) ผ่าน PostgreSQL 18.6: 121 targeted / 402 full tests พร้อม Django checks, migrations และ Ruff — [หลักฐาน](docs/evidence/issue-26-stock-ledger.md#owner-merge-and-main-push-ci), [Checklist](docs/TASKS.md) งานรับเข้า/โอนผ่าน business commands, หน้าจอ Inventory และการตรวจคุณภาพเต็มรูปแบบยังไม่ส่งมอบ M4.2 ยังเป็นเพียง [ข้อเสนอรอพิจารณา](docs/proposals/m4.2-synthetic-receipt.md) และยังไม่มีการ Deploy

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
