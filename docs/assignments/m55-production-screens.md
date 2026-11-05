# M5.5 — Manufacturing screens (read + record)

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `b5aa7df`.
[Issue #89](https://github.com/porntaned/ERP-for-Factory/issues/89). Status: **PR 1 merged** (PR #90 at `ac9a35d`, 2026-11-05); **PR 2 (record forms) next** ("PR 1 (read-only) in progress" held until then — historical). The owner wants to see production on the web and try it themselves. In plan mode
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

## PR 2 — record forms (next)

- Forms: create order, issue, return, consume, scrap, record output, reverse, close (with
  shortfall reason).
- Buttons are shown by role. A hidden request UUID makes a double submit post once.
- Cancel waits for [Issue #86](https://github.com/porntaned/ERP-for-Factory/issues/86).

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

PR CI [#226](https://github.com/porntaned/ERP-for-Factory/actions/runs/41991095449) on head `d0a9a5f` (tested as merge `52d58e3`): PostgreSQL 18.6, Python 3.14.8, **936 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/90#issuecomment-6652899139)). The owner approved the merge in chat; PR #90 merged at `ac9a35d0ea5dcdef5f2d22c684025414e26586db`; main CI: **result pending**. Issue #89 stays open for PR 2.

### Review

Self-review (scrutinize):
- Text is autoescaped.
- The read pages write nothing (tested).
- The query move kept the manufacturing suite green.

Deferred minor: the list and outputs query per row (`output_total`, `get_lot_disposition`).
This is fine at demo scale.
