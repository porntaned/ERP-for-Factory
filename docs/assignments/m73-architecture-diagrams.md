# M7.3 — Architecture and Domain diagrams that match the code

Repository `porntaned/ERP-for-Factory`; branch `claude/gracious-sagan-rwlo33` (base `main` `8bbfa9f`);
[Issue #123](https://github.com/porntaned/ERP-for-Factory/issues/123).
Status: **owner approved; implementation in progress** (2026-11-15).

Owner approval: [Issue #123 comment 6891924773](https://github.com/porntaned/ERP-for-Factory/issues/123#issuecomment-6891924773)
(2026-11-15), on the Issue body as edited 2026-11-15 on the owner's instruction in chat.

## Owner decisions (verbatim, Issue #123 comment 6891924773)

> อนุมัติ M7.3 ตามขอบเขตและ "ไฟล์ที่อนุญาตให้แก้" ใน body ของ Issue นี้ (ฉบับแก้ 2026-11-15)
> D1: A (Mermaid ใน Markdown)
> D2: A (ไฟล์เดียว docs/ARCHITECTURE.md)
> D3: ER แสดงแค่ entity + เส้นความสัมพันธ์ + cardinality; state diagram 2 ตัว (ProductionOrder.status, LotDisposition); ใส่ flow การเคลื่อนสต็อก 1 ตัว ตรวจด้วยมือ
> D4: A (pytest ใน suite เดิม ไม่ใช้ DB ไม่แก้ workflow ไม่เพิ่ม dependency)
> D5: อังกฤษ
> D6: ระดับเอกสาร/CI เล็ก ไม่มี reviewer session แยก ผู้ตรวจของเจ้าของตรวจตอน merge; Implementer = sub-agent ของ Manager
> ไฟล์นอกรายการต้องถามก่อน

## Roles

- **Manager** = Claude Code session `session_01MVmjhbuGPaWujXggKSGpsT`: spec, assignment, verification, PR, docs.
- **Implementer** = a sub-agent spawned by the Manager.
- **Review**: none by a separate session (standing rule 7, owner decision D6). The owner's checker reviews at merge.
  The Manager's own checks are self-verification and are labelled so.
- **Owner** merges on GitHub (standing rule 4). No deployment.

## Files allowed to change (closed list, Issue #123)

1. `docs/ARCHITECTURE.md` (new)
2. `tests/docs/__init__.py` (new)
3. `tests/docs/test_architecture_diagrams.py` (new)
4. `docs/PROJECT.md`
5. `README.md`
6. `docs/assignments/m73-architecture-diagrams.md` (this file)
7. `docs/TASKS.md` — only if needed

Any other file needs the owner's approval first.

## Scope

`docs/ARCHITECTURE.md`, in English, with Mermaid blocks. Each checked block is preceded on its own line by a marker
`<!-- architecture-check: NAME -->` and is a fenced ` ```mermaid ` block with one statement per line.

| Marker `NAME` | Diagram | How it is checked |
| --- | --- | --- |
| `modules` | (a) browser → Django (`config.urls`, `demo` views, read-only admin) → 6 domain apps → PostgreSQL; no deployment | test: the apps the `admin` node points to = apps with models in `admin.site._registry`; plus the admin coverage table below |
| `app-dependencies` | (b) cross-app imports as they are, including `inventory ↔ quality` | test: edge set equal (rules below) |
| `domain-er` | (c) the 21 models, relations and cardinality only (no fields); `User` (= `AUTH_USER_MODEL`) as an external node | test: entity set, edge set and cardinality equal; app grouping |
| `production-order-states` | (d) `ProductionOrder.status` (`OrderStatus`) | test: state set = `OrderStatus` values; every transition names an existing function; transitions themselves by hand |
| `lot-disposition-states` | (d) `LotDisposition`, as recorded by `LotDispositionEvent.from_disposition → to_disposition` | as above, against `LotDisposition` |
| `stock-flow` | one stock-movement flow: receipt → transfer → issue/return → consume/output → reversal | by hand; the test only checks that every function it names exists |

Also in `docs/ARCHITECTURE.md`:
- a **read-only admin coverage** table: per app, registered / total models and the models not registered. The test
  compares it with `admin.site._registry` and checks every project model there uses `config.readonly_admin.ReadOnlyAdmin`.
  At `8bbfa9f`: `facilities` 3/3, `catalog` 2/2, `access_control` 1/1, `quality` 2/2, `inventory` 6/8 (not
  `ProductionPosting`, `ProductionPostingReversal`); no `manufacturing/admin.py`; `demo` has no models.
- a short **domain ownership** section (Inventory, Quality, Manufacturing, Accounting not built) pointing at real
  functions. Every backticked dotted reference that starts with a project app (for example
  `` `quality.services.record_inspection` ``) must resolve; the test checks this for the whole file.
- a note that the `inventory ↔ quality` import cycle is shown as it is and is not changed by M7.3.

Links: `docs/PROJECT.md` → Architecture and `README.md` link to `docs/ARCHITECTURE.md` (no SHA in README).

## Comparison rules (Issue #123, D4-A)

**App dependencies.**
- Edge `X → Y` exists when any `.py` file in app `X` has `import Y…` or `from Y… import …` anywhere in its AST,
  **including imports inside functions** (for example `quality/services.py:247`, `:291`).
- Not counted: files under `migrations/`, `tests/` and `config/`; `config` is not a node, as source or target
  (`*/admin.py → config.readonly_admin` is not an edge).
- Not counted: imports within the same app (`X → X`), relative imports, and imports of Django, the standard
  library or other packages.
- Nodes = the 7 project apps in `INSTALLED_APPS`.

**Domain ER.**
- Entity set = `apps.get_models()` of the 6 domain apps (21 at `8bbfa9f`).
- Edge set = every concrete `ForeignKey` / `OneToOneField` between those models, identified by
  (source model, target model, field name): the relationship label in Mermaid is the field name.
- Cardinality (source side first): `ForeignKey` `}o--||` (`}o--o|` when `null=True`); `OneToOneField` `|o--||`
  (`|o--o|` when `null=True`).
- `User` (`AUTH_USER_MODEL`) is an external node. It may be drawn with its edges, but it and every edge touching it
  are **not** in the sets that must be equal (owner ruling).
- Grouping: entities are declared under `%% app: <label>` comment lines; the test checks each entity sits under its
  real app.

**Ground truth at `8bbfa9f`** (from `_meta`, development check, Manager): 21 models; 42 relation fields, of which
9 point to `auth.User` and 33 are between domain models (20 `ForeignKey`, 13 `OneToOneField`). No `ManyToManyField`.

**States.**
- `production-order-states`: `[*] → OPEN` `create_production_order`; `OPEN → CANCELLED` `cancel_production_order`;
  `OPEN → CLOSED` `close_production_order` (all in `manufacturing.services`).
- `lot-disposition-states` (per lot and warehouse): `[*] → HOLD` (no event: `quality.services.get_lot_disposition`
  defaults to `HOLD`); `HOLD → RELEASED` / `HOLD → REJECTED` `record_inspection` (PASS / FAIL);
  `RELEASED → HOLD` `transition_lot_disposition`; `REJECTED → HOLD` `return_rejected_to_hold`.
- These transitions are the Manager's reading of the code; the Implementer confirms them against the code and
  reports any difference instead of drawing it.

**Test constraints.** No database (`apps.get_models()`, `_meta`, `admin.site._registry` and `ast` only; no
`django_db`, no DB-backed `TestCase`); standard library + pytest/pytest-django already in the lock file; Ruff clean.
Mutation tests (the comparison reports a missing and an extra entity / edge / state on a modified copy of the
document text) stay in the suite.

## Not in scope

Code, model, migration or settings changes; fixing the `inventory ↔ quality` cycle; new dependencies or generated
images; workflow changes; infrastructure/deployment or CI diagrams; M7.4–M7.5; `AGENTS.md` and
`docs/MULTI_AGENT.md`. A difference between `AGENTS.md` "Domain ownership" and the code is reported to the owner as a
finding, not fixed.

## Acceptance criteria (Issue #123)

- [x] Owner approval with D1–D6 ([comment 6891924773](https://github.com/porntaned/ERP-for-Factory/issues/123#issuecomment-6891924773)).
- [ ] ER entities and FK/O2O edges equal the code (`User` external, not counted).
- [ ] App dependency edges equal the code under the rules above, including `inventory ↔ quality`.
- [ ] Diagram (a) shows admin as it is: read-only via `config/readonly_admin.py`, 5 apps, no manufacturing, inventory 6/8.
- [ ] States equal the `TextChoices`; every transition names an existing function.
- [ ] RED before GREEN recorded; the check fails on one missing and one extra item.
- [ ] Diagrams render on GitHub (PR file view).
- [ ] No new dependency; no app/migration/settings change; `makemigrations --check` and Ruff pass.
- [ ] Changed files are all in the allowed list.
- [ ] New tests use no database.
- [ ] CI test count = 1207 + the number of new tests.
- [ ] Relative links in changed Markdown: 0 broken; README has no SHA.
- [ ] CI on PostgreSQL 18.6 passes all 3 jobs (cited by the CI comment link).
- [ ] One report when ready to merge (standing rule 8).

## Evidence

### Baseline (development check, `8bbfa9f`, 2026-11-15)

Environment: this session's container; Python 3.14.8 (installed with a newer `uv` in the scratchpad, because the
container's `uv` 0.11.32 could not download 3.14.8); PostgreSQL **16** (local, not the CI version).

- `git fetch origin '+refs/heads/*:refs/remotes/origin/*'`; `git rev-parse --is-shallow-repository` → `false`
  (after `git fetch --unshallow origin` earlier in the session); `git branch -r --no-merged origin/main` → empty.
- `uv sync --locked --all-groups` → no lock change.
- `python manage.py check` → `System check identified no issues (0 silenced).`
- `python manage.py migrate --noinput` → OK.
- `pytest -q -p no:cacheprovider` → **1207 passed** in 229.51s.
