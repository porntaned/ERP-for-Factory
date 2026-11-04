# Independent review — M4.4.1 registry (PR #51) and M4.4.2 hardening

Reviewer: separate read-only agent, 2026-11-04, following [Scrutinize](../SCRUTINIZE.md).
It read code and diffs only; no database was reachable, so it ran no tests. The implementer
did not take part in the review pass.

## PR #51 — `f69df51..7d2ed62` (already merged; retroactive)

Verdict: **ship**. Production logic traced as correct: insert-or-keep then owner read-back
under READ COMMITTED, trigger ordering, savepoint rollback in services, reverse paths and
migration dependencies.

| # | Severity | Finding | Repair in M4.4.2 |
| --- | --- | --- | --- |
| 1 | Medium | Race test used one Lot, so the second command waited on the Lot lock and failed at the service pre-check; the trigger race and the services' `except IntegrityError` branches were untested. | Replaced by `test_cross_command_race_is_decided_at_the_registry` (4 orderings) using a second Lot and a second actor. Mutation check: disabling only the except-branch mapping in the three services made all 4 fail with `IntegrityError`; files restored. |
| 2 | Medium | quality/0004 abort branch and "legacy NULL keys not registered" untested; abort is per-migration atomic only. | Added `test_quality_backfill_aborts_when_a_disposition_key_was_used_by_a_receipt` (asserts inventory 0007 applied, quality 0004 not) and `test_legacy_null_transfer_survives_upgrade_unregistered`. |
| 3 | Low | Direct disposition insert took the registry key before the Lot lock (trigger name order), allowing a deadlock on concurrent misuse. | quality/0005 renames the trigger to `quality_lot_disposition_zz_request_key` so it fires after `quality_lot_disposition_validate_insert`; the registry is taken last. |
| 4 | Low | `stockledgerentry_set.first()` without ordering. | `order_by("id")`. |

## Branch `codex/inventory/m44-hardening` at `9f3ffb6`

Verdict: **fix-then-ship**, biggest reason finding 1 (same flaw in the new race test).

| # | Severity | Finding | Repair |
| --- | --- | --- | --- |
| 1 | Medium | New race test repeated the same-Lot flaw. | Folded into the 4-ordering registry race test above. |
| 2 | Low | 0008 copied the whole shared trigger function; a `CHECK ... NOT VALID` is simpler. Model `null=True` differs from DB rule. | 0008 is now `transfer_request_id_required CHECK (request_id IS NOT NULL) NOT VALID` (preceded by `SET CONSTRAINTS ALL IMMEDIATE` so it runs inside a transaction holding deferred FK checks); model difference documented in the migration. |
| 3 | Low | No test for legacy NULL across 0007/0008 or for 0008 reverse; quality/0004 abort untested. | `test_legacy_null_transfer_survives_upgrade_unregistered`, `test_require_key_constraint_reverses_and_reapplies`, and the abort test above. |
| 4 | Nit | Test name `_with_foreign_key` misleading; new CI steps re-run tests the full suite runs. | Renamed `_with_key_owned_by_receipt`. CI steps kept, consistent with the existing per-suite pattern. |

The repairs are self-verified by the implementer (below); they were not re-reviewed.

## Implementer verification after repairs (local, development only)

PostgreSQL 16.15, Python 3.14.6 (project pins 18.6 / 3.14.8). Full suite 675 passed; Ruff
clean; `makemigrations --check` clean. On a fresh database: `migrate`, `migrate inventory
0006` (reverses 0008, quality 0005/0004, inventory 0007), `migrate` again: all succeeded; the
Quality trigger order afterwards is `reject_mutation`, `validate_insert`, `zz_request_key`.
CI on PostgreSQL 18.6 is recorded in the PR.
