"""M6.1 PR 2 (Issue #96): Quality screens.

The list shows HOLD and REJECTED Lot-Warehouses with stock at warehouses where the user holds
QUALITY or APPROVER. Forms call quality.services; the commands enforce authority, the HOLD-only
inspection rule, the sample limit and the not-the-inspector rule. A hidden request UUID makes a
double submit replay instead of recording twice.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from access_control.policies import has_warehouse_role, warehouses_for_user
from inventory.models import Lot, StockLedgerEntry
from quality import services as qs

from .quality_forms import InspectionForm, ReturnToHoldForm
from .quantities import format_quantity

MESSAGES = (
    (qs.DispositionAuthorizationError, "ไม่มีสิทธิ์ทำรายการนี้", False),
    (qs.DispositionConflictError, "คำขอนี้ถูกใช้แล้ว กรุณาเปิดหน้าใหม่", False),
    (qs.DispositionValidationError, "ข้อมูลไม่ถูกต้อง", True),
)
COMMAND_ERRORS = tuple(kind for kind, _, _ in MESSAGES)


def _message(exc):
    for kind, text, detail in MESSAGES:
        if isinstance(exc, kind):
            return f"{text}: {exc}" if detail else text
    return str(exc)


def quality_warehouses(user):
    return warehouses_for_user(user, ["QUALITY", "APPROVER"])


def _pairs(user):
    warehouses = {w.pk: w for w in quality_warehouses(user)}
    totals = (
        StockLedgerEntry.objects.filter(warehouse_id__in=warehouses)
        .values("lot_id", "warehouse_id")
        .annotate(balance=Sum("quantity_delta"))
        .filter(balance__gt=0)
    )
    lots = Lot.objects.select_related("item").in_bulk({row["lot_id"] for row in totals})
    rows = []
    for row in totals:
        lot, warehouse = lots[row["lot_id"]], warehouses[row["warehouse_id"]]
        disposition = qs.get_lot_disposition(lot=lot, warehouse=warehouse)
        if disposition == "RELEASED":
            continue
        rows.append(
            {
                "lot": lot,
                "warehouse": warehouse,
                "balance": format_quantity(row["balance"]),
                "disposition": disposition,
                "can_inspect": disposition == "HOLD"
                and has_warehouse_role(user, warehouse, ["QUALITY"]),
                "can_return": disposition == "REJECTED"
                and has_warehouse_role(user, warehouse, ["APPROVER"]),
            }
        )
    return sorted(rows, key=lambda r: (r["warehouse"].code, r["lot"].code))


def _page(request, errors=()):
    if not quality_warehouses(request.user).exists():
        raise PermissionDenied("QUALITY or APPROVER role required")
    rows = _pairs(request.user)
    for row in rows:
        initial = {"lot": row["lot"].pk, "warehouse": row["warehouse"].pk}
        row["inspect_form"] = InspectionForm(initial=initial | {"sample_quantity": "1"})
        row["return_form"] = ReturnToHoldForm(initial=initial)
    return render(request, "demo/quality/list.html", {"rows": rows, "errors": errors})


@login_required
def quality_list(request):
    return _page(request)


def _run(request, form, post, success):
    if not form.is_valid():
        return _page(request, errors=[f"ข้อมูลไม่ถูกต้อง: {form.errors.as_text()}"])
    try:
        post(form.cleaned_data)
    except COMMAND_ERRORS as exc:
        return _page(request, errors=[_message(exc)])
    messages.success(request, success(form.cleaned_data))
    return redirect("quality-list")


@login_required
@require_POST
def inspect(request):
    def post(data):
        qs.record_inspection(
            lot=data["lot"],
            warehouse=data["warehouse"],
            result=data["result"],
            sample_quantity=data["sample_quantity"],
            note=data["note"],
            actor=request.user,
            request_id=data["request_id"],
        )

    return _run(
        request,
        InspectionForm(request.POST),
        post,
        lambda d: f"บันทึกผลตรวจ {d['result']} ของ {d['lot'].code} ที่ {d['warehouse'].code}",
    )


@login_required
@require_POST
def return_to_hold(request):
    def post(data):
        qs.return_rejected_to_hold(
            lot=data["lot"],
            warehouse=data["warehouse"],
            actor=request.user,
            reason=data["reason"],
            request_id=data["request_id"],
        )

    return _run(
        request,
        ReturnToHoldForm(request.POST),
        post,
        lambda d: f"ส่ง {d['lot'].code} ที่ {d['warehouse'].code} กลับเป็น HOLD",
    )
