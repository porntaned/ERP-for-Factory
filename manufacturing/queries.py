"""Read model for production orders: one place for the quantities the commands check and the
screens show (M5.5, Issue #89). Reads only; every write is in manufacturing.services.

A posting counts net of its reversal (M5.2c); a material movement is +issue / -return.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.db.models.functions import Coalesce

from inventory.models import Lot, ProductionPostingReversal
from quality.services import get_lot_disposition

from .models import MovementKind, OrderPosting, PostingKind, ProductionMaterialMovement

ZERO = Decimal("0")

# An issue adds to the order's holding, a return removes from it.
SIGNED_MOVEMENT = Case(
    When(kind=MovementKind.ISSUE, then=F("transfer__destination_entry__quantity_delta")),
    default=-F("transfer__destination_entry__quantity_delta"),
    output_field=DecimalField(),
)

# A posting's signed quantity net of its reversal (M5.2c): zero once reversed.
NET_POSTED = F("posting__ledger_entry__quantity_delta") + Coalesce(
    F("posting__reversal__ledger_entry__quantity_delta"), ZERO
)


def order_holdings(order) -> dict[int, Decimal]:
    """Net quantity per Lot id the order holds on its line: issued - returned - consumed - scrapped."""
    rows = (
        ProductionMaterialMovement.objects.filter(order=order)
        .values("transfer__destination_entry__lot_id")
        .annotate(net=Sum(SIGNED_MOVEMENT))
    )
    held = {row["transfer__destination_entry__lot_id"]: row["net"] for row in rows}
    used = (
        OrderPosting.objects.filter(order=order, kind__in=(PostingKind.CONSUME, PostingKind.SCRAP))
        .values("posting__ledger_entry__lot_id")
        .annotate(net=Sum(NET_POSTED))
    )
    for row in used:
        lot_id = row["posting__ledger_entry__lot_id"]
        held[lot_id] = held.get(lot_id, ZERO) + row["net"]
    return held


def output_total(order) -> Decimal:
    """Net output of the order: OUTPUT - reversed OUTPUT."""
    total = OrderPosting.objects.filter(order=order, kind=PostingKind.OUTPUT).aggregate(
        total=Sum(NET_POSTED)
    )["total"]
    return total or ZERO


@dataclass(frozen=True)
class MaterialRow:
    lot: Lot
    issued: Decimal
    returned: Decimal
    consumed: Decimal
    scrapped: Decimal

    @property
    def held(self) -> Decimal:
        return self.issued - self.returned - self.consumed - self.scrapped


def order_materials(order) -> list[MaterialRow]:
    """Each material Lot of the order with its issued, returned, consumed and scrapped totals."""
    lot_key = "transfer__destination_entry__lot_id"
    moved = (
        ProductionMaterialMovement.objects.filter(order=order)
        .values(lot_key)
        .annotate(
            issued=Sum(
                "transfer__destination_entry__quantity_delta", filter=Q(kind=MovementKind.ISSUE)
            ),
            returned=Sum(
                "transfer__destination_entry__quantity_delta", filter=Q(kind=MovementKind.RETURN)
            ),
        )
    )
    totals = {row[lot_key]: dict(issued=row["issued"], returned=row["returned"]) for row in moved}
    used = (
        OrderPosting.objects.filter(order=order, kind__in=(PostingKind.CONSUME, PostingKind.SCRAP))
        .values("posting__ledger_entry__lot_id", "kind")
        .annotate(net=Sum(NET_POSTED))
    )
    for row in used:
        name = "consumed" if row["kind"] == PostingKind.CONSUME else "scrapped"
        totals.setdefault(row["posting__ledger_entry__lot_id"], {})[name] = -row["net"]
    lots = Lot.objects.select_related("item").in_bulk(totals)
    rows = [
        MaterialRow(
            lot=lots[lot_id],
            **{k: values.get(k) or ZERO for k in ("issued", "returned", "consumed", "scrapped")},
        )
        for lot_id, values in totals.items()
    ]
    return sorted(rows, key=lambda row: row.lot.code)


@dataclass(frozen=True)
class OutputRow:
    lot: Lot
    net: Decimal
    reversed: bool
    disposition: str


def order_outputs(order) -> list[OutputRow]:
    """Each output Lot with its net quantity, whether any output was reversed, and its Quality."""
    rows = (
        OrderPosting.objects.filter(order=order, kind=PostingKind.OUTPUT)
        .values("posting__ledger_entry__lot_id")
        .annotate(
            net=Sum(NET_POSTED),
            reversals=Sum(Case(When(posting__reversal__isnull=False, then=1), default=0)),
        )
    )
    lots = Lot.objects.select_related("item").in_bulk(
        [row["posting__ledger_entry__lot_id"] for row in rows]
    )
    result = []
    for row in rows:
        lot = lots[row["posting__ledger_entry__lot_id"]]
        result.append(
            OutputRow(
                lot=lot,
                net=row["net"],
                reversed=row["reversals"] > 0,
                disposition=get_lot_disposition(lot=lot, warehouse=order.output_warehouse),
            )
        )
    return sorted(result, key=lambda row: row.lot.code)


@dataclass(frozen=True)
class HistoryRow:
    at: datetime
    kind: str  # ISSUE, RETURN, CONSUME, SCRAP, OUTPUT or REVERSAL
    lot: Lot
    quantity: Decimal
    actor: str
    reason: str


def order_history(order) -> list[HistoryRow]:
    """Every recorded step of the order, oldest first."""
    rows = []
    for movement in ProductionMaterialMovement.objects.filter(order=order).select_related(
        "transfer__destination_entry__lot", "transfer__destination_entry__actor"
    ):
        entry = movement.transfer.destination_entry
        rows.append(
            HistoryRow(
                movement.created_at,
                movement.kind,
                entry.lot,
                entry.quantity_delta,
                entry.actor.username,
                entry.reason,
            )
        )
    for link in OrderPosting.objects.filter(order=order).select_related(
        "posting__ledger_entry__lot", "posting__ledger_entry__actor"
    ):
        entry = link.posting.ledger_entry
        rows.append(
            HistoryRow(
                link.created_at,
                link.kind,
                entry.lot,
                abs(entry.quantity_delta),
                entry.actor.username,
                entry.reason,
            )
        )
    for reversal in ProductionPostingReversal.objects.filter(
        posting__order_link__order=order
    ).select_related("ledger_entry__lot", "ledger_entry__actor"):
        entry = reversal.ledger_entry
        rows.append(
            HistoryRow(
                reversal.created_at,
                "REVERSAL",
                entry.lot,
                abs(entry.quantity_delta),
                entry.actor.username,
                entry.reason,
            )
        )
    return sorted(rows, key=lambda row: row.at)
