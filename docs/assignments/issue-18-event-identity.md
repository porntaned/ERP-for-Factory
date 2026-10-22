# Issue #18 — authoritative Quality event identity

- Repository: `porntaned/ERP-for-Factory` only.
- Issue: https://github.com/porntaned/ERP-for-Factory/issues/18
- Feature branch: `codex/fix-quality-event-identity`.
- Base main: `a621c8eb71726f7ae03cb71eec9b94aedbb1bcc5`.
- Recovery: clean original branch `codex/record-finding2-merge`, HEAD
  `48bf11c36d338d517387172b02707bdf1d1c9db9`; fetched origin/main matches merged
  PR #17. Findings 1–2 and PRs #14/#16/#17 are complete and will not be repeated.
  GitHub browser showed zero open issues before Issue #18 was created.
- Scope: Finding 3 only; prevent ordinary supplied event IDs from blocking a later
  authorized HOLD, and preserve normal operation after upgrading existing high-ID history.
- Dependencies: existing PostgreSQL 18.6 CI, Quality 0001/0002 migrations and service.
- Allowed: new reversible migration, focused Quality tests and existing migration/trigger
  test seams, exact branch CI support, assignment/evidence/review/checklist documentation.
- Exclusions: prior migration rewrites, real data, new dependencies, privilege redesign,
  Finding 4/general CI triggers, README, Inventory, valuation, merge and deployment.
- Manager/implementer/verifier: `/root`; own PostgreSQL CI inspection is self-verification.
- Independent read-only scope reviewer: `/root/issue18_scope_review`; final independent
  implementation/evidence review is required before PR. Roles are recorded only as performed.
- Acceptance: ordinary ORM/SQL explicit IDs rejected without partial history; normal
  release/hold and retries pass; forward migration preserves history and handles existing
  high IDs without rewinding an ahead sequence; empty/reverse/reapply paths pass; existing
  descending-ID trigger still meaningfully tested; targeted/full PostgreSQL, Django checks,
  fresh migrations, drift and Ruff pass at exact recorded SHA.
- Evidence plan: test-only PostgreSQL RED, minimal migration, targeted then regression
  GREEN, independent Scrutinize, then owner-review PR and stop. Preserve separate RED audit branch.
- Repair limit: two cycles for the same finding; third recurrence stops for owner review.

## Proposed boundary

Use PostgreSQL ALWAYS identity for ordinary inserts. A new atomic migration must advance
generation beyond historical max IDs without reducing existing sequence progress. Reverse
restores BY DEFAULT without rewriting history or rewinding generation. Explicit SQL override,
COPY and sequence administration by trusted code remain outside this ordinary-insert contract.
No authentication or privileged-operator protection is claimed.

Local database runtime is not configured. Existing GitHub CI supplies PostgreSQL evidence;
local lint/diff checks are supplementary. GitHub work uses the owner's prepared browser.

## Handoff evidence

- RED `c3316f35123075f32bc92a841b6fd1dc7b1ce642`: **4 failed, 270 passed**.
- GREEN/reviewed implementation `1c19981778b2f1cd45279de1b30945523d5827e0`:
  targeted **11 passed**, full **281 passed** on PostgreSQL 18.6.
- [Commands, runtimes, actual results and CI](../evidence/issue-18-event-identity.md).
- New 0003 migration only; prior migrations/model/service untouched. Existing migration
  restoration and descending-trigger test seams updated to retain meaningful coverage.
- `/root/issue18_scope_review` independently traced design, source and captured CI evidence;
  [final Scrutinize](../reviews/issue-18-event-identity-independent-review.md): **ship**.
  This is independent evidence inspection, not separate runtime execution.
- No repair cycle needed. No merge/deployment or Finding 4/5 work. Next gate: owner-review PR.
