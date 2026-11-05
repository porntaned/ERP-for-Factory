"""M5.3 (Issue #78): Lot genealogy read from immutable production records.

An output Lot belongs to one order (M5.2b). Its inputs are the Lots that order consumed;
returned and scrapped material is not part of the output. Reversed postings (M5.2c) net out;
a Lot whose postings net to zero is not listed. Genealogy is at order granularity:
when one order outputs several Lots, each of them lists all of the order's consumed Lots.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from inventory.models import Lot

from .models import OrderPosting, PostingKind, ProductionOrder
from .services import NET_POSTED


@dataclass(frozen=True)
class Link:
    order: ProductionOrder
    lot: Lot
    quantity: Decimal  # consumed (inputs_of) or output (outputs_of) of `lot` on `order`
    consumed: Decimal | None = (
        None  # outputs_of only: how much of the queried Lot the order consumed
    )


def _require_saved(lot: object) -> Lot:
    if not isinstance(lot, Lot) or lot.pk is None or lot._state.adding:
        raise ValueError("lot must be a saved Lot")
    return lot


def _per_order_lot(kind: str, **filters) -> list[tuple[int, int, Decimal]]:
    rows = (
        OrderPosting.objects.filter(kind=kind, **filters)
        .values("order_id", "posting__ledger_entry__lot_id")
        .annotate(total=Sum(NET_POSTED))
        .exclude(total=0)
        .order_by("order_id", "posting__ledger_entry__lot_id")
    )
    return [(r["order_id"], r["posting__ledger_entry__lot_id"], abs(r["total"])) for r in rows]


def _links(rows, consumed=None) -> list[Link]:
    orders = ProductionOrder.objects.in_bulk({o for o, _, _ in rows})
    lots = Lot.objects.in_bulk({lot for _, lot, _ in rows})
    return [
        Link(orders[o], lots[lot], quantity, None if consumed is None else consumed[o])
        for o, lot, quantity in rows
    ]


def inputs_of(lot: Lot) -> list[Link]:
    """Lots consumed by the order that produced `lot`, with the quantity consumed."""
    lot = _require_saved(lot)
    order_ids = OrderPosting.objects.filter(
        kind=PostingKind.OUTPUT, posting__ledger_entry__lot=lot
    ).values("order_id")
    return _links(_per_order_lot(PostingKind.CONSUME, order_id__in=order_ids))


def outputs_of(lot: Lot) -> list[Link]:
    """Output Lots of every order that consumed `lot`, with output and consumed quantities."""
    lot = _require_saved(lot)
    consumed = {
        o: q for o, _, q in _per_order_lot(PostingKind.CONSUME, posting__ledger_entry__lot=lot)
    }
    return _links(_per_order_lot(PostingKind.OUTPUT, order_id__in=list(consumed)), consumed)
