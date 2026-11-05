# M5.5 — Manufacturing screens (read + record)

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `b5aa7df`.
[Issue #89](https://github.com/porntaned/ERP-for-Factory/issues/89). Status: **PR 1 (read-only) in
progress**. The owner wants to see production on the web and try it themselves. In plan mode
they chose the full flow, delivered in two PRs, and approved the plan (chat, 2026-11-05).

## Approach

The screens extend the existing web (Django Templates + Bootstrap, `demo/`, as in M4.6). No new
dependency, schema, migration or trigger.
- A SPA was not chosen: it needs a new API and new dependencies, which need separate approval.
- Django admin was not chosen: it is not a user-facing UX.

Every write goes through `manufacturing/services.py`. The screens only choose what to show and
turn command errors into Thai messages.

## PR 1 — read-only pages

| URL | Shows |
|---|---|
| `/production/` | orders: number, product and BOM version, quantity, net output, status |
| `/production/<id>/` | per Lot: issued, returned, consumed, scrapped and held on the line; outputs per Lot (net, reversed, Quality); history; shortfall reason |
| `/lots/<id>/genealogy/` | inputs of the Lot, and outputs made from it |

- **Read model:** `manufacturing/queries.py` with `order_materials`, `order_outputs` and
  `order_history`. `_order_holdings` and `_output_total` in `manufacturing/services.py` move into
  it, so there is one formula.
- **Navigation:** a "การผลิต" menu entry for every logged-in user.
- **No write buttons in PR 1.**

## PR 2 — record forms (next)

- Forms: create order, issue, return, consume, scrap, record output, reverse, close (with
  shortfall reason).
- Buttons are shown by role. A hidden request UUID makes a double submit post once.
- Cancel waits for [Issue #86](https://github.com/porntaned/ERP-for-Factory/issues/86).

## Out of scope

BOM approval screens, Quality release (M6), Deploy.
