"""M6.2 (Issue #103): a REJECTED Lot may not be used at any warehouse of its organization.

Owner ruling (2026-11-06): while a Lot is REJECTED at ANY warehouse, Inventory refuses to move it,
issue it, consume it, receive more of it, put output into it, or reverse a transfer, CONSUME or
SCRAP of it. SCRAP and the reversal of a receipt or OUTPUT only take stock out and stay allowed.
Quality owns the reading (quality.services.get_rejected_warehouses); this module enforces it.

A command calls `require_lot_not_rejected` inside its transaction, AFTER it locked the Lot (the
Lot lock is what serializes it with Quality) and AFTER its exact-replay check (a replay returns
history), and BEFORE any write. PostgreSQL re-checks every ledger entry at commit.
"""

from quality.services import get_rejected_warehouses


class LotRejectedError(Exception):
    pass


def require_lot_not_rejected(lot) -> None:
    rejected = get_rejected_warehouses(lot=lot)
    if rejected:
        where = ", ".join(warehouse.code for warehouse in rejected)
        raise LotRejectedError(f"Lot {lot.code} is REJECTED at {where}")
