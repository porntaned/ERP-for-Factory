# Issue #15 — Independent Scrutinize

- Reviewer: `/root/issue15_final_review`, separate read-only agent; manager transcribed
  this report from the review response. Reviewer did not edit implementation or run tests.
- Reviewed head: `d132237211c5abdc509679da91b7b12566dff38c`.
- Base: `eba63622495c6b065ad0abcd8e652676f9189d20`.
- Scope: audit Finding 2 only. A prior agent `/root/issue15_independent_review` performed
  a preliminary code trace but did not complete its final verdict before interruption.
  The final reviewer independently assessed code and evidence after work resumed.

## Intent and smaller alternative

Deny never-saved User instances through both shared Warehouse policies even when a
supplied PK matches an authorized persisted user. One shared-helper condition is the
smallest fix. Separate endpoint checks would duplicate it; a user-existence query would
still accept the colliding instance.

## Trace

- `access_control/policies.py:31`–`:38`: model-type guard precedes `_state` access;
  PK-less instances fail at `:34`, adding-state instances at `:35`. Authentication and
  in-memory active guards remain intact.
- Boolean entry at `:41` calls the helper at `:49`, returns False at `:53` for unsaved
  users before grant lookup, and retains exact user/warehouse/role matching and persisted
  active filtering at `:57` for accepted instances.
- QuerySet entry at `:63` calls the same helper at `:65`, returns `Warehouse.objects.none()`
  at `:66` for unsaved users, and retains persisted-active filtering at `:70` and distinct
  results at `:72`. No additional query, state mutation or transaction behavior is added.
- `access_control/models.py:15`–`:38` retains real foreign keys, valid roles and unique
  grants. Fixtures save synthetic users and real facility rows.
- `tests/access_control/test_unsaved_user_policy.py:9`–`:63`: real QUALITY grant,
  ORM-loaded positive control, and six cases across both interfaces with matching,
  verified nonexistent and absent PKs. Unsaved instances are active/authenticated with
  `_state.adding=True`; passwords are unusable. Policy results are not mocked.
- Existing role-policy tests retain saved-user positives, revocation, user/warehouse/
  plant/organization isolation, duplicate-free results, invalid/empty/Unicode/mixed role
  inputs, superusers and non-operational users.
- Existing persisted-deactivation tests at `:9`, `:29`, `:49` retain stale-instance and
  deferred-evaluation coverage from Finding 1.
- Workflow adds this exact feature branch and targeted test step only; PostgreSQL service
  and main-targeting PR trigger remain. General CI-trigger remediation is still pending.

## Verify

Reviewer independently inspected manager-captured browser DOM files, not the live GitHub
site or a separate PostgreSQL execution. [Evidence and commands](../evidence/issue-15-unsaved-user-policy.md).

- GREEN capture records exact checkout `d132237211c5abdc509679da91b7b12566dff38c`, Python
  3.14.8, Django 5.2.18, psycopg 3.3.6 and PostgreSQL vendor/server 18.6. Persisted module:
  **3 passed in 0.47s**; new module: **6 passed in 0.37s**; full: **270 passed in 3.17s**.
- RED capture demonstrates two matching-PK failures (True and a returned Warehouse),
  **2 failed, 268 passed in 4.68s**, after successful environment setup. The browser run
  overview associates that run/job with test commit `7c9c1ac81beaa71776516e5aea29c9d7bc3e7288`.
  Reviewer separately inspected the appended overview and confirmed that association;
  the preliminary missing-SHA evidence limitation is resolved.
- Reviewer ran `git diff --check eba63622495c6b065ad0abcd8e652676f9189d20 d132237211c5abdc509679da91b7b12566dff38c`
  successfully and examined base-to-head and RED-to-GREEN diffs.
- Local installed Django source confirms default adding state is True and normal
  loading/save completion makes it False. No schema, dependency, retry, write or locking
  behavior changed; no new concurrency mechanism or partial-failure path is introduced.

## Report and limits

No blocking finding within Finding 2; no repair cycle required. The shared guard closes
both specified paths and preserves Finding 1's database-active checks.

This checks ordinary Django instance state, not trusted Python code that deliberately
changes `_state` or identity attributes. Evaluated QuerySet caches and check-then-write
races remain outside the read-policy contract. No HTTP-authentication exploit, deployed
system validation or load testing is claimed. Finding 3 and other audit findings remain
unresolved. Subsequent documentation changes require final diff/link checks.

## Verdict

**ship — Finding 2 is fixed minimally through the shared helper, with six focused
regressions and 270 passing PostgreSQL tests at the exact reviewed implementation SHA.**
Complete evidence/checklist documentation and proceed to owner-review PR only; do not
merge, deploy or start Finding 3.
