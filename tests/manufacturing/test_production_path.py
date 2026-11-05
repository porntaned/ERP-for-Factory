"""M5.4 (Issue #85): one LAMP-A19 order end to end through the real commands, as demo data.

seed_production_demo runs seed_demo, then issues, consumes (one mistake reversed), scraps,
outputs two Lots (a third reversed), returns the rest and closes the order short with a reason.
A rerun replays every command and posts nothing new.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from access_control.models import WarehouseRoleAssignment
from facilities.models import Warehouse
from inventory.models import (
    Lot,
    ProductionPosting,
    ProductionPostingReversal,
    StockLedgerEntry,
)
from inventory.services import get_stock_balance
from manufacturing.genealogy import inputs_of, outputs_of
from manufacturing.models import OrderPosting, ProductionOrder
from manufacturing.services import (
    MaterialValidationError,
    issue_material,
    record_output,
    reverse_order_posting,
)
from quality.services import get_lot_disposition

D = Decimal


def counts():
    return [
        m.objects.count()
        for m in (StockLedgerEntry, ProductionPosting, ProductionPostingReversal, ProductionOrder)
    ]


def stock_table():
    """{(lot, warehouse): (balance, disposition)} for every pair with ledger history."""
    pairs = StockLedgerEntry.objects.values_list("lot", "warehouse").distinct()
    table = {}
    for lot_id, warehouse_id in pairs:
        entry = StockLedgerEntry.objects.filter(lot_id=lot_id, warehouse_id=warehouse_id).first()
        lot, warehouse = entry.lot, entry.warehouse
        table[(lot.code, warehouse.code)] = (
            get_stock_balance(lot=lot, warehouse=warehouse),
            get_lot_disposition(lot=lot, warehouse=warehouse),
        )
    return table


def links(result):
    return {link.lot.code: link.quantity for link in result}


@pytest.fixture
def seeded(db):
    call_command("seed_production_demo", verbosity=0)
    return ProductionOrder.objects.get()


@pytest.mark.django_db
def test_rerun_replays_and_posts_nothing_new(seeded):
    before = counts()
    call_command("seed_production_demo", verbosity=0)
    assert counts() == before
    assert before[2] == 2  # one consumption and one output reversed


@pytest.mark.django_db
def test_order_closes_short_with_its_reason(seeded):
    assert (seeded.bom.item.code, seeded.quantity, seeded.status) == ("LAMP-A19", D("10"), "CLOSED")
    assert seeded.shortfall_reason == "One lamp failed end-of-line test"
    assert seeded.closed_by.username == "demo-production"
    kinds = sorted(OrderPosting.objects.filter(order=seeded).values_list("kind", flat=True))
    assert kinds == ["CONSUME"] * 4 + ["OUTPUT"] * 3 + ["SCRAP"]


@pytest.mark.django_db
def test_every_lot_reconciles_by_warehouse(seeded):
    released, hold = "RELEASED", "HOLD"
    assert stock_table() == {
        ("L-0001", "RM-A"): (D("100"), released),  # M4.7 demo Lot, untouched
        ("L-0002", "RM-A"): (D("0"), released),  # 30 issued: 28 consumed, 2 scrapped
        ("L-0002", "LINE-1"): (D("0"), hold),
        ("L-0003", "RM-A"): (D("12"), released),  # 20 - 10 issued + 2 returned
        ("L-0003", "LINE-1"): (D("0"), hold),  # 8 consumed (+2 mistaken, reversed)
        ("D-0001", "RM-A"): (D("11"), released),  # 20 - 10 issued + 1 returned
        ("D-0001", "LINE-1"): (D("0"), hold),  # 9 consumed
        ("LAMP-0001", "FG"): (D("5"), hold),
        ("LAMP-0002", "FG"): (D("4"), hold),
        ("LAMP-0003", "FG"): (D("0"), hold),  # output reversed
    }


@pytest.mark.django_db
def test_genealogy_in_both_directions(seeded):
    lot = {code: Lot.objects.get(code=code) for code in ("LAMP-0001", "LAMP-0003", "L-0003")}
    inputs = {"L-0002": D("28"), "L-0003": D("8"), "D-0001": D("9")}
    assert links(inputs_of(lot["LAMP-0001"])) == inputs
    assert inputs_of(lot["LAMP-0003"]) == []
    result = outputs_of(lot["L-0003"])
    assert links(result) == {"LAMP-0001": D("5"), "LAMP-0002": D("4")}
    assert {link.consumed for link in result} == {D("8")}


@pytest.mark.django_db
def test_demo_approver_can_scrap_and_reverse_on_the_line(seeded):
    approver = get_user_model().objects.get(username="demo-approver")
    granted = WarehouseRoleAssignment.objects.filter(user=approver, role="APPROVER")
    assert {"LINE-1", "FG"} <= set(granted.values_list("warehouse__code", flat=True))


@pytest.mark.django_db
def test_the_closed_order_accepts_nothing_more(seeded):
    users = {u.username: u for u in get_user_model().objects.filter(username__startswith="demo-")}
    rm_a = Warehouse.objects.get(plant=seeded.line_warehouse.plant, code="RM-A")
    attempts = (
        lambda: issue_material(
            order=seeded,
            lot=Lot.objects.get(code="L-0003"),
            source_warehouse=rm_a,
            quantity=D("1"),
            actor=users["demo-production"],
            reason="After close",
            request_id=uuid4(),
        ),
        lambda: record_output(
            order=seeded,
            lot_code="LAMP-0001",
            quantity=D("1"),
            actor=users["demo-production"],
            reason="After close",
            request_id=uuid4(),
        ),
        lambda: reverse_order_posting(
            order_posting=OrderPosting.objects.filter(order=seeded, kind="OUTPUT").first(),
            actor=users["demo-approver"],
            reason="After close",
            request_id=uuid4(),
        ),
    )
    before = counts()
    for attempt in attempts:
        with pytest.raises(MaterialValidationError):
            attempt()
    assert counts() == before
