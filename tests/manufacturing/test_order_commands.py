"""M5.1 (Issue #69): create_production_order and cancel_production_order.

An order points at the ACTIVE version when created and keeps it after retirement; it names a
production line and an output warehouse in one plant; PRODUCTION at both is required. M5.1
orders are OPEN or CANCELLED and move no stock.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from access_control.models import WarehouseRoleAssignment
from inventory.models import RequestKey, StockLedgerEntry
from manufacturing.models import ProductionOrder
from manufacturing.services import (
    OrderAuthorizationError,
    OrderConflictError,
    OrderValidationError,
    approve_bom,
    cancel_production_order,
    create_bom_draft,
    create_production_order,
)
from tests.inventory.test_stock_receipt_concurrency import blocked_action


def active_bom(mf, item="lamp"):
    bom = create_bom_draft(
        item=mf.items[item],
        lines=[(mf.items["chip"], Decimal("4"))],
        actor=mf.users["production"],
        request_id=uuid4(),
    )
    return approve_bom(bom=bom, actor=mf.users["approver"], request_id=uuid4())


def order(
    mf, bom, *, quantity=Decimal("10"), line="LINE-1", output="FG", actor="production", key=None
):
    return create_production_order(
        bom=bom,
        quantity=quantity,
        line_warehouse=mf.wh[line],
        output_warehouse=mf.wh[output],
        actor=mf.users[actor],
        request_id=key or uuid4(),
    )


def cancel(mf, target, *, reason="Synthetic cancel", actor="production", key=None):
    return cancel_production_order(
        order=target, actor=mf.users[actor], reason=reason, request_id=key or uuid4()
    )


# ---------------------------------------------------------------- create


@pytest.mark.django_db
def test_order_created_open_on_active_bom(mf):
    bom = active_bom(mf)
    created = order(mf, bom)
    assert (created.status, created.bom, created.quantity) == ("OPEN", bom, Decimal("10"))
    assert (created.line_warehouse.code, created.output_warehouse.code) == ("LINE-1", "FG")
    assert created.created_by == mf.users["production"]
    assert not StockLedgerEntry.objects.exists()  # M5.1 moves no stock


@pytest.mark.django_db
def test_order_rejects_draft_bom(mf):
    bom = create_bom_draft(
        item=mf.items["lamp"],
        lines=[(mf.items["chip"], Decimal("4"))],
        actor=mf.users["production"],
        request_id=uuid4(),
    )
    with pytest.raises(OrderValidationError, match="ACTIVE"):
        order(mf, bom)


@pytest.mark.django_db
def test_order_rejects_retired_bom(mf):
    v1 = active_bom(mf)
    active_bom(mf)
    with pytest.raises(OrderValidationError, match="ACTIVE"):
        order(mf, v1)
    assert not ProductionOrder.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-1"), Decimal("1.0000001"), 10, 10.0])
def test_order_rejects_bad_quantity(mf, quantity):
    with pytest.raises(OrderValidationError):
        order(mf, active_bom(mf), quantity=quantity)
    assert (
        not ProductionOrder.objects.exists()
        and not RequestKey.objects.filter(command="ORDER_CREATE").exists()
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "line,output", [("LINE-1", "P2-FG"), ("X-LINE", "FG"), ("LINE-1", "LINE-1")]
)
def test_order_rejects_bad_warehouses(mf, line, output):
    with pytest.raises(OrderValidationError):
        order(mf, active_bom(mf), line=line, output=output)


@pytest.mark.django_db
def test_order_requires_both_warehouses(mf):
    bom = active_bom(mf)
    WarehouseRoleAssignment.objects.filter(
        user=mf.users["production"], warehouse=mf.wh["FG"]
    ).delete()
    with pytest.raises(OrderAuthorizationError):
        order(mf, bom)
    for actor in ("approver2", "outsider", "foreign"):
        with pytest.raises(OrderAuthorizationError):
            order(mf, bom, actor=actor)
    assert not ProductionOrder.objects.exists()


@pytest.mark.django_db
def test_inactive_actor_rejected(mf):
    bom = active_bom(mf)
    created = order(mf, bom)
    user = mf.users["production"]
    user.is_active = False
    user.save()
    with pytest.raises(OrderAuthorizationError):
        order(mf, bom)
    with pytest.raises(OrderAuthorizationError):
        cancel(mf, created)


@pytest.mark.django_db
def test_order_replay_and_conflict(mf):
    bom, key = active_bom(mf), uuid4()
    first = order(mf, bom, key=key)
    assert order(mf, bom, key=key) == first
    with pytest.raises(OrderConflictError):
        order(mf, bom, key=key, quantity=Decimal("11"))
    with pytest.raises(OrderConflictError):
        order(mf, bom, key=bom.request_id)  # key owned by BOM_DRAFT
    assert ProductionOrder.objects.count() == 1


@pytest.mark.django_db
def test_order_replay_after_bom_retirement(mf):
    v1, key = active_bom(mf), uuid4()
    first = order(mf, v1, key=key)
    active_bom(mf)
    assert order(mf, v1, key=key) == first


@pytest.mark.django_db
def test_order_keeps_version_after_retirement(mf):
    v1 = active_bom(mf)
    created = order(mf, v1)
    v2 = active_bom(mf)
    created.refresh_from_db()
    assert created.bom == v1 and created.bom.status == "RETIRED" and v2.status == "ACTIVE"


# ---------------------------------------------------------------- cancel


@pytest.mark.django_db
def test_cancel_open_order(mf):
    created = order(mf, active_bom(mf))
    cancelled = cancel(mf, created, reason="Customer changed plan")
    assert cancelled.status == "CANCELLED"
    assert (cancelled.cancelled_by, cancelled.cancel_reason) == (
        mf.users["production"],
        "Customer changed plan",
    )
    assert cancelled.cancelled_at is not None


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", "   ", None])
def test_cancel_rejects_blank_reason(mf, reason):
    created = order(mf, active_bom(mf))
    with pytest.raises(OrderValidationError):
        cancel(mf, created, reason=reason)
    created.refresh_from_db()
    assert created.status == "OPEN"


@pytest.mark.django_db
def test_cancel_rejects_cancelled(mf):
    created = order(mf, active_bom(mf))
    cancel(mf, created)
    with pytest.raises(OrderValidationError, match="OPEN"):
        cancel(mf, created)


@pytest.mark.django_db
def test_cancel_requires_both_warehouses(mf):
    created = order(mf, active_bom(mf))
    WarehouseRoleAssignment.objects.filter(
        user=mf.users["production"], warehouse=mf.wh["LINE-1"]
    ).delete()
    with pytest.raises(OrderAuthorizationError):
        cancel(mf, created)


@pytest.mark.django_db
def test_cancel_replay_and_conflict(mf):
    created, key = order(mf, active_bom(mf)), uuid4()
    first = cancel(mf, created, key=key)
    assert cancel(mf, created, key=key) == first
    with pytest.raises(OrderConflictError):
        cancel(mf, created, key=key, reason="Different reason")
    other = order(mf, created.bom)
    with pytest.raises(OrderConflictError):
        cancel(mf, other, key=key)
    other.refresh_from_db()
    assert other.status == "OPEN"


# ---------------------------------------------------------------- concurrency


@pytest.mark.django_db(transaction=True)
def test_order_and_approval_serialize(mf):
    v1 = active_bom(mf)
    v2 = create_bom_draft(
        item=mf.items["lamp"],
        lines=[(mf.items["driver"], Decimal("1"))],
        actor=mf.users["production"],
        request_id=uuid4(),
    )
    # The order holds v1; the approval of v2 must wait, then retire v1 after the order exists.
    created, outcome = blocked_action(
        lambda: order(mf, v1),
        lambda: approve_bom(bom=v2, actor=mf.users["approver"], request_id=uuid4()),
    )
    assert outcome[0] == "committed"
    created.refresh_from_db()
    assert created.bom.status == "RETIRED"

    # Reverse: the approval of v3 holds the rows; an order on v2 waits and then sees it retired.
    v3 = create_bom_draft(
        item=mf.items["lamp"],
        lines=[(mf.items["chip"], Decimal("3"))],
        actor=mf.users["production"],
        request_id=uuid4(),
    )
    _, outcome = blocked_action(
        lambda: approve_bom(bom=v3, actor=mf.users["approver"], request_id=uuid4()),
        lambda: order(mf, v2),
    )
    assert outcome[0] == "OrderValidationError"
    assert ProductionOrder.objects.count() == 1
