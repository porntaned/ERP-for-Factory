# Docs repair after M6 (2026-11-11)

Type: documentation only. Status: **PR open, awaiting the owner** (no merge, no deployment).

This is a **docs repair on the owner's instruction**, an exception to the AGENTS.md rules *No chain* and *One owner*
that the owner allowed in chat on 2026-11-11. It is **not** the post-merge docs PR of a slice. (Earlier wording in the
PR body, "Post-merge docs PR for PR #115", was wrong — historical, corrected 2026-11-11.)

The merge SHA of the PR for this repair ([PR #116](https://github.com/porntaned/ERP-for-Factory/pull/116)) will be
recorded in the post-merge docs PR of the next slice (M7.2). No docs PR is opened for PR #116 itself.

Owner's instruction, verbatim (chat, 2026-11-11; in a code block so Markdown does not alter it):

```text
## งานที่ 1 (ทำก่อน): docs PR ซ่อมเอกสาร
- บันทึก merge PR #115 (217be3f, main CI #281) ใน Progress log
- README รายการหน้าจอ: เพิ่ม /quality/, /quality/audit/, /lots/search/, /lots/<id>/trace/
- ลิงก์ CI ที่ขาด: M6.2 (main CI #257), PR #106 (CI #261), PR #107 (main CI #266)
- m62 / m63: แก้ข้อความว่า Issue #103 / #108 ยังเปิด ให้ตรงความจริง (historical + วันที่)
- ลิงก์เสีย 2 ลิงก์ใน docs/reviews/project-audit-after-pr12.md:
  คัดลอกไฟล์ jpg และไฟล์ test จาก branch codex/project-audit-after-pr12
  ไฟล์ test วางเป็น docs/evidence/project-audit-reproductions.py.txt (ห้ามวางใน tests/)
เปิด PR รอ CI ผ่าน แล้วรายงานผม ห้าม merge
```

## Roles (as performed)

- **This session** (`session_01MVmjhdAZRZbr6kL22x7hby`, branch `claude/vibrant-sagan-ivztik`): the session the owner
  gave this docs repair to directly. It is **not** the Manager of slice M6.4; that Manager is
  `session_01MVmjhfwWvvAa4GLjR3EaTs`. It made these edits itself; no sub-agent was used and there is no review
  (self-checked only). (Earlier wording "Manager: the Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby`" did not
  say this — historical, corrected 2026-11-11.)
- **Owner:** gave the task list in chat (2026-11-11) and decides the merge.

## Scope (owner's list)

1. Record the merge of [PR #115](https://github.com/porntaned/ERP-for-Factory/pull/115) at `217be3f` and
   [main CI #281](https://github.com/porntaned/ERP-for-Factory/actions/runs/43004892638) in `docs/TASKS.md`.
2. `README.md` screen list: add `/quality/`, `/quality/audit/`, `/lots/search/`, `/lots/<id>/trace/`.
3. Missing CI links in `docs/TASKS.md`: M6.2 (main CI #257), PR #106 (PR CI #261), PR #107 (main CI #266).
4. `m62` / `m63` records: the statements that Issue #103 / #108 are still open are marked historical with a date.
5. Two broken links in `docs/reviews/project-audit-after-pr12.md`: copy `docs/evidence/pr-12-merged.jpg` and the
   reproduction tests (as `docs/evidence/project-audit-reproductions.py.txt`, not under `tests/`) from branch
   `codex/project-audit-after-pr12` (`98103b2`).

Excluded: M7 work, code, tests, `AGENTS.md`, `docs/MULTI_AGENT.md`, branch/tag clean-up.

## Facts checked before editing (GitHub, 2026-11-11)

- Open PRs: none. Open Issues: none. Issue #103 closed (completed) 2026-11-10; Issue #108 closed (completed) 2026-11-11.
- Run numbers match the owner's list: #257 → `66c0ede` (push, main), #261 → `47f6f99` (PR #106 head),
  #266 → `94a3e38` (push, main, PR #107 merge), #280 → `d6555cc` (PR #115 head), #281 → `217be3f` (push, main).
- Test counts read from each run's `postgresql-tdd` job log (last pytest summary line): #281 `1160 passed`,
  #266 `1067 passed`, #261 `1067 passed`; PostgreSQL `18.6 (Debian 18.6-1.pgdg12+2)`, Python 3.14.8.
  The CI summary artifact could not be downloaded (the session's network proxy refused the artifact host), so
  the job logs were used instead.
- The copied files are byte copies of the blobs at `98103b2` (`git show <ref>:<path>`); the image is 58,667 bytes.
- `/quality/`, `/quality/audit/`, `/lots/search/`, `/lots/<int:pk>/trace/` exist in `config/urls.py`;
  all are `login_required`; `/quality/audit/` raises 403 without a QUALITY or APPROVER grant.

## Development checks (local, not CI; base `main` at `217be3f`, working tree before the commit)

- A small relative-link checker (session scratchpad, not committed) over the six changed Markdown files:
  on `main` `217be3f` `docs/reviews/project-audit-after-pr12.md` has **2 broken relative links**
  (`../evidence/pr-12-merged.jpg`, `../../tests/quality/test_project_audit_reproductions.py`); with this change
  all six files have **0 broken relative links**.
- `git diff --check`: no whitespace errors.
- No code, test or migration changed, so pytest/Ruff were not run locally; CI runs the full suite on PostgreSQL 18.6.

## Evidence

CI evidence of record: [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/116#issuecomment-6798804764) (always shows the latest head). ("linked from the PR once CI has run" held until CI ran — historical.)
