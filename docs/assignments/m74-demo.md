# M7.4 — Demo screenshots with Issue/PR/CI evidence

[Issue #129](https://github.com/porntaned/ERP-for-Factory/issues/129); approval:
[comment 6912041133](https://github.com/porntaned/ERP-for-Factory/issues/129#issuecomment-6912041133) (2026-11-16).
Status: PR open on branch `claude/gracious-sagan-rwlo33`, awaiting the owner's screenshot check and merge.

## Owner decisions (verbatim)

> อนุมัติ M7.4 ตามขอบเขตและรายการไฟล์ใน body ของ Issue นี้
> D1: A (PNG อย่างเดียว)
> D2: 3 เส้นทาง ประมาณ 12–15 ภาพ
> D3: docs/DEMO.md + docs/demo/ งบรวมไม่เกิน 3 MB กว้าง 1280 px deviceScaleFactor 1
> D4: A (สคริปต์ Playwright รันจาก scratchpad ไม่ commit ไม่เพิ่ม dependency ไม่แก้ workflow)
> D5: ใช่ (Bootstrap 5.3.3 จาก npm tarball บันทึก sha256)
> D6: DEMO.md เป็นอังกฤษ; แต่ละขั้น login ด้วยผู้ใช้ที่มีสิทธิ์จริงของขั้นนั้น
> D7: ไม่เพิ่มเทสต์; ใช้ link check ใน PR body และเจ้าของดูภาพในหน้า PR
> ระดับรีวิว: เอกสาร ไม่มี reviewer session แยก; Implementer = sub-agent ของ Manager
> ห้ามมีรหัสผ่านหรือค่าลับในภาพ

## Scope

Real screenshots from an empty database, `seed_production_demo --reset` and `runserver`, on three paths:
- Inventory (M4)
- Production (M5)
- Quality and trace (M6)

`docs/DEMO.md` shows the screenshots in order. Each step links its Issue, its PR and its CI evidence.
`README.md` links to the page.

Not in scope:
- app, template, CSS, settings, migration or seed changes (screen problems are reported as findings);
- new dependencies or workflow changes;
- deployment;
- real data or secrets;
- M7.5.

## Files allowed

`docs/DEMO.md`, `docs/demo/*.png`, `README.md`, this file, `docs/TASKS.md`,
`docs/assignments/i126-process-simplification.md` (P2), `docs/DEVELOPMENT.md` (link only).

## Acceptance criteria (Issue #129)

- [x] Owner approval with D1–D7.
- [x] Every screenshot comes from an empty database and the seeds at a stated commit. The commands, users and
      commit are in the PR body.
- [x] Numbers in the screenshots match the seed data and `docs/DEVELOPMENT.md`.
- [x] Every step in `docs/DEMO.md` links an Issue, a PR and CI evidence that open.
- [x] No password, secret or real data in any screenshot.
- [x] Total size ≤ 3 MB, width 1280 px, deviceScaleFactor 1. Relative links: 0 broken. No SHA in README.
- [ ] The owner checked the screenshots in the PR.
- [x] Changed files all on the list. No new dependency, no workflow change.
- [x] First commit records the merges of PR #127 and #128 (P2).
- [ ] CI on PostgreSQL 18.6 passes all 3 jobs. One report (standing rule 8).

## Roles and evidence

Manager = session `session_01MVmjhbuGPaWujXggKSGpsT`. Implementer = a sub-agent of the Manager. There is no
separate reviewer session (standing rule 7). Commands, results and the CI link are in the PR body (P5).
