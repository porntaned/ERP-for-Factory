# Issue #26 — independent M4.1 Scrutinize

- Reviewer: `/root/m41_final_review`, separate read-only agent.
- Reviewed head: `040b883c313cb70e05bdaef57839a4f07bcd3ee3` against main
  `e806b6491d962f8124cc17d902eca2a692485ad1`.
- Scope: source, migration, tests and contract; no edits, PostgreSQL execution,
  live GitHub/CI retrieval or Git writes by the reviewer. Root separately verified
  [final PostgreSQL CI](https://github.com/porntaned/ERP-for-Factory/actions/runs/39802033213).

## Intent and smaller alternative

Provide exact, immutable stock history and nonnegative Lot/Warehouse balances while
preventing parent deletion or PK replacement from changing the meaning of history.
The reviewer considered native immediate referential constraints for direct parents
instead of duplicating them in triggers; ancestor Item/Plant guards are needed where
the ledger has no direct foreign key.

## Trace

- `inventory/fields.py` and `inventory/models.py` retain exact numeric deltas with
  explicit precision/range checks, protected parents, reason and database identity/time.
- `inventory/migrations/0002_stock_ledger.py` locks Lot, Item, Warehouse and Plant,
  validates persisted organization identity, sums the pair and rejects negative totals;
  it also blocks ledger rewrites and history-bearing identity-edge changes.
- `inventory/migrations/0003_preserve_stock_parent_lifetime.py:41` changes the three
  direct ledger FKs to immediate `RESTRICT`, including same-statement replacement.
  Lines 46–85 guard Item/Plant DELETE and distinct PK changes, reject fixed snapshots
  and preserve unchanged PK/metadata updates. Reverse restores original deferred FKs.
- `inventory/services.py` reads an internal persisted-pair snapshot, not a posting
  authorization or stock reservation.

## Verify and report

The reviewer inspected the final tests for direct-parent and ancestor removal at zero
balance (`tests/inventory/test_stock_parent_lifetime.py:13`), one-statement direct
replacement (`:32`), isolation and no-op controls (`:52`), permitted prehistory
replacement (`:73`), both transaction orders with observed blockers for five parent
types (`:90`), and reversible migration with data retained (`:153`). It also traced
quantity, concurrency and rollback coverage. `git diff --check` passed in the
reviewer's read-only pass.

**No actionable defect found.** These are inspected test paths, not independently
executed tests. Root observed the final commit's PostgreSQL CI separately:
[121 targeted and 402 full tests passed](../evidence/issue-26-stock-ledger.md#implementation-repairs-and-final-postgresql-evidence).
Storage constraints do not establish Warehouse posting permission, Quality eligibility,
idempotency, reversal or M4.2 behavior. Ordinary privileged trigger disabling,
TRUNCATE and database administration remain outside this contract.

## Verdict

**`ship` for owner-review PR** — the reviewed migration and tests close the identified
lifetime bypass within the ordinary-write boundary; exact-head PostgreSQL CI passed
as recorded independently by the manager. Owner acceptance, merge and deployment are
separate decisions.
