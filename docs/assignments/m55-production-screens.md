# M5.5 — Manufacturing screens (read + record)

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `b5aa7df`.
[Issue #89](https://github.com/porntaned/ERP-for-Factory/issues/89). Status: **merged** (PR 1: PR #90 at `ac9a35d`; PR 2: PR #92 at `866e8af`, 2026-11-05; "PR 2 implemented, PR awaiting owner review", "PR 2 next" and "PR 1 (read-only) in progress" held until then — historical). The owner wants to see production on the web and try it themselves. In plan mode
they chose the full flow, delivered in two PRs, and approved the plan (chat, 2026-11-05).

## Approach

The screens extend the existing web (Django Templates + Bootstrap, `demo/`, as in M4.6). No new
dependency, schema, migration or trigger.
- A SPA was not chosen: it needs a new API and new dependencies, which need separate approval.
- Django admin was not chosen: it is not a user-facing UX.

Every write goes through `manufacturing/services.py`. The screens only choose what to show and
turn command errors into Thai messages.

## PR 1 — read-only pages

| URL | Shows |
|---|---|
| `/production/` | orders: number, product and BOM version, quantity, net output, status |
| `/production/<id>/` | per Lot: issued, returned, consumed, scrapped and held on the line; outputs per Lot (net, reversed, Quality); history; shortfall reason |
| `/lots/<id>/genealogy/` | inputs of the Lot, and outputs made from it |

- **Read model:** `manufacturing/queries.py` with `order_materials`, `order_outputs` and
  `order_history`. `_order_holdings` and `_output_total` in `manufacturing/services.py` move into
  it, so there is one formula.
- **Navigation:** a "การผลิต" menu entry for every logged-in user.
- **No write buttons in PR 1.**

## PR 2 — record forms (planned before PR 1 merged; delivered below)

- Forms: create order, issue, return, consume, scrap, record output, reverse, close (with
  shortfall reason).
- Buttons are shown by role. A hidden request UUID makes a double submit post once.
- Cancel waited for [Issue #86](https://github.com/porntaned/ERP-for-Factory/issues/86) (historical; delivered 2026-11-05, see the last section).

## Out of scope

BOM approval screens, Quality release (M6), Deploy.

## PR 1 — delivered

- `manufacturing/queries.py`:
  - `order_holdings` and `output_total` moved here from `services.py` with the same formulas;
    `services.py` imports them.
  - New: `order_materials`, `order_outputs`, `order_history`.
- `demo/production_views.py` with three templates under `demo/templates/demo/production/`.
- URLs in `config/urls.py` and the "การผลิต" menu entry.
- `tests/web/test_production_screens.py`: 11 tests.

### Rulings

1. **The read pages are open to every logged-in user**, as the balance page is. Only the PR 2
   buttons follow roles.
2. **No entry-id tie-breaker for history.** The history test was added after the first GREEN
   and passed at once: created times are distinct even within one transaction
   (statement time), so no tie-breaker was added. The test stays as a regression guard.
3. **Genealogy pages are keyed by Lot id**, because Lot codes are unique per item, not
   globally.

### RED / GREEN

- RED: 9 failed with 404 (the pages did not exist). `test_unknown_order_or_lot_is_404` passed
  from the start: it guards behaviour, it does not drive it.
- GREEN: 10 passed. Then the full suite: 935 passed. With the history test: 936.
- The query move was checked separately: `tests/manufacturing`, 166 passed, unchanged.

### Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6. Tested commit `6f111f1b7be84e8799f250776c7d73363b4b3f3c` (code at `4e4a9ba`; the later commit adds only docs and the history test).

| Command | Result |
|---|---|
| `uv run --env-file .env pytest -q` | 936 passed |
| `uv run ruff check .` / `ruff format --check .` | clean |
| `makemigrations --check --dry-run` | No changes detected |
| `runserver` on `erp_demo` (`seed_production_demo`) with Playwright: login as `demo-production` → การผลิต → #1 → LAMP-0001 → L-0003 | pages render; no 4xx/5xx in the server log |

The sandbox cannot reach `cdn.jsdelivr.net`. The screenshot script therefore served Bootstrap
5.3.3 from the npm tarball (sha256 `3c8f27e6…`, as in M4.7).

### PR 1 closeout (2026-11-05)

PR CI [#226](https://github.com/porntaned/ERP-for-Factory/actions/runs/41991095449) on head `d0a9a5f` (tested as merge `52d58e3`): PostgreSQL 18.6, Python 3.14.8, **936 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/90#issuecomment-6652899139)). The owner approved the merge in chat; PR #90 merged at `ac9a35d0ea5dcdef5f2d22c684025414e26586db`; [main CI #227](https://github.com/porntaned/ERP-for-Factory/actions/runs/41992724003): **936 passed**. Issue #89 stays open for PR 2.

### Review

Self-review (scrutinize):
- Text is autoescaped.
- The read pages write nothing (tested).
- The query move kept the manufacturing suite green.

Deferred minor: the list and outputs query per row (`output_total`, `get_lot_disposition`).
This is fine at demo scale.

## PR 2 — delivered

| URL | Command | Shown to |
|---|---|---|
| `/production/new/` | `create_production_order` | users with PRODUCTION anywhere (the list's "สร้าง order" button) |
| `/production/<id>/issue/` | `issue_material` | PRODUCTION at the order's line and output warehouse; the order is OPEN |
| `/production/<id>/return/` | `return_material` | same |
| `/production/<id>/consume/` | `consume_material` | same |
| `/production/<id>/output/` | `record_output` | same |
| `/production/<id>/close/` | `close_production_order` (blank shortfall reason is sent as none) | same |
| `/production/<id>/scrap/` | `scrap_material` | APPROVER at the line; the order is OPEN |
| `/production/<id>/reverse/<posting>/` | `reverse_order_posting` | APPROVER at the posting's warehouse; a "กลับรายการ" button on each unreversed history row |

- **Files:** `demo/production_forms.py`; `ACTIONS`, `order_action`, `production_new` and
  `reverse_posting` in `demo/production_views.py`; `order_actions` and
  `production_warehouses` in `demo/permissions.py`.
- **History rows:** `HistoryRow` carries the posting link and whether it was reversed.
- **Unauthorized:** a user without the role gets 403. So does a user on a non-OPEN order,
  even when calling the URL directly.
- **Unknown action:** 404.
- **Double submit:** a hidden request UUID makes it replay instead of posting twice.
- **Command errors:** shown as a Thai heading plus the command's own detail (for example the
  held Lots). Nothing is written.

### Rulings

1. **The issue form lists every Lot of the BOM's components, not only RELEASED ones.** Whether
   a Lot is RELEASED depends on the chosen source warehouse. The command refuses with
   "Lot ต้องเป็น RELEASED ที่คลังต้นทาง". Cost if wrong: one extra refusal for the user.
2. **Error detail keeps the command's English text**, for example `net issue would exceed the
   BOM requirement` or `LED-CHIP lot L-0001 holds 4`, after a Thai heading. Translating each
   command message is left for later.
3. **No cancel button.** It waits for Issue #86. (Historical, 2026-11-05: added after the owner ruled; see the last section.)

### RED / GREEN

- RED: 6 setup errors and 2 failures. The pages did not exist, so the fixture could not create
  an order.
- GREEN: 19 passed.
- `test_unknown_action_is_404`: RED with `NameError: Http404`, then GREEN.
- Driving the real server found a partly reversed output Lot labelled "กลับรายการแล้ว". The
  full-flow test was extended: RED, then "กลับรายการบางส่วน", GREEN.
- `tests/web/test_production_screens.py`: 20 passed.

### Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6. Tested commit `12e0a3001fcc4c5c8d31758996616f877f8f505b`.

| Command | Result |
|---|---|
| `uv run --env-file .env pytest -q` | 945 passed |
| `uv run ruff check .` / `ruff format --check .` | clean |
| `makemigrations --check --dry-run` | No changes detected |
| Real `runserver` on `seed_production_demo` data, Playwright clicking through every form (see below) | order CLOSED with reason; no 5xx in the server log |

The Playwright walk:
1. `demo-production`: create an order for 2 → issue L-0001 8 and D-0001 2.
2. An over-issue shows "เกินจำนวนที่อนุญาต: net issue would exceed the BOM requirement".
3. Consume L-0001 7 and D-0001 2; record output twice.
4. `demo-approver`: scrap 1; reverse the second output.
5. `demo-production`: close without a reason, which is refused with "net output is short of
   the order"; then close with a reason.

Two runs of the walk failed on script errors, not app errors:
- the login click hit the logout button;
- a Lot code was reused across runs, which the app refused correctly.

### Review

Self-review (scrutinize):
- Every form posts with a CSRF token.
- Role checks happen in the view and again in the command.
- Closed orders give 403.
- A double submit replays.
- Errors write nothing.

## Closeout (2026-11-05)

PR 2: PR CI [#231](https://github.com/porntaned/ERP-for-Factory/actions/runs/42009537477) on head `397c9d7` (tested as merge `86c0c63`): PostgreSQL 18.6, Python 3.14.8, **945 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/92#issuecomment-6655524390)). The owner approved the merge in chat; PR #92 merged at `866e8afb79be4ebefa41126ccb7a55d966daa0af`; [main CI #232](https://github.com/porntaned/ERP-for-Factory/actions/runs/42010216747): **945 passed**. Issue #89 was closed by PR #92. Review remained self-review only.

Of Issue #89's acceptance criteria, "the owner tries the web themselves" has no recorded evidence. The owner was given:
- the session's demo server, on preview port 8000;
- a private, read-only claude.ai snapshot of the PR 1 pages;
- local-run steps.

## Issue #86 — cancel needs no output (2026-11-05)

Branch `claude/affectionate-hawking-eyr2d1`; base `main` `bf6d58f`; tested commit `bb2ecb68c7babeb85f13cdbb4e41bb1fbe30f243`.
Owner chose option A in chat: an order with net output cannot be cancelled.

- **Rule:** OPEN → CANCELLED is refused while net output (OUTPUT − reversed OUTPUT) is above
  zero. To cancel, reverse the output first (APPROVER, order still OPEN), then cancel; or close the
  order with a shortfall reason.
- **Command:** `cancel_production_order` refuses with "reverse the output or close the order
  before cancelling: net output is N", using the existing `output_total`.
- **Database:** migration `0009_order_cancel_needs_no_output` adds a trigger using the existing
  `manufacturing_order_net_output`. It checks the transition only, so orders cancelled earlier are
  untouched. Reverse SQL drops the trigger and function.
- **Web:** `/production/<id>/cancel/` (reason, request UUID) and a "ยกเลิก order" button for users
  with PRODUCTION at the line and output warehouses, on OPEN orders only. Others get 403.
- **Double submit:** the command replays by request key (existing command tests). On the web, a
  repeated post after the cancellation is a 403 because the order is no longer OPEN. "Close"
  behaves the same way.

### RED / GREEN

- RED: 3 manufacturing tests failed with `DID NOT RAISE` (command twice, trigger once); the 4 new
  web tests failed because the button was missing and the URL gave 404.
- GREEN: `tests/manufacturing` 169 passed (166 before); web tests passed after one test fix: my
  first draft expected a replay after cancel and the real behaviour is 403 (see above).
- The existing migration round-trip test (`test_migrations_unapply_only_without_reversals`)
  also unapplies and reapplies 0009.

### Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6 (the pin is 3.14.8, not available in this sandbox).

| Command | Result |
|---|---|
| `uv run --env-file .env pytest -q` | 952 passed (945 before) |
| `ruff check .` / `ruff format --check .` | clean |
| `makemigrations --check --dry-run` | No changes detected |
| Real `runserver` on `seed_production_demo`, Playwright as `demo-production` and `demo-approver` | see below |

The walk (order #3, 2 × LAMP-A19): issue, consume, record output 1 → cancel refused with "net output
is 1" → reverse the output as `demo-approver` → cancel again. The second cancel was also refused,
with "return the material on the line … L-0001 holds 8": my script had reversed the first
reversible row (the consumption) instead of the output, which was correct app behaviour and a script
error. After reversing the output row and using the 8 chips again, the cancel succeeded; the
database showed `CANCELLED`, and there was no 5xx in the server log.

### Review

Self-review only (one agent, no sub-agents); scrutinize per `docs/SCRUTINIZE.md` below.

- The command and the trigger use the same definition of net output as close, so cancel and close
  cannot disagree.
- The trigger is the backstop for any writer that skips the command.
- Existing data: a database that already holds a CANCELLED order with output keeps it. The rule is
  not retroactive.
- Not tested: concurrent output and cancel. Both lock the order row first (`select_for_update`),
  so cancel sees committed output; no race test was added.

### Issue #86 closeout (2026-11-06)

PR CI [#235](https://github.com/porntaned/ERP-for-Factory/actions/runs/42016533064) on head `1ec82bb` (tested as merge `441a6c3`): PostgreSQL 18.6, Python 3.14.8, **952 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/94#issuecomment-6656531421)). The owner approved the merge in chat; [PR #94](https://github.com/porntaned/ERP-for-Factory/pull/94) merged at `69b4e18590a59ed2e6ea10ac94a28a0af4992991`; [main CI #236](https://github.com/porntaned/ERP-for-Factory/actions/runs/42148409105): PostgreSQL 18.6, **952 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/commit/69b4e18590a59ed2e6ea10ac94a28a0af4992991#commitcomment-208403221)). Review remained self-review only. Issue #86 is still open: the PR said "Issue: #86" without a closing keyword, so the owner closes it.
