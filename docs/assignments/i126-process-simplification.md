# Issue #126 — fewer process steps (P1–P5)

[Issue #126](https://github.com/porntaned/ERP-for-Factory/issues/126); approval:
[comment 6910189566](https://github.com/porntaned/ERP-for-Factory/issues/126#issuecomment-6910189566) (2026-11-16).
Status: done — [PR #127](https://github.com/porntaned/ERP-for-Factory/pull/127) (PR A) and [PR #128](https://github.com/porntaned/ERP-for-Factory/pull/128) (PR B) merged by the owner on GitHub (2026-11-16).

## Owner decisions (verbatim)

> อนุมัติ P1–P5
> D-P1: ใช่ status text แก้ทับได้ ไม่ต้องมีวันที่หรือข้อความเดิม
> D-P2: (a) ใช่ main CI fail ให้แจ้งเจ้าของในแชตครั้งเดียว (b) ใช่ งานสุดท้ายเปิด docs PR ได้ (c) ใช่ ยอมให้ติ๊กบน main ช้าได้ 1 PR
> D-P5: ไม่เกิน 60 บรรทัด
> D-การทำ: แยก 2 PR (A: P1 P2 P3 P5, B: P4) ทำหลัง merge PR #125 และก่อน M7.4; ไม่มี reviewer session แยก
> PR A ให้บันทึกผล main CI #305 (ผ่าน) ที่ยังค้างจาก PR #125 ด้วย

## Scope

- **PR A** (documentation and rules):
  - P1: historical only for owner rules and decisions; status text is overwritten.
  - P2: no post-merge docs PR and no merge SHA or `main` CI in the docs. Facts known after a merge go in the first
    commit of the next PR. A failed `main` CI is reported to the owner once in chat. M7.5 may have its own docs PR.
    Ticks may lag `main` by one PR.
  - P3: the owner's checker reviews an Issue before approval only for business code, database or permissions.
  - P5: a slice record is at most 60 lines; evidence by link; commands and results in the PR body.
  - Also: the result of main CI #305 (PR #124), on the owner's instruction.
- **PR B** (small CI): P4, `::warning::` when the `pkill -9` fallback runs.

Not changed: the owner merges every PR; CI on PostgreSQL 18.6 is the evidence of record; work that touches business
code, the database or permissions, and the final Scrutinize, gets an independent review by a separate session.

## Files

- PR A: `AGENTS.md`, `docs/MULTI_AGENT.md`, `.github/pull_request_template.md`, `docs/DEVELOPMENT.md`,
  `docs/TASKS.md`, `docs/assignments/m73-architecture-diagrams.md` (main CI #305), this file.
- PR B: `.github/workflows/foundation.yml`, `scripts/check_install_guide.py`, `tests/ci/test_install_guide_check.py`.

## Acceptance criteria (Issue #126)

- [x] New text as approved; the replaced owner rules kept as historical with a date (P1).
- [x] No document states the post-merge docs PR as a current rule (`grep`).
- [x] P4: `install-guide` and its check step pass on PostgreSQL 18.6; `postgresql-tdd` and `report` unchanged;
      `tests/ci` pass.
- [x] Relative links in the changed files: 0 broken.
- [x] One report per PR when ready to merge (standing rule 8).

## Roles and review

Manager = session `session_01MVmjhbuGPaWujXggKSGpsT`, who also made the changes. No separate reviewer session
(standing rule 7, D-การทำ). The owner's checker reviews at merge.

## Evidence

Development checks, commands and CI links are in each PR body (P5): [PR #127](https://github.com/porntaned/ERP-for-Factory/pull/127),
[PR #128](https://github.com/porntaned/ERP-for-Factory/pull/128).
