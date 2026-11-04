"""Inventory screens (M4.6). Every write goes through the Inventory commands, which enforce
authority, Quality and stock rules; these views only choose what to display and turn
command errors into messages. A hidden request UUID per form makes a double submit post once.
"""

from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from facilities.models import Warehouse
from inventory import reversals
from inventory.models import Lot, StockLedgerEntry, StockReceipt, StockReversal, StockTransfer
from inventory.services import (
    ReceiptAuthorizationError,
    ReceiptConflictError,
    ReceiptValidationError,
    receive_stock,
)
from inventory.transfer_policy import TransferQualityError, TransferQualityValidationError
from inventory.transfers import (
    InsufficientStockError,
    TransferAuthorizationError,
    TransferConflictError,
    TransferValidationError,
    transfer_stock,
)
from quality.services import get_lot_disposition

from .forms import ReceiptForm, ReversalForm, TransferForm
from .permissions import can_approve_all, movable_warehouses

MESSAGES = {
    InsufficientStockError: "ยอดคงเหลือไม่พอ",
    TransferQualityError: "คลังต้นทางต้องเป็น RELEASED ก่อนโอน",
    reversals.ReversalQualityError: "คลังที่ของจะออกต้องเป็น RELEASED ก่อนกลับรายการ",
    reversals.AlreadyReversedError: "รายการนี้ถูกกลับรายการไปแล้ว",
    ReceiptAuthorizationError: "ไม่มีสิทธิ์ WAREHOUSE ที่คลังนี้",
    TransferAuthorizationError: "ต้องมีสิทธิ์ WAREHOUSE ทั้งคลังต้นทางและปลายทาง",
    reversals.ReversalAuthorizationError: "ต้องมีสิทธิ์ APPROVER ทุกคลังที่เกี่ยวข้อง",
    ReceiptConflictError: "คำขอนี้ถูกใช้กับรายการอื่นแล้ว กรุณาเปิดฟอร์มใหม่",
    TransferConflictError: "คำขอนี้ถูกใช้กับรายการอื่นแล้ว กรุณาเปิดฟอร์มใหม่",
    reversals.ReversalConflictError: "คำขอนี้ถูกใช้กับรายการอื่นแล้ว กรุณาลองใหม่",
}
COMMAND_ERRORS = tuple(MESSAGES) + (
    ReceiptValidationError,
    TransferValidationError,
    TransferQualityValidationError,
    reversals.ReversalValidationError,
)


def _message(exc):
    for kind, text in MESSAGES.items():
        if isinstance(exc, kind):
            return text
    return f"ข้อมูลไม่ถูกต้อง: {exc}"


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


def _movement_view(request, form_class, template, post):
    warehouses = movable_warehouses(request.user)
    if not warehouses.exists():
        raise PermissionDenied("WAREHOUSE role required")
    form = form_class(request.POST or None, warehouses=warehouses)
    if request.method == "POST" and form.is_valid():
        try:
            success = post(form.cleaned_data)
        except COMMAND_ERRORS as exc:
            form.add_error(None, _message(exc))
        else:
            messages.success(request, success)
            return redirect("stock-overview")
    return render(request, template, {"form": form})


@login_required
def receipt_new(request):
    def post(data):
        receive_stock(
            lot=data["lot"],
            warehouse=data["warehouse"],
            actor=request.user,
            quantity=data["quantity"],
            reason=data["reason"],
            request_id=data["request_id"],
        )
        return f"รับเข้าสำเร็จ {data['quantity'].normalize()} ที่ {data['warehouse'].code}"

    return _movement_view(request, ReceiptForm, "demo/receipt_form.html", post)


@login_required
def transfer_new(request):
    def post(data):
        transfer_stock(
            lot=data["lot"],
            source_warehouse=data["source_warehouse"],
            destination_warehouse=data["destination_warehouse"],
            actor=request.user,
            quantity=data["quantity"],
            reason=data["reason"],
            request_id=data["request_id"],
        )
        return (
            f"โอนสำเร็จ {data['quantity'].normalize()} "
            f"{data['source_warehouse'].code} → {data['destination_warehouse'].code}"
        )

    return _movement_view(request, TransferForm, "demo/transfer_form.html", post)


@login_required
def history(request):
    receipts = StockReceipt.objects.select_related(
        "ledger_entry__lot", "ledger_entry__warehouse", "ledger_entry__actor", "reversal"
    ).order_by("-id")[:100]
    transfers = StockTransfer.objects.select_related(
        "source_entry__lot",
        "source_entry__warehouse",
        "source_entry__actor",
        "destination_entry__warehouse",
        "reversal",
    ).order_by("-id")[:100]
    receipt_rows = [
        {
            "obj": r,
            "entry": r.ledger_entry,
            "key": uuid4(),
            "reversed": hasattr(r, "reversal"),
            "can_reverse": not hasattr(r, "reversal")
            and can_approve_all(request.user, [r.ledger_entry.warehouse]),
        }
        for r in receipts
    ]
    transfer_rows = [
        {
            "obj": t,
            "key": uuid4(),
            "reversed": hasattr(t, "reversal"),
            "can_reverse": not hasattr(t, "reversal")
            and can_approve_all(
                request.user, [t.source_entry.warehouse, t.destination_entry.warehouse]
            ),
        }
        for t in transfers
    ]
    reversal_rows = StockReversal.objects.select_related(
        "debit_entry__actor", "debit_entry__warehouse"
    ).order_by("-id")[:100]
    return render(
        request,
        "demo/history.html",
        {
            "receipts": receipt_rows,
            "transfers": transfer_rows,
            "reversals": reversal_rows,
        },
    )


@login_required
@require_POST
def reverse(request, kind, pk):
    if kind == "receipt":
        original = get_object_or_404(
            StockReceipt.objects.select_related("ledger_entry__warehouse"), pk=pk
        )
        involved = [original.ledger_entry.warehouse]
    else:
        original = get_object_or_404(
            StockTransfer.objects.select_related(
                "source_entry__warehouse", "destination_entry__warehouse"
            ),
            pk=pk,
        )
        involved = [original.source_entry.warehouse, original.destination_entry.warehouse]
    if not can_approve_all(request.user, involved):
        raise PermissionDenied("APPROVER role required at every warehouse involved")
    form = ReversalForm(request.POST)
    if not form.is_valid():
        messages.error(request, "ต้องระบุเหตุผลในการกลับรายการ")
        return redirect("history")
    data = form.cleaned_data
    command = reversals.reverse_receipt if kind == "receipt" else reversals.reverse_transfer
    try:
        command(
            **{kind: original},
            actor=request.user,
            reason=data["reason"],
            request_id=data["request_id"],
        )
    except COMMAND_ERRORS as exc:
        messages.error(request, _message(exc))
    else:
        messages.success(request, "กลับรายการแล้ว")
    return redirect("history")
