# Issue #18 — Independent Scrutinize

- Reviewer: `/root/issue18_scope_review`, separate read-only agent; manager transcribed
  this report from its design review and final implementation review responses.
- Exact implementation: `1c19981778b2f1cd45279de1b30945523d5827e0`.
- Base: `a621c8eb71726f7ae03cb71eec9b94aedbb1bcc5`.
- No edits, test execution, browser interaction, Git writes or GitHub mutation by reviewer.
- Scope: Finding 3 only. Final code verdict is distinct from earlier approval of the design.

## Intent and smaller alternative

Prevent ordinary supplied event IDs from disabling a later legitimate HOLD, including
history accepted before upgrade. A database-only migration is appropriately small;
service/model changes or history rewriting would add unnecessary scope.

## Trace

- `quality/migrations/0003_authoritative_event_identity.py:12`: ALWAYS identity rejects
  ordinary explicit IDs at PostgreSQL's boundary.
- `:24`: resolves the owned sequence through `pg_get_serial_sequence`/regclass instead
  of assuming its name in production SQL.
- `:29`: reads historical maximum while ALTER's ACCESS EXCLUSIVE lock prevents ordinary
  inserts racing history/sequence inspection.
- `:31`: computes the next available value from last_value/is_called and historical max
  plus one. Numeric arithmetic avoids overflow; exhaustion raises `22003` at `:36`.
- `:41`: transactional RESTART only for a behind sequence; ahead/unused state is preserved.
- `:53`: reverse restores BY DEFAULT without rewinding generation or changing events.
- Existing service, business model fields, authorization, locking, typed history and
  earlier migrations remain unchanged.

## Verification

Reviewer independently inspected source and manager-captured browser evidence; no
independent PostgreSQL execution or live reviewer GitHub retrieval is claimed.
[Actual commands and CI links](../evidence/issue-18-event-identity.md).

- `tests/quality/test_event_identity.py:10`: four ORM/SQL × small/high-ID cases assert
  `428C9`, no partial event, successful service RELEASE/HOLD and exact retry.
- `tests/quality/test_event_identity_migration.py:65`: three historical high-ID/sequence
  modes prove upgrade, preserved contents, HOLD, reverse and reapply with more history.
- `:135`: three empty/sequence modes preserve is_called and first generated value.
- `:155`: maximum historical bigint aborts atomically, preserving BY DEFAULT and sequence
  state without partial test history. Fixture at `:15` restores graph leaves in finally.
- `tests/quality/test_postgresql_constraints.py:56`: prior migration roundtrip restores
  graph leaves; `:231` still reaches and asserts the existing descending-ID ordering error
  through deliberate SQL override. It was not removed or weakened.
- RED capture: exact checkout `c3316f35123075f32bc92a841b6fd1dc7b1ce642`, four business
  `DID NOT RAISE DatabaseError` failures and **270 passed**.
- GREEN capture: exact checkout `1c19981778b2f1cd45279de1b30945523d5827e0`, Python 3.14.8,
  Django 5.2.18, psycopg 3.3.6, PostgreSQL 18.6. Targeted **11 passed in 1.36s**;
  full suite **281 passed in 5.83s**. Django clear, no migration drift, fresh 0003 OK.
- Successful job/workflow covers Ruff and retained access-policy tests; detailed Ruff
  output was collapsed in the capture the reviewer inspected.
- Reviewer ran `git diff --check a621c8eb71726f7ae03cb71eec9b94aedbb1bcc5 1c19981778b2f1cd45279de1b30945523d5827e0` successfully.

## Report and limits

No blocking findings; no repair cycle required. Both future ordinary explicit-ID writes
and legacy high-ID history are addressed while audit records remain intact.

DDL can block readers/writers while holding ACCESS EXCLUSIVE; keep the migration short.
Sequence arithmetic assumes repository-default increment one/cache one; administrator
changes/cached configurations were not tested. ALWAYS is an ordinary-insert boundary:
SQL override, COPY and sequence administration remain outside it, and override is not
inherently limited to a separately privileged role. Bigint exhaustion deliberately stops
migration for a separate owner remedy. No deployed/live-data/load validation is claimed.
Later documentation changes require final diff/link checks.

## Verdict

**ship — the exact reviewed migration fixes ordinary explicit-ID acceptance and upgrades
legacy high-ID history without rewriting it, with 11 targeted and 281 full PostgreSQL
tests passing.** Owner-review PR is the next gate; no merge or deployment authority granted.
