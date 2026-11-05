"""M5.2b (Issue #75): consume, scrap, record output and close a production order.

Owner rules: an order closes only with nothing left on its line (return or scrap); scrap needs a
reason and an APPROVER; output enters FG as HOLD. Inventory posts every ledger entry.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRoleAssignment
from inventory.models import Lot, ProductionPosting, RequestKey, StockLedgerEntry
from manufacturing.models import OrderPosting
from manufacturing.services import (
    MaterialAuthorizationError,
    MaterialConflictError,
    MaterialLimitError,
    MaterialValidationError,
    OrderValidationError,
    cancel_production_order,
    close_production_order,
    consume_material,
    record_output,
    scrap_material,
)
from quality.services import get_lot_disposition
from tests.inventory.test_stock_receipt_concurrency import blocked_action

from .test_material_movements import balance, give_back, issue, order, plant, stock  # noqa: F401

D = Decimal


def consume(mf, quantity, *, lot=None, target=None, actor="production", key=None):
    return consume_material(
        order=target or mf.order,
        lot=lot or mf.lot,
        quantity=D(quantity),
        actor=mf.users[actor],
        reason="Synthetic consumption",
        request_id=key or uuid4(),
    )


def scrap(mf, quantity, *, actor="approver2", reason="Damaged on the line", key=None):
    return scrap_material(
        order=mf.order,
        lot=mf.lot,
        quantity=D(quantity),
        actor=mf.users[actor],
        reason=reason,
        request_id=key or uuid4(),
    )


def output(mf, quantity, *, code="LAMP-0001", target=None, actor="production", key=None):
    return record_output(
        order=target or mf.order,
        lot_code=code,
        quantity=D(quantity),
        actor=mf.users[actor],
        reason="Synthetic output",
        request_id=key or uuid4(),
    )


SHORT = "Synthetic run stopped short"  # M5.2c: closing with output below quantity needs one


def close(mf, *, target=None, key=None, shortfall_reason=None):
    return close_production_order(
        order=target or mf.order,
        actor=mf.users["production"],
        request_id=key or uuid4(),
        shortfall_reason=shortfall_reason,
    )


@pytest.fixture
def line(plant):  # noqa: F811 (fixture imported from test_material_movements)
    """40 chips issued to the order's line; approver2 may scrap there."""
    WarehouseRoleAssignment.objects.create(
        user=plant.users["approver2"], warehouse=plant.wh["LINE-1"], role="APPROVER"
    )
    issue(plant, "40")
    return plant


# ---------------------------------------------------------------- consume


@pytest.mark.django_db
def test_consume_posts_a_line_debit_through_inventory(line):
    link = consume(line, "30")
    assert balance(line, "LINE-1") == D("10")
    posting = link.posting
    assert (link.kind, posting.kind) == ("CONSUME", "CONSUME")
    entry = posting.ledger_entry
    assert (entry.warehouse.code, entry.quantity_delta, entry.actor) == (
        "LINE-1",
        D("-30"),
        line.users["production"],
    )


@pytest.mark.django_db
def test_consume_limited_to_what_the_order_holds(line):
    with pytest.raises(MaterialLimitError):
        consume(line, "40.000001")
    other_lot = stock(line, "L9", D("5"))
    with pytest.raises(MaterialLimitError):
        consume(line, "1", lot=other_lot)
    consume(line, "40")
    with pytest.raises(MaterialLimitError):
        give_back(line, "1")


@pytest.mark.django_db
def test_return_after_consumption_is_limited_to_the_rest(line):
    consume(line, "30")
    with pytest.raises(MaterialLimitError):
        give_back(line, "11")
    give_back(line, "10")


@pytest.mark.django_db
def test_consume_requires_production_at_the_line(line):
    with pytest.raises(MaterialAuthorizationError):
        consume(line, "1", actor="approver2")


@pytest.mark.django_db
def test_consume_replay_and_conflict(line):
    key = uuid4()
    first = consume(line, "5", key=key)
    assert consume(line, "5", key=key) == first
    with pytest.raises(MaterialConflictError):
        consume(line, "6", key=key)
    with pytest.raises(MaterialConflictError):
        consume(line, "5", key=line.order.request_id)  # ORDER_CREATE key
    assert balance(line, "LINE-1") == D("35")


# ---------------------------------------------------------------- scrap


@pytest.mark.django_db
def test_scrap_needs_an_approver_at_the_line_and_a_reason(line):
    with pytest.raises(MaterialAuthorizationError):
        scrap(line, "1", actor="production")
    with pytest.raises(MaterialValidationError):
        scrap(line, "1", reason="  ")
    link = scrap(line, "2")
    assert (link.kind, link.posting.ledger_entry.quantity_delta) == ("SCRAP", D("-2"))
    assert link.posting.ledger_entry.actor == line.users["approver2"]
    with pytest.raises(MaterialLimitError):
        scrap(line, "38.1")


# ---------------------------------------------------------------- output


@pytest.mark.django_db
def test_output_enters_fg_as_hold(line):
    link = output(line, "10")
    lot = link.posting.ledger_entry.lot
    assert (lot.item, lot.code) == (line.items["lamp"], "LAMP-0001")
    assert balance(line, "FG", lot=lot) == D("10")
    assert get_lot_disposition(lot=lot, warehouse=line.wh["FG"]) == "HOLD"


@pytest.mark.django_db
def test_output_cannot_exceed_order_quantity(line):
    output(line, "6")
    output(line, "4")  # same lot, same order: allowed
    with pytest.raises(MaterialLimitError):
        output(line, "0.000001")


@pytest.mark.django_db
def test_output_lot_belongs_to_one_order(line):
    output(line, "1")
    other = order(line)
    with pytest.raises(MaterialValidationError):
        output(line, "1", target=other)
    Lot.objects.create(item=line.items["lamp"], code="LAMP-OLD")
    with pytest.raises(MaterialValidationError):
        output(line, "1", code="LAMP-OLD")  # an existing Lot is never adopted


@pytest.mark.django_db
def test_output_requires_production_at_output_warehouse(line):
    WarehouseRoleAssignment.objects.filter(
        user=line.users["production"], warehouse=line.wh["FG"]
    ).delete()
    with pytest.raises(MaterialAuthorizationError):
        output(line, "1")
    assert not Lot.objects.filter(code="LAMP-0001").exists()


# ---------------------------------------------------------------- close


@pytest.mark.django_db
def test_close_requires_an_empty_line(line):
    with pytest.raises(OrderValidationError, match="line"):
        close(line)
    consume(line, "38")
    scrap(line, "2")
    output(line, "9")
    closed = close(line, shortfall_reason=SHORT)
    assert (closed.status, closed.closed_by) == ("CLOSED", line.users["production"])
    assert closed.closed_at is not None


@pytest.mark.django_db
def test_closed_order_accepts_nothing_more(line):
    give_back(line, "40")
    close(line, shortfall_reason=SHORT)
    for action in (lambda: issue(line, "1"), lambda: output(line, "1"), lambda: close(line)):
        with pytest.raises((MaterialValidationError, OrderValidationError)):
            action()
    with pytest.raises(OrderValidationError):
        cancel_production_order(
            order=line.order, actor=line.users["production"], reason="x", request_id=uuid4()
        )


@pytest.mark.django_db
def test_close_replay_and_conflict(line):
    give_back(line, "40")
    key = uuid4()
    first = close(line, key=key, shortfall_reason=SHORT)
    assert close(line, key=key, shortfall_reason=SHORT) == first
    with pytest.raises(OrderValidationError):
        close(line)  # a new key on a CLOSED order


@pytest.mark.django_db
def test_keys_registered_for_postings_and_close(line):
    consume(line, "30")
    scrap(line, "1")
    output(line, "1")
    give_back(line, "9")
    closed = close(line, shortfall_reason=SHORT)
    commands = set(RequestKey.objects.values_list("command", flat=True))
    assert {"CONSUME", "SCRAP", "OUTPUT", "ORDER_CLOSE"} <= commands
    assert RequestKey.objects.get(request_id=closed.close_request_id).command == "ORDER_CLOSE"


# ---------------------------------------------------------------- database rules


def rejected(action):
    with pytest.raises(IntegrityError), transaction.atomic():
        action()


@pytest.mark.django_db
def test_database_enforces_posting_sign_and_exclusivity(line):
    receipt_entry = StockLedgerEntry.objects.filter(
        quantity_delta__gt=0, warehouse=line.wh["RM-A"]
    ).first()
    rejected(
        lambda: ProductionPosting.objects.create(
            kind="OUTPUT", ledger_entry=receipt_entry, request_id=uuid4()
        )
    )
    link = consume(line, "1")
    rejected(lambda: ProductionPosting.objects.filter(pk=link.posting.pk).update(kind="SCRAP"))
    rejected(lambda: OrderPosting.objects.filter(pk=link.pk).update(kind="SCRAP"))


@pytest.mark.django_db
def test_database_enforces_holding_and_open_order(line):
    give_back(line, "40")
    close(line, shortfall_reason=SHORT)
    # A raw link to a CLOSED order is refused even with a valid Inventory posting.
    posting = ProductionPosting.objects.select_related("ledger_entry").first()
    assert posting is None
    rejected(lambda: line.order.__class__.objects.filter(pk=line.order.pk).update(status="OPEN"))


# ---------------------------------------------------------------- concurrency


@pytest.mark.django_db(transaction=True)
def test_concurrent_consumption_respects_holding(line):
    _, outcome = blocked_action(lambda: consume(line, "30"), lambda: consume(line, "30"))
    assert outcome[0] == "MaterialLimitError"
    assert balance(line, "LINE-1") == D("10")


@pytest.mark.django_db
def test_replay_with_another_lot_or_lot_code_conflicts(line):
    other_lot = stock(line, "L8", D("10"))
    key = uuid4()
    consume(line, "1", key=key)
    with pytest.raises(MaterialConflictError):
        consume(line, "1", key=key, lot=other_lot)
    out_key = uuid4()
    output(line, "1", key=out_key)
    with pytest.raises(MaterialConflictError):
        output(line, "1", key=out_key, code="LAMP-0002")
    assert not Lot.objects.filter(code="LAMP-0002").exists()
