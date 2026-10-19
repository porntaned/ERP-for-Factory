# Project brief

## Goal

Create a reproducible portfolio showing how a small industrial ERP is analyzed, designed, implemented, tested and reviewed. The business is fictional and all demo data is synthetic.

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

## Milestones

1. Foundation: Organization, Plant and Warehouse constraints.
2. Inventory: item, lot, permissions, audit, ledger, synthetic receipt, transfer and history.
3. Manufacturing: versioned BOM, production order, consumption and output.
4. Quality and traceability: inspection, hold/release and lot tracing.
5. Portfolio delivery: demo data, walkthrough, diagrams and reproducible evidence.

## Evidence boundary

Passing a milestone proves only its documented behavior. It does not establish production readiness. HR/payroll, full accounting, advanced planning, external hardware integration and deployment remain deferred.
