# M7.2 — Install guide checked from a fresh state

Repository `porntaned/ERP-for-Factory`; branch `claude/vibrant-sagan-ivztik` (restarted from `main` `1261e86`
after PR #116 merged); [Issue #117](https://github.com/porntaned/ERP-for-Factory/issues/117).
Status: **spec approved by the owner; implementation not started.**

Owner approval: [Issue #117 comment](https://github.com/porntaned/ERP-for-Factory/issues/117#issuecomment-6820317207)
(2026-11-12) and the owner's chat message of the same day (conditions 1–5 below).

Roles (as they actually happen; updated as work proceeds):
- **Manager** = Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby` (the owner's chat session for this period).
- **Implementer** = a sub-agent spawned by the Manager (not started yet).
- **Reviewer** = a **separate Claude Code session**, given only the PR number, the Issue number and this path,
  as in M6.2–M6.4. Not a sub-agent of the Manager. Report in `docs/reviews/m72-independent-review.md`.
- **Owner** decides the merge. No deployment.

## Purpose

A visitor who clones the repository should get from nothing to the running demo by following one page, and
the project should prove that page works from a fresh state. Today the steps are split and disagree:

- `README.md` "Run locally" (bash): `cp .env.example .env`, `uv sync`, `migrate`, `pytest`, `seed_demo`,
  `set_demo_passwords`, `runserver`; no `seed_production_demo`.
- `docs/DEVELOPMENT.md` "Local commands" (PowerShell): `Copy-Item`, `uv sync`, `check`, `pytest`, `ruff`; no
  `migrate` or seeds.
- Neither says the PostgreSQL user must be able to create the test database (pytest-django creates
  `test_<POSTGRES_DB>`), nor how to create the role and database.
- Nobody has recorded running the steps from a fresh clone and an empty database.

## Owner rulings (verbatim, Issue #117 comment 6820317207)

```text
- D1 = C (CI job ใหม่แยกจาก job เดิม บน PostgreSQL 18.6 เป็นหลักฐานหลัก; ผลใน container เป็น development check)
- D2 = bash เป็นหลัก หมายเหตุ Windows ต้องเขียนว่า "ยังไม่ได้ทดสอบบน Windows"
- D3 = ไม่มี Docker/compose
- Independent review โดย session แยก
- คำสั่งใน CI job ต้องตรงกับ INSTALL.md ตามตัวอักษร
- README, DEVELOPMENT.md และ INSTALL.md ต้องไม่มีคำสั่งที่ขัดกัน และลิงก์ relative เสีย 0
- ห้ามแก้ AGENTS.md ใน M7.2
```

Further conditions from the owner's chat (2026-11-12), summarised:

1. D1: the new CI job is **separate** from `postgresql-tdd`; **the existing jobs are not changed**. Results in the
   session container (PostgreSQL 16) are labelled a development check.
2. D3: no Docker/compose and no pulling of outside images by this work.
3. Review by a separate session (PR number, Issue number, spec path only); never a Manager sub-agent.
4. The `--depth=50` finding about AGENTS.md step 1 is reported to the owner; AGENTS.md is not edited in M7.2.
5. Post-merge docs PR item (e) is added (below).

## Scope

1. **`docs/INSTALL.md`** (new), the single install guide, bash first:
   - What you need, pointing to the Version contract in `docs/DEVELOPMENT.md` (no second copy of the pins):
     Git, uv, Python 3.14.8 (installed by uv), PostgreSQL 18.6 installed any way (link to the official download
     page; no Docker/compose instructions).
   - Create the role and database with `psql` as a PostgreSQL superuser, with synthetic placeholder values; the
     role gets `CREATEDB` so pytest-django can create the test database. Explain why in one line.
   - `git clone` → `.env` from `.env.example` (every placeholder replaced; how, without real secrets) →
     `uv sync --locked --all-groups` → `manage.py check` → `migrate` → `pytest` → `seed_demo` →
     `seed_production_demo` → `set_demo_passwords` → `runserver` → log in.
   - Which demo user sees which screen (only screens that exist in `config/urls.py`), and links to the existing
     walkthroughs in `docs/DEVELOPMENT.md` instead of copying them.
   - Reset: `seed_demo --reset` / `seed_production_demo --reset` flush every table; disposable databases only.
   - Troubleshooting: only problems actually met while checking the guide (with the real error text).
   - A Windows note that states **"ยังไม่ได้ทดสอบบน Windows"** (not tested on Windows).
2. **`README.md`** "Run locally": a short summary and a link to `docs/INSTALL.md`; no commit SHA.
3. **`docs/DEVELOPMENT.md`** "Local commands": point to `docs/INSTALL.md`; keep only developer-only commands
   (Ruff, format) that the guide does not cover. Statements that no longer hold are marked historical, not deleted.
4. **`.github/workflows/foundation.yml`**: one **new job** (for example `install-guide`) that follows
   `docs/INSTALL.md` on `ubuntu-24.04` with PostgreSQL 18.6. The jobs `postgresql-tdd` and `report` are not edited.
   - It uses the same service image already used by `postgresql-tdd` (`postgres:18.6-bookworm`); no other image.
     The service starts with only a superuser, so the job runs the guide's own role/database `psql` commands.
   - Every command in the guide's checked path appears in the job **in the same order and character for
     character**. The only allowed differences, each marked in the workflow with a `# CI-only:` comment and listed
     in this spec's Evidence section:
     - `git clone` is replaced by `actions/checkout`; installing uv is replaced by the pinned setup-uv action;
     - values the guide tells the reader to choose (passwords, secret key) come from job env variables named in
       the guide;
     - `runserver` is started in the background, followed by HTTP checks (login page 200; log in as a demo user;
       the balance page shows the seeded stock) and then stopped;
     - re-running the seed commands to show they add nothing.
   - The new job does not feed the CI comment (the `report` job and `scripts/ci_summary.py` stay unchanged); its
     result is the job's own status on the PR and on `main`.
5. **`docs/assignments/m72-install-guide.md`** (this file): Evidence section with the fresh-state run.

## Not in scope

Deploy/hosting; Docker, compose, pulled images or any new dependency; application code or settings; changes to
`postgresql-tdd` or `report`; M7.3–M7.5; testing on Windows or macOS; production hardening; deleting or archiving
branches; editing `AGENTS.md` or `docs/MULTI_AGENT.md`.

## Acceptance criteria

- [ ] Spec and rulings D1–D3 approved by the owner before writing (done: comment 6820317207).
- [ ] Every command in `docs/INSTALL.md` was run, in order, from a fresh clone and an empty PostgreSQL database;
      results recorded here with the commit they ran on. The session-container run (PostgreSQL 16) is labelled a
      development check.
- [ ] Results seen: `check` passes, `migrate` passes, the full suite passes, both seeds run and a second run adds
      nothing, the login page answers 200, and a logged-in demo user sees the seeded stock (exact text recorded).
- [ ] The new CI job passes on PostgreSQL 18.6; `postgresql-tdd` and `report` are byte-for-byte unchanged and still
      pass.
- [ ] **The commands in the new CI job match `docs/INSTALL.md` character for character**, apart from the listed
      `# CI-only:` differences. The reviewer compares them line by line.
- [ ] `README.md`, `docs/DEVELOPMENT.md` and `docs/INSTALL.md` contain no conflicting commands, and the relative
      links in every changed Markdown file resolve (**0 broken**).
- [ ] No real secrets: placeholders only; README has no commit SHA.
- [ ] Independent review by a separate session → `docs/reviews/m72-independent-review.md`; at most 2 repair rounds.
- [ ] CI evidence cited by link to the PR's CI comment while the PR is open; documentation in the same PR.

## Prohibited

Merging without the owner's explicit instruction; deployment; external services or images beyond the existing CI
service image; new dependencies; force-push; editing `AGENTS.md` / `docs/MULTI_AGENT.md`; real data or secrets.

## Post-merge docs PR (owner, 2026-11-12)

The Manager opens it immediately after the owner merges M7.2. It also does:

- (a) record the merge of PR #116 at `1261e86`, merged by `session_01MVmjhdAZRZbr6kL22x7hby` on the owner's
  instruction (quoted verbatim in Issue #117), with PR CI #284 and main CI #285
  ([CI comment](https://github.com/porntaned/ERP-for-Factory/commit/1261e86a5dbd396dd9f10234e44e353829cebcc6#commitcomment-209414826),
  1160 passed);
- (b) `docs/assignments/docs-repair-2026-11-11.md`: "PR open, awaiting the owner" → historical; closeout with merge
  SHA, PR CI #284 and main CI #285;
- (c) `AGENTS.md:5` and `:20` describe what happens: the owner decides; a session merges only on the owner's explicit
  instruction, and that instruction is quoted in the record;
- (d) a `Type:` line at the top of `docs/reviews/m61-pr2-independent-review.md` saying it was a sub-agent of the
  Manager, with the date of the correction;
- (e) if the owner has created the archive tags and deleted the branches by then:
  `docs/reviews/project-audit-after-pr12.md:3` "not done yet" → historical, with the tag name and the date.

## Evidence

Not started.
