"""M5.3 (Issue #78): Lot genealogy read from immutable production records.

An output Lot belongs to one order (M5.2b). Its inputs are the Lots that order consumed;
returned and scrapped material is not part of the output. Reversed postings (M5.2c) net out;
a Lot whose postings net to zero is not listed. Genealogy is at order granularity:
when one order outputs several Lots, each of them lists all of the order's consumed Lots.

M6.3 (Issue #108): `trace` follows these links through every level, and `lot_positions` shows
where each traced Lot is now. Both only read.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from inventory.models import Lot

from .models import OrderPosting, PostingKind, ProductionOrder
from .queries import NET_POSTED


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
    # M5.4: only orders where `lot` still has output; a fully reversed output came from nothing.
    order_ids = [
        o for o, _, _ in _per_order_lot(PostingKind.OUTPUT, posting__ledger_entry__lot=lot)
    ]
    return _links(_per_order_lot(PostingKind.CONSUME, order_id__in=order_ids))


def outputs_of(lot: Lot) -> list[Link]:
    """Output Lots of every order that consumed `lot`, with output and consumed quantities."""
    lot = _require_saved(lot)
    consumed = {
        o: q for o, _, q in _per_order_lot(PostingKind.CONSUME, posting__ledger_entry__lot=lot)
    }
    return _links(_per_order_lot(PostingKind.OUTPUT, order_id__in=list(consumed)), consumed)


# ---------------------------------------------------------------- M6.3 (Issue #108): every level


@dataclass(frozen=True)
class Edge:
    level: int  # 1 = a direct link of the start Lot
    from_lot: Lot  # the Lot being expanded
    order: ProductionOrder
    to_lot: Lot  # backward: a Lot the order consumed; forward: a Lot the order output
    quantity: Decimal  # backward: consumed; forward: output (as inputs_of / outputs_of)
    consumed: Decimal | None = None  # forward only: how much of `from_lot` the order consumed
    repeat: bool = False  # `to_lot` was reached before: listed, not expanded again


@dataclass(frozen=True)
class Trace:
    lot: Lot
    direction: str
    edges: list[Edge]

    @property
    def lots(self) -> list[Lot]:
        """The start Lot, then every Lot the trace reached, in the order first reached."""
        return [self.lot] + [edge.to_lot for edge in self.edges if not edge.repeat]


DIRECTIONS = ("backward", "forward")


def _level(
    direction: str, frontier: list[int]
) -> list[tuple[int, int, int, Decimal, Decimal | None]]:
    """One level as (from Lot id, order id, to Lot id, quantity, consumed) rows: two queries."""
    if direction == "backward":
        # As inputs_of: only orders where the Lot still has output; then what they consumed.
        made = _per_order_lot(PostingKind.OUTPUT, posting__ledger_entry__lot_id__in=frontier)
        by_order: dict[int, list[int]] = {}
        for order_id, lot_id, _ in made:
            by_order.setdefault(order_id, []).append(lot_id)
        if not by_order:
            return []
        used = _per_order_lot(PostingKind.CONSUME, order_id__in=list(by_order))
        return [(f, o, t, q, None) for o, t, q in used for f in by_order[o]]
    # As outputs_of: the orders that consumed the Lot (and how much), then what they output.
    used = _per_order_lot(PostingKind.CONSUME, posting__ledger_entry__lot_id__in=frontier)
    by_order = {}
    for order_id, lot_id, quantity in used:
        by_order.setdefault(order_id, []).append((lot_id, quantity))
    if not by_order:
        return []
    made = _per_order_lot(PostingKind.OUTPUT, order_id__in=list(by_order))
    return [(f, o, t, q, c) for o, t, q in made for f, c in by_order[o]]


def trace(lot: Lot, direction: str) -> Trace:
    """Every level of `lot`'s genealogy, breadth-first.

    backward: the Lots consumed to make `lot`, down to Lots no order produced. forward: the Lots
    made from `lot`, up to Lots no order consumed. The links and their netting are M5.3's. A Lot
    is expanded once: a Lot reached again (a diamond or a cycle) is listed with `repeat` set and
    the walk stops there. One batch of queries per level; edges are ordered by level, order id,
    then Lot code.
    """
    lot = _require_saved(lot)
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    lots = Lot.objects.select_related("item").in_bulk([lot.pk])
    if lot.pk not in lots:
        raise ValueError("lot must be a saved Lot")
    start = lots[lot.pk]
    seen, frontier, edges, level = {start.pk}, [start.pk], [], 0
    while frontier:
        level += 1
        rows = _level(direction, frontier)
        if not rows:
            break
        orders = ProductionOrder.objects.in_bulk({o for _, o, _, _, _ in rows})
        lots |= Lot.objects.select_related("item").in_bulk(
            {t for _, _, t, _, _ in rows} - lots.keys()
        )
        rows.sort(key=lambda r: (r[1], lots[r[2]].code, r[2], lots[r[0]].code, r[0]))
        frontier = []
        for from_id, order_id, to_id, quantity, consumed in rows:
            repeat = to_id in seen
            if not repeat:
                seen.add(to_id)
                frontier.append(to_id)
            edges.append(
                Edge(
                    level, lots[from_id], orders[order_id], lots[to_id], quantity, consumed, repeat
                )
            )
    return Trace(start, direction, edges)
