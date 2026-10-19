# Project brief

## Outcomes

This public portfolio must demonstrate two verifiable outcomes:

1. A functioning industrial ERP for a fictional LED assembly factory, delivered in small reviewable milestones.
2. A Multi-Agent software factory that assigns bounded roles, records handoffs and proves implementation, verification and review with GitHub evidence.

The business is fictional and all demo data is synthetic.

## Pilot factory

- One company and one LED assembly plant.
- Raw-material warehouses `RM-A` and `RM-B`; finished-goods warehouse `FG`.
- One product and one assembly line initially.
- Planned roles: warehouse, production, quality and approver.

These are demo assumptions, not claims about rules shared by every factory or industrial estate.

## Architecture

- Django modular monolith.
- PostgreSQL is the authoritative transactional database.
- Django Templates and Bootstrap when screens are introduced.
- pytest, pytest-django, Ruff and GitHub Actions.
- Small GitHub issues with explicit acceptance criteria and evidence-backed pull requests.

## Multi-Agent delivery

[The execution contract](MULTI_AGENT.md) defines actual agent roles, assignments, handoffs, evidence, repair limits and stop conditions. Native Codex agents are the default. Noodle remains an optional tool; the portfolio evaluates results and evidence.

## Milestones

1. Foundation: Organization, Plant and Warehouse constraints.
2. Inventory: item, lot, permissions, audit, ledger, synthetic receipt, transfer and history.
3. Manufacturing: versioned BOM, production order, consumption and output.
4. Quality and traceability: inspection, hold/release and lot tracing.
5. Portfolio delivery: ERP demo plus reproducible Multi-Agent evidence.

## Evidence boundary

Passing a milestone proves only its documented behavior. It does not establish production readiness. HR/payroll, full accounting, advanced planning, external hardware integration and deployment remain deferred.
