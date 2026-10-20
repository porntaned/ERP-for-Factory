# Issue #9 TDD RED independent review

- Reviewer: `/root/m32_red_independent_review`
- Reviewed commit: [`a58c6eb02efdb324c068343476bfc317f4c5657e`](https://github.com/porntaned/ERP-for-Factory/commit/a58c6eb02efdb324c068343476bfc317f4c5657e)
- CI evidence: [Foundation #26](https://github.com/porntaned/ERP-for-Factory/actions/runs/39435149544), [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39435149544/job/118670107134)
- Method: `docs/SCRUTINIZE.md`

## Intent and simpler alternative

The tests lock the smallest explicit Warehouse-scoped role assignment and evaluation boundary before
implementation. Django Groups and model permissions alone cannot express Warehouse instance scope;
Django's built-in User plus one assignment model and two narrow policy functions is the smaller
adequate design.

## Trace and verification

- The exact commit contains no `access_control` application, model, migration or policy module.
- The tests collect before implementation and fail through the single guard in
  `tests/access_control/conftest.py` when the assignment model is absent.
- Schema tests lock the four fields, four roles, required references, exact-tuple uniqueness,
  protected deletion and concurrent duplicate behavior.
- Policy tests lock exact Warehouse and User predicates, cross-Plant and cross-Organization
  isolation, inactive/anonymous/unsaved denial, fail-closed roles and no implicit superuser bypass.
- Grant revocation is traced from a successful boolean check and authorized-Warehouse query through
  `assignment.delete()` to denial and an empty query.
- Every synthetic User created by the test surface receives an unusable password.
- The concurrency harness uses separate thread connections and transactions, synchronizes two
  writes and requires one success, one `IntegrityError` and one resulting row.

The first review found that grant revocation was claimed but not tested. The repaired exact commit
adds that missing path without changing production code.

## CI result

GitHub Actions checked out the exact reviewed SHA, connected to PostgreSQL 18.6, passed Django
checks, migration drift, fresh migrations and Ruff, then ran the full suite. All 115 existing tests
passed. All 58 new cases ended only with the expected absent-contract message. Final result:
`115 passed, 58 errors in 1.42s`.

No blocker, major or minor finding remains.

**Verdict: `ship` for the RED stage — implementation may begin.**
