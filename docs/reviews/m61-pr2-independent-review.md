# Review — PR #101 (Issue #96, M6.1 PR 2: Quality web screens)

Reviewer: separate sub-agent (fresh context), date 2026-11-06, read-only, following docs/SCRUTINIZE.md

- Reviewed commit: `38d7d45729ba4b90aba939ffeef28f9315776e19` (branch `claude/dreamy-volta-9v3i8u`), base `origin/main` `5323859`. One commit: `feat(demo): Quality inspection screens (M6.1 PR 2)`.
- Spec: `docs/assignments/m61-inspection.md` (Owner rulings 1–7, Scope "PR 2", PR split "PR 2 gets its own short design before code").
- This is an independent review by a sub-agent; it is not an owner review. GitHub was not reachable from this session (MCP github failed to connect), so PR CI / CI comment were **not** checked.

## 1. Intent

Give QUALITY a web screen to inspect HOLD Lot-Warehouses (PASS/FAIL via `record_inspection`), give APPROVER a "ส่งกลับ HOLD" button on REJECTED rows (via `return_rejected_to_hold`), and show inspection + disposition history on the Lot genealogy page. The change is about as small as it can be: a thin view layer on top of the PR 1 commands, the M5.5 pattern (hidden request UUID, command errors → messages). No simpler alternative found. The seed grant change is needed only so FINAL inspection can be shown with demo users (PR 1 finding 1).

## 2. What was traced

- `config/urls.py` → `quality_list` / `inspect` / `return_to_hold` (`demo/quality_views.py`): `@login_required`, `@require_POST` on both writes.
- `_pairs`: ledger `Sum(quantity_delta)` per (lot, warehouse) at `warehouses_for_user(user, ["QUALITY","APPROVER"])`, `balance > 0`; per row `qs.get_lot_disposition` (→ `_validate_pair` → latest `LotDispositionEvent`), RELEASED skipped; `can_inspect` = HOLD ∧ `has_warehouse_role(QUALITY)`; `can_return` = REJECTED ∧ `has_warehouse_role(APPROVER)`. `StockLedgerEntry` has no `Meta.ordering`, so the `values().annotate()` GROUP BY is correct.
- `_run`: form invalid → re-render with `form.errors.as_text()`; command raises one of `DispositionAuthorizationError / ConflictError / ValidationError` (the `Inspection*` errors subclass these) → re-render with message; success → message + redirect.
- `quality/services.py`: `record_inspection` (validate pair/result/quantity/note/UUID → lock Lot → lock actor + QUALITY grant → replay → kind → HOLD check → balance → insert inspection + event); `return_rejected_to_hold` (APPROVER grant → replay → REJECTED check → not-the-rejecting-inspector → insert). `IntegrityError` that is not a replay is re-raised.
- `access_control/policies.py`: `has_warehouse_role` / `warehouses_for_user` require an active saved user, same as the commands.
- `demo/permissions.py` nav flag `can_quality`; `demo/templates/demo/base.html` nav link.
- `demo/production_views.py::lot_genealogy` + `genealogy.html`: two new tables, `select_related`, ordered by id, autoescaped.
- `seed_demo` grant change, and its interaction with `seed_production_demo` (which already grants `demo-approver` APPROVER at LINE-1 and FG, `seed_production_demo.py:53-56`) and `order_actions` / history `can_approve_all`.
- `tests/web/test_quality_screens.py` (12 tests): all go through the real URLs, views, forms and PR 1 commands on top of `seed_production_demo`. No mocks.

## 3. Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6, local, at `38d7d45`.

| Command | Result |
|---|---|
| `UV_PYTHON=3.14.6 uv run --env-file …/.env pytest -q tests/web tests/quality` | **203 passed** |
| Throwaway probes `…/scratchpad/probe_quality_pr2.py` (outside the repo, `PYTHONPATH=. pytest -c pyproject.toml --rootdir .`) | 8 passed; observations below |

Probe observations:

| Probe | Observed |
|---|---|
| CSRF: `Client(enforce_csrf_checks=True)` POST without token | 403; list page carries a token per form |
| GET `/quality/inspect/`, `/quality/return/` | 405 (existing test) |
| Tampered `warehouse` = warehouse of another Organization | 200, "ข้อมูลไม่ถูกต้อง: lot and warehouse must belong to one organization", nothing written |
| Tampered `warehouse` = LINE-1 (no QUALITY grant) | 200, "ไม่มีสิทธิ์ทำรายการนี้", nothing written |
| Nonexistent lot id / `result=MAYBE` / `request_id=not-a-uuid` / sample `10^14` | 200 with form error, nothing written |
| Note `<script>alert(1)</script>` on genealogy page | escaped (`&lt;script&gt;`) |
| Double submit, same key | 302 and 302, one `LotInspection` |
| Same key, different note | 200, conflict message, nothing written |
| Stale page: inspect a pair already RELEASED (new key) | 200, **"คำขอนี้ถูกใช้แล้ว กรุณาเปิดหน้าใหม่"** (see m3) |
| Stale page: return a pair that is no longer REJECTED | 200, same "request used" message (see m3) |
| `demo-quality` given APPROVER at FG, FAILs LAMP-0001 | "ส่งกลับ HOLD" button **shown** to that user; POST → "ไม่มีสิทธิ์ทำรายการนี้", state stays REJECTED (see m2) |
| Query count of `/quality/` | 2 rows → 18 queries; 22 rows → 58 queries (2 per row; see m4) |
| Plain `seed_demo` grants | demo-approver APPROVER at FG/RM-A/RM-B; demo-quality QUALITY at FG/RM-A/RM-B |

No path found where a command exception escapes as a 500 under normal or tampered input. The only re-raise is the non-replay `IntegrityError` (and any trigger-raised `InternalError`) in the commands, which needs a database-level race the Lot lock already serializes; this is the same contract as the M5.5 screens.

## 4. Findings

### Blocker

None.

### Major

**M1. The PR changes no documentation; required docs are now stale and the owner rulings it relies on are not recorded in the repo.**
- Where: `git diff --stat origin/main...HEAD` lists only code and tests. `docs/DEVELOPMENT.md:154` says "Web screens come in M6.1 PR 2; until then use the shell"; `docs/DEVELOPMENT.md:171` says "`demo-quality` has QUALITY only at RM-A" (already wrong before: RM-A and RM-B; now also FG). `docs/assignments/m61-inspection.md` has no PR 2 design (its "PR split" says "PR 2 … gets its own short design before code"), no PR 2 evidence section, and its closeout still lists "Open owner decision before PR 2: whether the demo seed grants `demo-quality` QUALITY at FG". `docs/TASKS.md` has no Progress log line for PR 2.
- Why it matters: `AGENTS.md` ("Documentation updates": the agent that prepares a change prepares its docs in the same PR; items 1, 2, 4) and the PR template checklist. The seed change is a privileged-access change; `AGENTS.md` "Safety boundaries" requires explicit owner approval, and the only record of it is a test docstring (`tests/web/test_quality_screens.py:6-7`: "Owner decisions (chat, 2026-11-06): design approved; demo-quality gets QUALITY and demo-approver gets APPROVER at FG"). The approval of `demo-approver` at FG in `seed_demo` was never an open question in the spec (only demo-quality was).
- Evidence: diff stat above; `grep` of the two DEVELOPMENT.md lines.
- Smallest fix: in this PR add to `m61-inspection.md` (a) the owner rulings of 2026-11-06 under "Owner rulings" (design approved; QUALITY for demo-quality and APPROVER for demo-approver at FG in `seed_demo`), (b) the short PR 2 design, (c) a "PR 2 — delivered" section with tested SHA, actual commands/results and review type; update `DEVELOPMENT.md` (web steps for `/quality/`, correct the grant sentence, mark the "until then use the shell" sentence historical with a date); add a dated TASKS.md Progress line; fill the PR template doc checklist.

### Minor

**m1. The `seed_demo` APPROVER-at-FG grant is redundant for the quality demo, and the test does not test it.**
- Where: `demo/management/commands/seed_demo.py:81`; `tests/web/test_quality_screens.py:76-80`.
- Why it matters: FG holds stock only after `seed_production_demo`, which already grants demo-approver APPROVER at LINE-1 and FG (`seed_production_demo.py:53-56`). The extra grant in plain `seed_demo` changes only the M4.7 demo: an order created on the web after plain `seed_demo` now shows demo-approver "กลับรายการ" on OUTPUT rows (`order_actions["reverse_output"]`, APPROVER at FG) but still no Scrap or line reversal (no LINE-1) — an odd half-grant. `test_seed_grants_quality_and_approver_at_fg` uses the `seed_production_demo` fixture, so it passes with or without the `seed_demo` approver change.
- Evidence: probe on plain `seed_demo` lists `('FG','APPROVER')` for demo-approver; `permissions.order_actions` lines for `reverse_output`.
- Smallest fix: revert the `demo-approver` line in `seed_demo` (keep demo-quality at FG), or, if the owner wants it, record that ruling (M1) and make the test call `seed_demo` alone.

**m2. The "ส่งกลับ HOLD" button is shown to the rejecting inspector when they also hold APPROVER, and the refusal hides the reason.**
- Where: `demo/quality_views.py:65-66` (`can_return` checks only the APPROVER grant); `demo/quality_views.py:24` (`DispositionAuthorizationError` → generic "ไม่มีสิทธิ์ทำรายการนี้", `detail=False`).
- Why it matters: owner ruling 5 says the APPROVER must not be the inspector. The command enforces it (safe), but the screen offers an action the user cannot take and the message does not say why. No demo user holds both roles today, so it is latent.
- Evidence: probe — demo-quality + APPROVER at FG, FAIL, then `/quality/` contains `data-action="return-hold"`; POST → "ไม่มีสิทธิ์ทำรายการนี้"; state REJECTED.
- Smallest fix: in `_pairs`, add `and qs._rejecting_inspector_id(lot, warehouse) != user.pk` (or a public wrapper) to `can_return`; optionally set `detail=True` for the authorization message so the command's reason is shown.

**m3. A stale page gets a misleading message.**
- Where: `demo/quality_views.py:25`.
- Why it matters: `record_inspection` raises `InspectionConflictError("only a HOLD Lot can be inspected; current state is …")` and `return_rejected_to_hold` raises `DispositionConflictError("expected REJECTED, current state is …")`. Both map to "คำขอนี้ถูกใช้แล้ว กรุณาเปิดหน้าใหม่" ("this request was already used"), which is wrong for a Lot someone else already inspected — the common two-inspector case.
- Evidence: probe — PASS, then a second form (new key) FAIL → "คำขอนี้ถูกใช้แล้ว กรุณาเปิดหน้าใหม่"; same for a stale return.
- Smallest fix: show the command detail for conflicts (`detail=True`), or a neutral text such as "สถานะเปลี่ยนแล้วหรือคำขอนี้ถูกใช้แล้ว กรุณาเปิดหน้าใหม่".

**m4. List page is N+1 and unbounded.**
- Where: `demo/quality_views.py:42-69` (`get_lot_disposition` and `has_warehouse_role` per row; no row limit).
- Why it matters: 2 queries per row; every HOLD/REJECTED pair with stock at every granted warehouse is rendered with two forms. Fine for the demo, grows linearly with Lots.
- Evidence: probe — 2 rows → 18 queries, 22 rows → 58 queries.
- Smallest fix: fetch the user's QUALITY/APPROVER warehouse ids once (two sets) and the latest disposition per pair in one query (`Subquery`/`DISTINCT ON (lot_id, warehouse_id)` ordered by `-id`); optionally cap rows like `history` (`[:100]`). Acceptable to defer with a note.

**m5. Tests miss several real paths the PR depends on.**
- Where: `tests/web/test_quality_screens.py`.
- Gaps: CSRF (Django's test client skips CSRF checks; no `enforce_csrf_checks=True` test), tampered warehouse of another organization / of a warehouse without the role, the inspector-with-APPROVER case (m2), the stale-state message (m3), REJECTED rows seen by a QUALITY-only user (only asserts the button is absent), and the second response of the double submit (only counts rows). All of these behave acceptably in the probes, so this is coverage, not behaviour.
- Smallest fix: add 3–4 short tests mirroring the probes (CSRF 403, other-org warehouse refused with nothing written, stale message, inspector+APPROVER button hidden after m2).

**m6. Duplicate HTML ids and an unlabeled select on the list page.**
- Where: `demo/templates/demo/quality/list.html:17-18,25` — every row renders `id_lot`, `id_warehouse`, `id_request_id`, `id_result`; the result `<select>` has no label or `aria-label`. Also `InspectionForm(initial=… "sample_quantity": "1")` at `quality_views.py:78` is unused because the template hard-codes the input.
- Why it matters: invalid HTML / accessibility only; posting works because each form is separate.
- Smallest fix: pass `auto_id=False` (or a per-row `prefix`) to the row forms and add `aria-label="ผล"`; drop the unused initial.

### Notes (no change requested)

- `lot_genealogy` is open to any logged-in user for any Lot (pre-existing M5.5 decision); it now also shows inspection notes and inspector usernames. Synthetic data, single organization in the demo; flag only if per-warehouse visibility is wanted later (M6.3).
- `demo-quality` QUALITY at FG adds no buttons outside `/quality/`: no other screen keys on QUALITY (`grep` of `demo/views.py`, `production_views.py`, templates). Existing nav expectations in `tests/web/test_inventory_screens.py:119-120` still hold (203 passed).
- REJECTED is shown as plain text in the list, while production pages use `demo/production/_status.html` badges — cosmetic consistency only.
- PR CI on PostgreSQL 18.6 is the evidence of record and was not checked here.

## 5. Verdict

**fix-then-ship** — the code path is correct and safe (commands enforce every rule; CSRF, POST-only, tampering and double submit all hold on PostgreSQL), but the PR ships without the required documentation and without a repo record of the owner's privileged-access ruling for the seed grants (M1); m1–m3 are small and worth fixing in the same pass.

## Implementer response (2026-11-06)

Fixed in one pass, each test-first, at `3a9c0c4` (full suite 1003 passed, development check on
PostgreSQL 16.15). Review type of this file: **independent** (findings) plus the implementer's
response (this section).

| Finding | Outcome |
|---|---|
| M1 docs and owner rulings not recorded | Fixed: spec gains the PR 2 design, the owner rulings of 2026-11-06 and a delivered section; `DEVELOPMENT.md` web walkthrough and demo grants; `TASKS.md` log line; this file. |
| m1 demo-approver FG grant in `seed_demo` | Fixed: removed; APPROVER at FG comes from `seed_production_demo`, the seed that creates FG Lots, so the owner-approved demo works; `test_plain_seed_grants_only_quality_at_fg` |
| m2 return button for the rejecting inspector | Fixed: `can_return` excludes `rejecting_inspector_id` (now public); `test_rejecting_inspector_who_is_also_approver_gets_no_return_button` RED → GREEN |
| m3 stale page told "request already used" | Fixed: conflicts show the command's reason; `test_stale_page_explains_the_current_state` RED → GREEN |
| m4 per-row queries, no row limit | Deferred: synthetic demo data has a handful of pairs; recorded for M7 polish |
| m5 test gaps | Fixed: CSRF, warehouse without a role, inspector-approver, stale page (2 of these passed at once: coverage only) |
| m6 duplicate ids, unlabelled select | Fixed: `auto_id=False` on row forms, `aria-label`; `test_row_forms_have_no_duplicate_ids` RED → GREEN |

The reviewer did not re-review the fixes (one repair cycle, as MULTI_AGENT.md allows); the fixes are
covered by the tests above and by CI on the PR.
