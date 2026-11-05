"""Manufacturing screens (M5.5, Issue #89). PR 1: read-only pages over the production records.

Quantities come from manufacturing.queries and manufacturing.genealogy, the same read model the
commands use for their checks; these views only arrange them for display.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from inventory.models import Lot
from manufacturing.genealogy import inputs_of, outputs_of
from manufacturing.models import ProductionOrder
from manufacturing.queries import order_history, order_materials, order_outputs, output_total

KIND_LABELS = {
    "ISSUE": "เบิก",
    "RETURN": "คืน",
    "CONSUME": "ใช้",
    "SCRAP": "scrap",
    "OUTPUT": "ผลผลิต",
    "REVERSAL": "กลับรายการ",
}


def _orders():
    return ProductionOrder.objects.select_related("bom__item", "line_warehouse", "output_warehouse")


@login_required
def production_list(request):
    orders = [(order, output_total(order)) for order in _orders().order_by("-id")]
    return render(request, "demo/production/list.html", {"orders": orders})


@login_required
def production_detail(request, pk):
    order = get_object_or_404(_orders(), pk=pk)
    history = [(row, KIND_LABELS[row.kind]) for row in order_history(order)]
    context = {
        "order": order,
        "net_output": output_total(order),
        "materials": order_materials(order),
        "outputs": order_outputs(order),
        "history": history,
    }
    return render(request, "demo/production/detail.html", context)


@login_required
def lot_genealogy(request, pk):
    lot = get_object_or_404(Lot.objects.select_related("item"), pk=pk)
    by_lot = lambda link: (link.order.pk, link.lot.code)  # noqa: E731
    context = {
        "lot": lot,
        "inputs": sorted(inputs_of(lot), key=by_lot),
        "outputs": sorted(outputs_of(lot), key=by_lot),
    }
    return render(request, "demo/production/genealogy.html", context)
