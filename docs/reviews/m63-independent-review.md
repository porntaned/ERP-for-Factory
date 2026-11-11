# Review — PR #111 (Issue #108, M6.3: trace Lots through every production level)

**Type: independent review by a separate session** (Claude Code session `session_01MVmjhewJFpBspSkUbCyJN4`,
created by the Manager session; read-only, Scrutinize per `docs/SCRUTINIZE.md`). It is not an owner review.
Date 2026-11-11. Reviewed head `afcea7d` (branch `claude/keen-feynman-jkijlw`), base `main` `94a3e38`.
Spec: `docs/assignments/m63-lot-trace.md`.

The Reviewer was given only the PR number, the Issue number and the spec path. "Report" is the
Reviewer's message as received, copied by the Manager without edits other than restoring the `<` and
`>` characters that the message transport had escaped. "Manager disposition" is the Manager's own and
is not part of the review.

## Report

Review type: INDEPENDENT REVIEW by a separate Claude Code session (Reviewer role, docs/MULTI_AGENT.md; Scrutinize per docs/SCRUTINIZE.md). Read-only: no edits, commits, pushes or PR comments.

PR #111 (claude/keen-feynman-jkijlw), head afcea7d, base main 94a3e38. Issue #108. Spec docs/assignments/m63-lot-trace.md.

### 1. Intent
Follow the M5.3 one-level links through every production level, in both directions, and show where each traced Lot is now (balance and disposition per warehouse). Show it read-only on a search page and a trace page, and add one WIP level to the demo. The change is warranted (the spec documents that multi-level chains are already possible). A smaller design that does the same job would be a recursive CTE, but that would mean writing the M5.3 netting again in SQL. Reusing `_per_order_lot` in Python, one batch per level, is simpler and guarantees the same netting as level 1. I agree with the chosen design.

### 2. What I traced (PR claims vs what I verified)
- `trace` (manufacturing/genealogy.py:134) → `_level` (:109) → `_per_order_lot` (unchanged, :40) with `lot_id__in=frontier`.
  - Backward: the OUTPUT net per (order, lot) picks the orders. Then all CONSUME nets of those orders, which is exactly `inputs_of`, batched.
  - Forward: the CONSUME net per (order, from_lot) gives `consumed`. Then the OUTPUT nets of those orders, which is exactly `outputs_of`.
  - Grouping by (order, lot) with `__in` gives the same per-pair nets as the single-Lot queries, so reversed postings and zero nets are excluded the same way.
  - `seen` holds the start Lot, so a cycle back to the start is marked repeat. The first edge to reach a Lot (after the sort) expands it. `lots[r[0]]` is always loaded, because from-Lots are the start Lot or earlier `to` Lots.
  - `in_bulk(set())` issues no query, so the stated bound of 1 + 4 per level + 1 holds.
- `lot_positions` (:182):
  - Balances: GROUP BY (lot, warehouse) with HAVING sum <> 0.
  - Latest disposition: DISTINCT ON (lot, warehouse) ordered by -id. This is the same rule as `quality.services.get_lot_disposition` (quality/services.py:115) and `get_rejected_warehouses` (:126).
  - A pair is shown if its balance is nonzero, or if it is REJECTED at zero balance. The test checks every position against `get_stock_balance` and `get_lot_disposition`.
- Views (demo/production_views.py:105, :122): `@login_required` on both. GET only, no writes. A NUL character makes the form invalid. Merging the Lots of both directions with a dict keeps the start Lot first.
- Templates: output is autoescaped. The trace page is read-only.
- Seed: new Lots and keys only, all through the real commands with existing grants. The FINAL inspection is guarded by the HOLD check, so a rerun replays. Existing tests were adapted without removing assertions (test_production_path.py, test_production_screens.py, test_quality_screens.py): I read each change.
- Docs: the DEVELOPMENT.md walkthrough and the corrected M5.4 shell snippet (old text marked historical) match the behaviour I saw. The M5.3 note is present.

### 3. Development checks (not evidence of record)
Local PostgreSQL 16 cluster, Python 3.14, on afcea7d.
- `pytest -q tests/manufacturing/test_trace.py tests/manufacturing/test_wip_demo.py tests/web/test_trace_screens.py` → **29 passed**.
- A throwaway probe test (scratchpad only, not in the repo), seeded demo, logged in as demo-warehouse:
  - Whole-request query counts for `/lots/<pk>/trace/`: LAMP-BR30-0001 21, L-0004 21, L-0003 17. All 200, and the count is bounded.
  - Search `"  LAMP-BR30-0001 "` → 302 to its trace (spaces trimmed).
  - `"<b>x</b>"` → escaped (not rendered raw).
  - A 5000-character code → 200.
  - Thai Unicode code → 200.

CI evidence of record: check run postgresql-tdd (run 42952879338) was **in progress** when I looked. No CI comment is on the PR yet, so I cannot cite PostgreSQL 18.6 results.

### 4. Findings (most severe first)
No blocking or major defect found in code or tests.

1. **Low (documentation accuracy): stale status in the slice record.**
   - Where: docs/assignments/m63-lot-trace.md:5 says "not yet reviewed; PR not yet opened", and :8-9 say "Reviewer = … (not started)".
   - Why it matters: PR #111 is open and this independent review exists. AGENTS.md says documentation must describe the state as it is and must label review accurately.
   - Smallest change (docs-only commit):
     - Set Status to "PR #111 open; independent review by a separate session: ship, no code findings (2026-11-11)", and mark the old text historical.
     - Update the Reviewer line.
     - Replace :216 "linked here once the PR exists" with the link to the CI comment once CI posts it.
2. **Low (documentation deliverable missing): the review record.** The spec's Documentation section lists `docs/reviews/m63-independent-review.md` for the same PR, and it is not on the branch. Smallest change: add it from this report, with the review type stated on its first lines (AGENTS.md naming rule).
3. **Info (UX semantics, no change required by the spec):** `lot_positions` shows "HOLD" for any warehouse with stock and no disposition event, for example material on LINE-1. That is the `get_lot_disposition` rule the spec requires. A recall reader could still take it as "quarantined" when it means "not inspected there". An optional one-line caption under the positions table would help; or leave it.
4. **Info (test coverage):** `test_queries_grow_with_levels_not_lots` (tests/manufacturing/test_trace.py:261) widens only a forward level, by adding more orders. The backward direction is bounded only on a narrow chain. The code is batched the same way in both directions (:109-131), so this is not a defect. Optionally, add an order that consumes several Lots and assert the same bound backward.
5. **Info (owner rulings to confirm, already listed in the PR body):**
   - Search is exact and case-sensitive.
   - `lot_positions` reads `LotDispositionEvent` directly in manufacturing rather than through a Quality function. This duplicates the "latest by id" rule a third time; a future Quality batch reader would remove it.
   - A Lot reached twice within the same level (not a cycle) is also shown as "ซ้ำ (ไม่ขยายต่อ)".

### Verdict
**fix-then-ship.** The fixes are documentation only (findings 1–2): stale status and review lines, the missing `docs/reviews/m63-independent-review.md`, and the CI link. Under AGENTS.md these documentation-only commits need no new review. No code change is required. Merge only after the postgresql-tdd CI comment on the final head shows green on PostgreSQL 18.6, since it was still running when I reviewed.

## Manager disposition (Manager session, repair round 1 of 2)

| # | Disposition |
|---|---|
| 1 | Fixed (documentation only): status, Reviewer line and CI link in the spec. |
| 2 | Fixed: this file. |
| 3 | Not changed: the spec requires the `get_lot_disposition` rule and lists no caption; left for the owner to decide. |
| 4 | Not changed: optional coverage; the Reviewer traced the same batching in both directions. |
| 5 | Owner to confirm (listed in the PR body and the final report). |

The fixes in this round are documentation only; under AGENTS.md they need no new review.
