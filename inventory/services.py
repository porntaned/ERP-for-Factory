"""Internal snapshot queries, not reservations or business posting authority."""

from decimal import Decimal

from django.db.models import Sum

from facilities.models import Warehouse

from .models import Lot, StockLedgerEntry


def get_stock_balance(*, lot: Lot, warehouse: Warehouse) -> Decimal:
    for value, model in ((lot, Lot), (warehouse, Warehouse)):
        if not isinstance(value, model) or value.pk is None or value._state.adding:
            raise ValueError("lot and warehouse must be saved records")
    lot_org = Lot.objects.filter(pk=lot.pk).values_list("item__organization_id", flat=True).first()
    warehouse_org = (
        Warehouse.objects.filter(pk=warehouse.pk)
        .values_list("plant__organization_id", flat=True)
        .first()
    )
    if lot_org is None or warehouse_org is None or lot_org != warehouse_org:
        raise ValueError("lot and warehouse must exist in the same organization")
    total = StockLedgerEntry.objects.filter(lot_id=lot.pk, warehouse_id=warehouse.pk).aggregate(
        total=Sum("quantity_delta")
    )["total"]
    return total if total is not None else Decimal("0")
