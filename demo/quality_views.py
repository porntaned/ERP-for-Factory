"""M6.1 PR 2 (Issue #96): Quality screens.

The list shows HOLD and REJECTED Lot-Warehouses with stock at warehouses where the user holds
QUALITY or APPROVER. Forms call quality.services; the commands enforce authority, the HOLD-only
inspection rule, the sample limit and the not-the-inspector rule. A hidden request UUID makes a
double submit replay instead of recording twice.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Value
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from access_control.policies import has_warehouse_role, warehouses_for_user
from inventory.models import Lot, StockLedgerEntry
from quality import services as qs
from quality.models import LotDispositionEvent, LotInspection

from .quality_forms import AuditFilterForm, InspectionForm, ReturnToHoldForm
from .quantities import format_quantity

MESSAGES = (
    (qs.DispositionAuthorizationError, "ไม่มีสิทธิ์ทำรายการนี้", False),
    # Review m3: a stale page also raises Conflict/Validation; show the command's reason.
    (qs.DispositionConflictError, "ทำรายการไม่ได้ กรุณาเปิดหน้าใหม่", True),
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
                # Review m2: the command refuses the inspector who rejected the pair.
                "can_return": disposition == "REJECTED"
                and has_warehouse_role(user, warehouse, ["APPROVER"])
                and qs.rejecting_inspector_id(lot, warehouse) != user.pk,
            }
        )
    return sorted(rows, key=lambda r: (r["warehouse"].code, r["lot"].code))


def _page(request, errors=()):
    if not quality_warehouses(request.user).exists():
        raise PermissionDenied("QUALITY or APPROVER role required")
    rows = _pairs(request.user)
    for row in rows:
        initial = {"lot": row["lot"].pk, "warehouse": row["warehouse"].pk}
        # Review m6: auto_id=False so the repeated row forms carry no duplicate element ids.
        row["inspect_form"] = InspectionForm(initial=initial, auto_id=False)
        row["return_form"] = ReturnToHoldForm(initial=initial, auto_id=False)
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


# ---------------------------------------------------------------- M6.4 (Issue #113): QC history
# Owner ruling 1 (chat, 2026-11-11): every inspection and disposition change at the warehouses
# where the user holds QUALITY or APPROVER, newest first, in one table; read-only. A fixed page
# size with "older" paging keeps the query count independent of the history's length.

AUDIT_PAGE_SIZE = 50


def _audit_keys(warehouse_ids, start, end, page):
    """(created_at, id, kind) of one page of both kinds, newest first; one query."""

    def scoped(queryset, kind):
        queryset = queryset.filter(warehouse_id__in=warehouse_ids)
        if start:
            queryset = queryset.filter(created_at__date__gte=start)  # local dates (TIME_ZONE)
        if end:
            queryset = queryset.filter(created_at__date__lte=end)
        return queryset.annotate(row_kind=Value(kind)).values_list("created_at", "id", "row_kind")

    combined = scoped(LotInspection.objects.order_by(), "inspection").union(
        scoped(LotDispositionEvent.objects.order_by(), "event"), all=True
    )
    offset = (page - 1) * AUDIT_PAGE_SIZE
    return list(
        combined.order_by("-created_at", "row_kind", "-id")[offset : offset + AUDIT_PAGE_SIZE + 1]
    )


def _audit_rows(keys):
    ids = {"inspection": [], "event": []}
    for _, pk, kind in keys:
        ids[kind].append(pk)
    found = {
        "inspection": LotInspection.objects.select_related("lot", "warehouse", "inspector").in_bulk(
            ids["inspection"]
        ),
        "event": LotDispositionEvent.objects.select_related("lot", "warehouse", "actor").in_bulk(
            ids["event"]
        ),
    }
    return [{"kind": kind, "obj": found[kind][pk]} for _, pk, kind in keys]


@login_required
@require_GET
def quality_audit(request):
    allowed = quality_warehouses(request.user)
    warehouses = list(allowed.order_by("code", "pk"))
    if not warehouses:
        raise PermissionDenied("QUALITY or APPROVER role required")
    form = AuditFilterForm(request.GET or None, warehouses=allowed.order_by("code", "pk"))
    context = {"form": form, "rows": [], "errors": [], "older": None, "page": 1}
    if form.is_bound and not form.is_valid():
        context["errors"] = [f"ตัวกรองไม่ถูกต้อง: {form.errors.as_text()}"]
        return render(request, "demo/quality/audit.html", context)
    data = form.cleaned_data if form.is_bound else {}
    chosen = data.get("warehouse")
    page = data.get("page") or 1
    keys = _audit_keys(
        [chosen.pk] if chosen else [w.pk for w in warehouses],
        data.get("date_from"),
        data.get("date_to"),
        page,
    )
    if len(keys) > AUDIT_PAGE_SIZE:
        query = request.GET.copy()
        query["page"] = page + 1
        context["older"] = query.urlencode()
    context |= {"rows": _audit_rows(keys[:AUDIT_PAGE_SIZE]), "page": page}
    return render(request, "demo/quality/audit.html", context)
