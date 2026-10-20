# Independent Scrutinize — Issue #1 TDD RED foundation

- Reviewer: `/root/independent_scrutinize`
- Reviewed artifact: the complete working-tree snapshot that became commit
  [`31ba6be9cf94f50f28267734f7040a4592db3545`](https://github.com/porntaned/ERP-for-Factory/commit/31ba6be9cf94f50f28267734f7040a4592db3545)
- Review type: independent, read-only code and workflow trace
- Verdict after repair: ship the TDD RED foundation snapshot

## Intent and smaller-alternative check

The change prepares a pinned Django/PostgreSQL environment and writes Issue #1 acceptance tests
before implementation. A single sentinel test would be smaller, but it would not preserve the
required contracts for scoped uniqueness, foreign keys, code format, deletion protection, Thai
text and concurrent writes. The reviewer found no need for Docker Compose or new orchestration;
the GitHub Actions PostgreSQL service is sufficient.

## Findings and repair

### Deferred foreign-key checking could produce a false failure

- Finding: the invalid-parent test originally used pytest-django's normal transaction wrapper,
  while PostgreSQL may defer foreign-key checking until the outer transaction ends.
- Consequence: a correct FK could produce `DID NOT RAISE` inside the nested `atomic()` block.
- Repair: both invalid-parent cases now use `django_db(transaction=True)`, so the `atomic()` block
  commits and forces the deferred check inside `pytest.raises`.
- Evidence: `tests/foundation/test_postgresql_constraints.py` covers Plant → Organization and
  Warehouse → Plant with the corrected transaction semantics.

### A downstream PROTECT could mask an incorrect CASCADE

- Finding: deleting an Organization from a graph containing both Plant and Warehouse could raise
  from Warehouse → Plant even if Organization → Plant were incorrectly configured as CASCADE.
- Consequence: the test could pass for the wrong relationship.
- Repair: deletion protection now uses two independent graphs: Organization with Plant only, and
  Plant with Warehouse.
- Evidence: `tests/foundation/test_hierarchy.py` has separate tests for each relation.

### Publishing target could point at the governance branch

- Finding: the local feature branch initially tracked `origin/chore/project-foundation`.
- Consequence: an ambiguous push could fail or target the wrong branch.
- Repair: the first publish used
  `git push --set-upstream origin feat/warehouse-foundation`; the local branch now tracks the
  matching remote feature branch.

The independent re-review confirmed both test repairs, found no new blocker or major issue in
those patches, and reported `git diff --check` passing. The reviewer did not run pytest or GitHub
Actions; PostgreSQL execution evidence is recorded separately in
[`issue-1-tdd-red.md`](../evidence/issue-1-tdd-red.md).
