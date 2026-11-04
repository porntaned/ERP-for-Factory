"""Read-only stock overview for synthetic demo data. Writes go through commands only."""

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from facilities.models import Warehouse
from inventory.models import Lot, StockLedgerEntry
from quality.services import get_lot_disposition


@login_required
def stock_overview(request):
    totals = (
        StockLedgerEntry.objects.values("lot_id", "warehouse_id")
        .annotate(balance=Sum("quantity_delta"))
        .order_by("lot_id", "warehouse_id")
    )
    lots = Lot.objects.select_related("item").in_bulk({row["lot_id"] for row in totals})
    warehouses = Warehouse.objects.select_related("plant").in_bulk(
        {row["warehouse_id"] for row in totals}
    )
    rows = []
    for row in totals:
        lot, warehouse = lots[row["lot_id"]], warehouses[row["warehouse_id"]]
        rows.append(
            {
                "item": lot.item.code,
                "lot": lot.code,
                "warehouse": warehouse.code,
                "balance": row["balance"].normalize(),
                "disposition": get_lot_disposition(lot=lot, warehouse=warehouse),
            }
        )
    return render(request, "demo/stock_overview.html", {"rows": rows})
