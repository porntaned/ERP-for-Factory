"""Manufacturing screens (M5.5, Issue #89): read-only pages (PR 1) and record forms (PR 2).

Quantities come from manufacturing.queries and manufacturing.genealogy, the same read model the
commands use for their checks; these views only arrange them for display.
"""

from dataclasses import dataclass
from typing import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import Lot
from manufacturing import services as mf
from manufacturing.genealogy import inputs_of, lot_positions, outputs_of, trace
from manufacturing.models import OrderPosting, ProductionOrder
from manufacturing.queries import (
    order_history,
    order_holdings,
    order_materials,
    order_outputs,
    output_total,
)
from quality.models import LotDispositionEvent, LotInspection

from .permissions import order_actions, production_warehouses
from .production_forms import (
    CancelForm,
    CloseForm,
    HeldLotForm,
    IssueForm,
    LotSearchForm,
    OrderForm,
    OutputForm,
    ReturnForm,
    ReverseForm,
)
from .quantities import format_quantity

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
    can_create = production_warehouses(request.user).exists()
    return render(
        request, "demo/production/list.html", {"orders": orders, "can_create": can_create}
    )


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
        "actions": order_actions(request.user, order),
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
        # M6.1 PR 2: who inspected this Lot, with what result, and every disposition change.
        "inspections": LotInspection.objects.filter(lot=lot)
        .select_related("warehouse", "inspector")
        .order_by("id"),
        "dispositions": LotDispositionEvent.objects.filter(lot=lot)
        .select_related("warehouse", "actor")
        .order_by("id"),
    }
    return render(request, "demo/production/genealogy.html", context)


# ---------------------------------------------------------------- M6.3: Lot search and trace
# Login only, as the genealogy page (owner ruling 2). Read-only: no HOLD or recall action here.


@login_required
def lot_search(request):
    form = LotSearchForm(request.GET or None)
    context = {"form": form, "searched": False, "lots": [], "invalid": False}
    if form.is_bound and not form.is_valid():
        context["invalid"] = True
    elif form.is_bound and form.cleaned_data["code"]:
        code = form.cleaned_data["code"]
        lots = list(
            Lot.objects.filter(code=code).select_related("item").order_by("item__code", "pk")
        )
        if len(lots) == 1:
            return redirect("lot-trace", pk=lots[0].pk)
        context |= {"searched": True, "code": code, "lots": lots}
    return render(request, "demo/production/lot_search.html", context)


@login_required
def lot_trace(request, pk):
    lot = get_object_or_404(Lot.objects.select_related("item"), pk=pk)
    backward, forward = trace(lot, "backward"), trace(lot, "forward")
    lots = list({each.pk: each for each in backward.lots + forward.lots[1:]}.values())
    positions = lot_positions(lots)
    context = {
        "lot": lot,
        "backward": backward.edges,
        "forward": forward.edges,
        "positions": [(each, positions[each.pk]) for each in lots],
    }
    return render(request, "demo/production/trace.html", context)


# ---------------------------------------------------------------- PR 2: record forms
# Each form calls one manufacturing.services command; the command enforces authority, limits,
# Quality and order state. A hidden request UUID makes a double submit replay, not post twice.

MESSAGES = (
    ((mf.MaterialAuthorizationError, mf.OrderAuthorizationError), "ไม่มีสิทธิ์ทำรายการนี้", False),
    (
        (mf.MaterialLotRejectedError,),
        "Lot นี้ถูก REJECTED ที่คลังใดคลังหนึ่ง จึงใช้งานไม่ได้ (scrap ได้เท่านั้น)",
        True,
    ),
    ((mf.MaterialQualityError,), "Lot ต้องเป็น RELEASED ที่คลังต้นทาง", False),
    ((mf.MaterialConflictError, mf.OrderConflictError), "คำขอนี้ถูกใช้แล้ว กรุณาเปิดฟอร์มใหม่", False),
    ((mf.AlreadyReversedError,), "รายการนี้ถูกกลับรายการไปแล้ว", False),
    ((mf.MaterialLimitError,), "เกินจำนวนที่อนุญาต", True),
    ((mf.MaterialValidationError, mf.OrderValidationError), "ข้อมูลไม่ถูกต้อง", True),
)
COMMAND_ERRORS = tuple(kind for kinds, _, _ in MESSAGES for kind in kinds)


def _message(exc):
    for kinds, text, detail in MESSAGES:
        if isinstance(exc, kinds):
            return f"{text}: {exc}" if detail else text
    return str(exc)


def _held(order):
    return [lot_id for lot_id, quantity in order_holdings(order).items() if quantity > 0]


def _run_form(request, *, form, template, context, post, success, done):
    if request.method == "POST" and form.is_valid():
        try:
            post(form.cleaned_data)
        except COMMAND_ERRORS as exc:
            form.add_error(None, _message(exc))
        else:
            messages.success(request, success(form.cleaned_data))
            return redirect(done)
    return render(request, template, context | {"form": form})


@login_required
def production_new(request):
    warehouses = production_warehouses(request.user)
    if not warehouses.exists():
        raise PermissionDenied("PRODUCTION role required")
    form = OrderForm(request.POST or None, warehouses=warehouses)
    created = {}

    def post(data):
        created["order"] = mf.create_production_order(
            bom=data["bom"],
            quantity=data["quantity"],
            line_warehouse=data["line_warehouse"],
            output_warehouse=data["output_warehouse"],
            actor=request.user,
            request_id=data["request_id"],
        )

    if request.method == "POST" and form.is_valid():
        try:
            post(form.cleaned_data)
        except COMMAND_ERRORS as exc:
            form.add_error(None, _message(exc))
        else:
            order = created["order"]
            messages.success(request, f"สร้าง order #{order.pk} แล้ว")
            return redirect(f"/production/{order.pk}/")
    return render(
        request,
        "demo/production/form.html",
        {"form": form, "title": "สร้าง production order", "submit": "สร้าง order"},
    )


@dataclass(frozen=True)
class Action:
    title: str
    permission: str
    form: Callable
    run: Callable
    success: str


def _issue_form(request, order, data):
    return IssueForm(data, order=order, warehouses=production_warehouses(request.user))


def _return_form(request, order, data):
    return ReturnForm(
        data, order=order, held=_held(order), warehouses=production_warehouses(request.user)
    )


def _held_form(request, order, data):
    return HeldLotForm(data, held=_held(order))


def _quantity(data):
    return format_quantity(data["quantity"])


ACTIONS = {
    "issue": Action(
        "เบิกวัตถุดิบเข้า line",
        "record",
        _issue_form,
        lambda request, order, d: mf.issue_material(
            order=order,
            lot=d["lot"],
            source_warehouse=d["source_warehouse"],
            quantity=d["quantity"],
            actor=request.user,
            reason=d["reason"],
            request_id=d["request_id"],
        ),
        "เบิก {lot} {quantity} แล้ว",
    ),
    "return": Action(
        "คืนวัตถุดิบจาก line",
        "record",
        _return_form,
        lambda request, order, d: mf.return_material(
            order=order,
            lot=d["lot"],
            destination_warehouse=d["destination_warehouse"],
            quantity=d["quantity"],
            actor=request.user,
            reason=d["reason"],
            request_id=d["request_id"],
        ),
        "คืน {lot} {quantity} แล้ว",
    ),
    "consume": Action(
        "ใช้วัตถุดิบ",
        "record",
        _held_form,
        lambda request, order, d: mf.consume_material(
            order=order,
            lot=d["lot"],
            quantity=d["quantity"],
            actor=request.user,
            reason=d["reason"],
            request_id=d["request_id"],
        ),
        "ใช้ {lot} {quantity} แล้ว",
    ),
    "scrap": Action(
        "Scrap วัตถุดิบ (APPROVER)",
        "scrap",
        _held_form,
        lambda request, order, d: mf.scrap_material(
            order=order,
            lot=d["lot"],
            quantity=d["quantity"],
            actor=request.user,
            reason=d["reason"],
            request_id=d["request_id"],
        ),
        "scrap {lot} {quantity} แล้ว",
    ),
    "output": Action(
        "บันทึกผลผลิต",
        "record",
        lambda request, order, data: OutputForm(data),
        lambda request, order, d: mf.record_output(
            order=order,
            lot_code=d["lot_code"],
            quantity=d["quantity"],
            actor=request.user,
            reason=d["reason"],
            request_id=d["request_id"],
        ),
        "บันทึกผลผลิต {lot_code} {quantity} แล้ว",
    ),
    "close": Action(
        "ปิด order",
        "record",
        lambda request, order, data: CloseForm(data),
        lambda request, order, d: mf.close_production_order(
            order=order,
            actor=request.user,
            request_id=d["request_id"],
            shortfall_reason=d["shortfall_reason"].strip() or None,
        ),
        "ปิด order แล้ว",
    ),
    "cancel": Action(
        "ยกเลิก order",
        "cancel",
        lambda request, order, data: CancelForm(data),
        lambda request, order, d: mf.cancel_production_order(
            order=order, actor=request.user, reason=d["reason"], request_id=d["request_id"]
        ),
        "ยกเลิก order แล้ว",
    ),
}


@login_required
def order_action(request, pk, action):
    order = get_object_or_404(_orders().select_related("bom"), pk=pk)
    spec = ACTIONS.get(action)
    if spec is None:
        raise Http404("unknown action")
    if not order_actions(request.user, order)[spec.permission]:
        raise PermissionDenied(f"cannot {action} on this order")
    form = spec.form(request, order, request.POST or None)

    def success(data):
        values = {k: v for k, v in data.items() if isinstance(v, str)}
        lot = data.get("lot")
        return spec.success.format(
            lot=lot.code if lot else "",
            quantity=_quantity(data) if "quantity" in data else "",
            **values,
        )

    context = {
        "order": order,
        "title": spec.title,
        "submit": spec.title,
        "net_output": output_total(order),
    }
    return _run_form(
        request,
        form=form,
        template="demo/production/form.html",
        context=context,
        post=lambda data: spec.run(request, order, data),
        success=success,
        done=f"/production/{order.pk}/",
    )


@login_required
def reverse_posting(request, pk, link_pk):
    order = get_object_or_404(_orders(), pk=pk)
    link = get_object_or_404(
        OrderPosting.objects.select_related("posting__ledger_entry__lot"), pk=link_pk, order=order
    )
    needed = "reverse_output" if link.kind == "OUTPUT" else "reverse_line"
    if not order_actions(request.user, order)[needed]:
        raise PermissionDenied("APPROVER at the posting warehouse is required")
    entry = link.posting.ledger_entry
    form = ReverseForm(request.POST or None)
    label = (
        f"{KIND_LABELS[link.kind]} {entry.lot.code} {format_quantity(abs(entry.quantity_delta))}"
    )
    return _run_form(
        request,
        form=form,
        template="demo/production/form.html",
        context={"order": order, "title": f"กลับรายการ: {label}", "submit": "กลับรายการ"},
        post=lambda d: mf.reverse_order_posting(
            order_posting=link, actor=request.user, reason=d["reason"], request_id=d["request_id"]
        ),
        success=lambda d: f"กลับรายการ {label} แล้ว",
        done=f"/production/{order.pk}/",
    )
