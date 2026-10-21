# Issue #11 — PostgreSQL GREEN evidence (M3.3.4)

## Latest verification after M3.3.5 review repairs

- Tested and independently reviewed SHA: `44b466fdd4e9d0134564c77aef7a316c1a2b8b7e`.
- [Foundation #42](https://github.com/porntaned/ERP-for-Factory/actions/runs/39528381765),
  [postgresql-tdd logs](https://github.com/porntaned/ERP-for-Factory/actions/runs/39528381765/job/118988295071).
- Result: **`261 passed in 4.54s`** on PostgreSQL 18.6; Python/Django/psycopg versions and commands
  remain the same as recorded below. Fresh migration `quality.0002_preserve_history_identity` applied
  successfully; Django check, migration drift check and Ruff passed.
- Evidence verifier: `/root`, from actual checkout/runtime/migration/test logs. Independent review:
  [review record](../reviews/issue-11-lot-disposition-independent-review.md).

The additional 17 cases verify event-ID order, stale persisted active status, grant revocation while
waiting for the Lot lock, all four identity guards (sequential and observed concurrent waits),
permitted unreferenced/metadata updates and migration reverse/reapply. Invalid identity/order writes
assert the specific trigger message. See `test_descending_event_id_is_rejected_without_hiding_the_next_decision`,
`test_stale_active_actor_cannot_bypass_persisted_deactivation`,
`test_grant_revoked_while_waiting_for_lot_lock_denies_append`,
`test_recorded_history_prevents_identity_edge_reassignment`,
`test_identity_update_waits_for_new_history_then_rejects_reassignment` and
`test_history_identity_migration_reverses_and_reapplies` in the existing Quality test files.

Repair CI #41 initially reported `259 passed, 2 failed` from unrelated target-code collisions in
the allowed-reassignment fixtures. The fixture correction at `44b466f` removed those collisions and
strengthened rejection assertions; production fixes are in `6253fd2`. The earlier 244-test evidence
below is retained as the baseline before review repairs.

## Baseline identity and scope (before M3.3.5 repairs)

- Recorded: 2026-10-21 by `/root`, acting as manager and CI evidence verifier.
- Verification classification: project self-verification using GitHub Actions; this is not independent Scrutinize.
- Issue: [#11](https://github.com/porntaned/ERP-for-Factory/issues/11).
- Branch: `codex/audit-release-hold`.
- Tested commit: [`7ce4ef84570628234d4097e0b95643bbf38880db`](https://github.com/porntaned/ERP-for-Factory/commit/7ce4ef84570628234d4097e0b95643bbf38880db).
- Latest production change: [`825b34fea7ad16605210ef4760a41627f0965c06`](https://github.com/porntaned/ERP-for-Factory/commit/825b34fea7ad16605210ef4760a41627f0965c06).
- Workflow: [Foundation #39](https://github.com/porntaned/ERP-for-Factory/actions/runs/39526993055).
- Job and logs: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39526993055/job/118983871383).
- Result: GREEN, **`244 passed in 2.71s`**, no failures, errors or skipped tests in the pytest summary.

The workflow checked out the tested SHA above. Only the M3.3.3 handoff/checklist documentation
differs between that SHA and production commit `825b34f`; production and test code are identical.
The existing complete-suite run includes all Quality tests and all regression tests, so no duplicate
test run or new workflow/dependency was needed to record M3.3.4.

## Environment confirmed in job logs

- GitHub-hosted Ubuntu 24.04 runner (OS 24.04.5).
- uv 0.13.1; Python 3.14.8.
- Django 5.2.18; psycopg 3.3.6.
- `vendor=postgresql`.
- `server_version=18.6 (Debian 18.6-1.pgdg12+2)`.
- Fresh PostgreSQL service using `postgres:18.6-bookworm` and synthetic CI configuration/data.

## Actual commands and results

| Command / step | Observed result |
| --- | --- |
| `uv sync --locked --all-groups` | Locked dependencies synchronized successfully |
| `uv run python --version` and Django/psycopg version print | Versions above confirmed |
| `uv run python manage.py check` | `System check identified no issues (0 silenced).` |
| Workflow PostgreSQL connection check (`connection.ensure_connection()`, vendor assertion, `SHOW server_version`) | PostgreSQL vendor and 18.6 server confirmed |
| `uv run python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `uv run python manage.py migrate --noinput` | Fresh migrations passed, including `quality.0001_initial... OK` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run pytest -q --tb=short` | `244 passed in 2.71s` |

## Acceptance evidence in the executed suite

The [service tests](../../tests/quality/test_lot_disposition.py) call the real Quality interfaces.
The [database tests](../../tests/quality/test_postgresql_constraints.py) execute ORM/direct writes
against PostgreSQL, with separate connections for concurrency. All tests below are included in Run #39.

| Behavior | Executed tests and assertions |
| --- | --- |
| Pair scope and fail-safe initial state | `test_missing_history_is_hold_for_exact_lot_and_warehouse` and `test_disposition_is_independent_for_each_lot_warehouse_pair`: no history returns HOLD without insertion; another Lot or Warehouse remains HOLD |
| Decision attribution and transitions | `test_release_then_hold_records_an_exact_attributed_chain`: HOLD → RELEASED → HOLD records exact actor, pair, reason, UUID and aware timestamp; query returns the final state |
| Authorization | `test_non_quality_roles_cannot_record_a_decision`, `test_quality_grant_for_another_warehouse_does_not_authorize_target`, `test_non_operational_actor_cannot_record_a_decision`, `test_superuser_has_no_implicit_quality_bypass`, `test_revoked_quality_grant_cannot_record_a_decision`: denied calls add no history |
| Organization boundary | `test_lot_and_warehouse_must_belong_to_same_organization`, `test_query_rejects_a_cross_organization_pair`, `test_direct_write_rejects_cross_organization_pair`: invalid pairs fail through service and direct insert paths |
| Input and state validation | `test_invalid_or_noop_transition_adds_no_history`, `test_reason_must_be_nonblank`, `test_request_key_must_be_a_uuid`, `test_stale_expected_state_conflicts_without_adding_history`: invalid/no-op/stale commands add no event |
| Retry | `test_exact_retry_returns_the_original_event_without_duplicate_history`, `test_reused_request_key_with_different_payload_conflicts`: identical retry returns the original event; changing any locked payload field conflicts |
| Database constraints and references | `test_required_event_fields_reject_null_at_database_boundary`, `test_state_and_reason_constraints_reject_direct_invalid_writes`, `test_invalid_references_fail_at_database_boundary`, `test_request_id_is_unique_at_database_boundary`, `test_recorded_event_protects_referenced_records`: PostgreSQL rejects invalid values/FKs/duplicate keys; ORM deletion raises ProtectedError |
| Time | `test_created_at_is_required_and_direct_insert_supplies_aware_server_time`: timestamp field is non-null and valid direct insert supplies an aware time between call bounds |
| Chain and immutability | `test_direct_write_cannot_forge_the_event_chain`, `test_recorded_event_cannot_be_updated_or_deleted`: forged from-state, UPDATE and DELETE are rejected and the original event remains |
| Failure path | `test_service_failure_rolls_back_without_partial_history`: a stale command after an existing direct event conflicts, adds no event and preserves current state |
| Concurrent retry | `test_concurrent_exact_retries_converge_on_one_event`: two service calls with the same key return one event ID and leave one row |
| Concurrent distinct commands | `test_concurrent_distinct_commands_allow_one_authoritative_transition`: one success and one defined conflict, with one row |
| Concurrent direct inserts | `test_concurrent_direct_inserts_serialize_one_transition`: one committed insert and one IntegrityError, with one row |
| Regression | Full suite contains 70 Quality cases plus the 174 existing cases from access_control, catalog, facilities/foundation and inventory; all 244 passed |

## Repair history and limits

[Foundation #37](https://github.com/porntaned/ERP-for-Factory/actions/runs/39453854257) initially
reported `242 passed, 2 failed`: reused request IDs with changed expected/target disposition returned
validation errors before conflict resolution. Production commit `825b34f` moved existing-request
resolution before new-transition validation. [Foundation #38](https://github.com/porntaned/ERP-for-Factory/actions/runs/39454155496)
then passed all 244 tests, and Run #39 confirms GREEN at the later tested SHA recorded above.

This evidence establishes the observed test results, not an independent implementation verdict.
The stale-command test does not inject a database failure after a successful insert. The concurrency
tests cover the specific two-caller scenarios listed above, not every possible schedule or privileged
database operation. Exact-Warehouse authorization is exercised through the service; direct-insert
tests establish the listed integrity constraints, not database-level role authorization.
There is no stock ledger, inspection or movement-enforcement claim. Independent Scrutinize and
the owner-review PR belong to M3.3.5; their subsequent status is recorded in the review and assignment
records. No merge or deployment is authorized by this report.
