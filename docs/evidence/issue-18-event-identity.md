# Issue #18 — authoritative event-identity evidence

- Repository: `porntaned/ERP-for-Factory` only.
- Issue: https://github.com/porntaned/ERP-for-Factory/issues/18
- Branch: `codex/fix-quality-event-identity`.
- Base main: `a621c8eb71726f7ae03cb71eec9b94aedbb1bcc5` (PR #17 merged).
- Finding 3 only; Findings 1–2 were recovered as already complete, not repeated.
- Manager/implementer `/root` inspected actual GitHub CI through the prepared browser.
  This is self-verification, not local PostgreSQL execution.

## RED

- Test commit: `c3316f35123075f32bc92a841b6fd1dc7b1ce642`.
- [Foundation #64](https://github.com/porntaned/ERP-for-Factory/actions/runs/39718978305),
  [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39718978305/job/119627783398).
- Full suite `uv run pytest -q --tb=short`: **4 failed, 270 passed in 4.58s**.
- All four new cases fail with `DID NOT RAISE DatabaseError`: ordinary ORM and SQL accept
  supplied IDs 1 and 1,000,000,000. This is business-behavior RED after successful setup,
  not a missing migration/import/connectivity failure. Production files are unchanged.
- [Captured browser DOM](issue-18-red-browser.txt) records failing assertions, exact
  checkout, runtime and live PostgreSQL version. The original audit's high-ID-to-HOLD
  counterexample remains on its separate RED branch; it was not skipped or removed.

## GREEN

- Exact implementation: `1c19981778b2f1cd45279de1b30945523d5827e0`.
- [Foundation #65](https://github.com/porntaned/ERP-for-Factory/actions/runs/39719363464),
  [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39719363464/job/119628998006).
- Targeted event-identity and migration modules: **11 passed in 1.36s**.
- Full suite: **281 passed in 5.83s**.
- Django checks: no issues; migration drift: no changes; fresh Quality 0003 applied
  successfully. Job succeeded through Ruff and retained access-policy targeted checks.
- [Captured browser DOM](issue-18-green-browser.txt) records exact checkout, runtime,
  PostgreSQL version, targeted/full outputs, Django checks and fresh migrations. Ruff's
  detailed output was collapsed; its success follows from job/workflow completion.

## Runtime and actual commands

Both captures show Python 3.14.8, Django 5.2.18, psycopg 3.3.6, vendor `postgresql`,
server `18.6 (Debian 18.6-1.pgdg12+2)`. Existing CI runs on GitHub-hosted Ubuntu 24.04
with a disposable PostgreSQL service and synthetic configuration/data.

```text
uv python install 3.14.8
uv sync --locked --all-groups
uv run python --version
uv run python -c "import django, psycopg; print('Django', django.get_version()); print('psycopg', psycopg.__version__)"
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run ruff check .
uv run pytest -q tests/access_control/test_persisted_deactivation.py --tb=short
uv run pytest -q tests/access_control/test_unsaved_user_policy.py --tb=short
uv run pytest -q tests/quality/test_event_identity.py tests/quality/test_event_identity_migration.py --tb=short
uv run pytest -q --tb=short
```

The live connection/version command is in [the workflow](../../.github/workflows/foundation.yml).
The new targeted command was added for GREEN; RED ran all four new cases in the full suite.
Local supplemental checks: `.venv/Scripts/ruff.exe check .` and `git diff --check` passed.
They do not supply database evidence.

## Accepted behavior and traced migration

- Ordinary explicit IDs are rejected with PostgreSQL SQLSTATE `428C9`. No partial event
  remains; authorized service RELEASE/HOLD and exact retry still work.
- New [Quality 0003](../../quality/migrations/0003_authoritative_event_identity.py) sets
  ALWAYS identity while retaining ALTER's table lock, resolves the owned sequence via
  `pg_get_serial_sequence`, compares its next available value with historical max plus
  one, and uses transactional RESTART only if generation is behind. History is not rewritten.
- Three populated-history tests upgrade an accepted high-ID release from 0002, preserve
  all fields, perform a normal HOLD, reverse, insert another legacy event and reapply.
  Sequence-ahead cases include both called and unused state.
- Three empty-history cases preserve sequence state and the correct first generated ID.
  A maximum-bigint history case proves clear SQLSTATE `22003` and atomic migration abort.
- Reverse restores BY DEFAULT and preserves sequence progress/history. The earlier
  migration roundtrip now restores graph leaves in `finally`; it cannot leave 0003 undone.
- The descending-ID trigger test deliberately uses SQL override to reach the existing
  trigger and still asserts its specific ordering rejection. That test was not weakened.
- Services, model fields and migrations 0001/0002 are unchanged. No dependency added.

Design references: PostgreSQL's [identity behavior](https://www.postgresql.org/docs/18/ddl-identity-columns.html)
explains ALWAYS versus BY DEFAULT and explicit SQL override. [ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
documents subsequent-write semantics and locking. [ALTER SEQUENCE](https://www.postgresql.org/docs/18/sql-altersequence.html)
documents transactional RESTART; the production migration avoids nontransactional setval.
The Supabase PostgreSQL best-practices skill's short-transaction/locking guidance was used
as supporting review guidance; this repository does not use a Supabase service.

## Independent review and limits

Reviewer `/root/issue18_scope_review` separately reviewed design, exact implementation
and manager-captured browser evidence; final verdict **ship** —
[independent Scrutinize](../reviews/issue-18-event-identity-independent-review.md).
This is independent evidence inspection, not independent PostgreSQL execution or live
reviewer retrieval from GitHub. No repair cycle was needed.

DDL holds ACCESS EXCLUSIVE and can block readers/writers during migration. Arithmetic
assumes this repository's increment-one/cache-one sequence; administrator-modified
sequence settings were not tested. Bigint exhaustion intentionally aborts for a separate
owner decision. ALWAYS protects ordinary inserts; SQL override and COPY can still supply
IDs and do not inherently require a separately privileged role. Sequence administration
and deliberate direct-SQL bypass are outside this contract. No permissions redesign,
real-data migration, deployment or load testing is claimed.

Finding 4/general CI triggers and Finding 5/README remain pending. CI only adds this
exact branch and the targeted step. Stop at owner-review PR; no merge or deployment.

## Owner-review delivery

- [PR #19](https://github.com/porntaned/ERP-for-Factory/pull/19), opened through the
  prepared browser on 2026-10-22 — [visible proof](issue-18-pr.jpg).
- Documentation head `6bcdabfc1489d281ad3ee2d78c3ad8cead0eb600` passed
  [Foundation #66](https://github.com/porntaned/ERP-for-Factory/actions/runs/39719868596);
  manager inspected its actual browser run summary. Detailed counts above remain tied
  to implementation `1c199817`, not a separate independent execution claim.
- Final relative links/diff were checked. Later delivery changes only add PR linkage
  and screenshot; production/tests/workflow are unchanged from reviewed GREEN.
- Issue #18, PA.5 and owner acceptance remain pending owner merge. No merge, deployment
  or Finding 4/5 work performed.
