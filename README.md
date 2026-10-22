# ERP for Factory

Portfolio ERP สำหรับโรงงานประกอบโคมไฟ LED จำลอง พัฒนาเป็นขั้นเล็ก ๆ ที่ตรวจสอบย้อนหลังได้ผ่าน GitHub Issues, Tests, Reviews และ Pull Requests

โครงการมีผลลัพธ์หลักสองส่วน: ระบบ ERP ที่ทำงานได้ตาม Scope และหลักฐานว่า Multi-Agent สามารถแบ่งงาน ส่งต่องาน ตรวจสอบอิสระ และควบคุมคุณภาพได้จริง

> สถานะอ้างอิง `main` วันที่ 2026-10-22: Foundation `Organization → Plant → Warehouse`, [Item/UOM](https://github.com/porntaned/ERP-for-Factory/pull/6), [Lot identity](https://github.com/porntaned/ERP-for-Factory/pull/8), [สิทธิ์ตามบทบาท/คลัง](https://github.com/porntaned/ERP-for-Factory/pull/10) และ [ประวัติ Quality Hold/Release](https://github.com/porntaned/ERP-for-Factory/pull/12) Merge แล้ว รวมถึง Audit Findings 1–4; [main CI หลัง PR #21](https://github.com/porntaned/ERP-for-Factory/actions/runs/39724957324) ที่ commit `a294080` ผ่าน PostgreSQL 18.6 และ 281 tests พร้อม Django checks, migrations และ Ruff ดู [หลักฐาน Finding 4](docs/evidence/issue-20-ci-triggers.md#owner-authorized-merge-and-main-push) และ [Checklist/งานที่ยังไม่ตรวจรับ](docs/TASKS.md) สำหรับสถานะล่าสุด ส่วนงานเอกสาร Finding 5 ติดตามใน [Issue #22](https://github.com/porntaned/ERP-for-Factory/issues/22); Stock ledger/movement, หน้าจอ Inventory และการตรวจคุณภาพเต็มรูปแบบยังไม่ส่งมอบ และยังไม่มีการ Deploy

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
