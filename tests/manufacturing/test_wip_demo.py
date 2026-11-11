"""M6.3 (Issue #108): seed_production_demo adds one WIP level, RAW -> WIP -> FINISHED.

LED-BOARD (WIP, 4 LED-CHIP) and LAMP-BR30 (FINISHED, 1 LED-BOARD + 1 DRIVER), drafted by
demo-production and approved by demo-approver. Order A makes LED-BOARD-0001 from new chip Lot
L-0004 into FG, where demo-quality passes its FINAL inspection; order B issues it from FG with new
DRIVER Lot D-0002 and makes LAMP-BR30-0001. Real commands and existing grants only; new Lots
only, so the M4.7 and M5.4 balances stay as they were.
"""

from decimal import Decimal

import pytest
from django.core.management import call_command

from inventory.models import Lot, ProductionPosting, StockLedgerEntry
from manufacturing.genealogy import trace
from manufacturing.models import BillOfMaterials, ProductionOrder
from quality.models import LotDispositionEvent, LotInspection

from .test_production_path import stock_table

D = Decimal


@pytest.fixture
def seeded(db):
    call_command("seed_production_demo", verbosity=0)


def flat(result):
    return [(e.level, e.from_lot.code, e.to_lot.code, e.quantity, e.repeat) for e in result.edges]


def snapshot():
    return {
        "stock": stock_table(),
        "orders": list(
            ProductionOrder.objects.order_by("pk").values_list(
                "pk", "bom__item__code", "quantity", "status", "created_by__username"
            )
        ),
        "boms": list(
            BillOfMaterials.objects.order_by("pk").values_list(
                "item__code", "version", "status", "created_by__username", "approved_by__username"
            )
        ),
        "inspections": list(
            LotInspection.objects.order_by("pk").values_list(
                "lot__code", "warehouse__code", "kind", "result", "inspector__username"
            )
        ),
        "counts": [
            m.objects.count()
            for m in (StockLedgerEntry, ProductionPosting, LotInspection, LotDispositionEvent)
        ],
    }


@pytest.mark.django_db
def test_seed_adds_a_wip_bom_and_a_finished_bom_through_the_commands(seeded):
    boms = {
        bom.item.code: bom
        for bom in BillOfMaterials.objects.filter(item__code__in=("LED-BOARD", "LAMP-BR30"))
    }
    assert {code: (b.item.item_type, b.version, b.status) for code, b in boms.items()} == {
        "LED-BOARD": ("WIP", 1, "ACTIVE"),
        "LAMP-BR30": ("FINISHED", 1, "ACTIVE"),
    }
    assert dict(boms["LED-BOARD"].lines.values_list("component__code", "quantity_per")) == {
        "LED-CHIP": D("4")
    }
    assert dict(boms["LAMP-BR30"].lines.values_list("component__code", "quantity_per")) == {
        "LED-BOARD": D("1"),
        "DRIVER": D("1"),
    }
    for bom in boms.values():
        assert (bom.created_by.username, bom.approved_by.username) == (
            "demo-production",
            "demo-approver",
        )


@pytest.mark.django_db
def test_seed_runs_both_orders_and_passes_the_wip_final_inspection(seeded):
    orders = ProductionOrder.objects.filter(bom__item__code__in=("LED-BOARD", "LAMP-BR30"))
    assert sorted(orders.values_list("bom__item__code", "quantity", "status")) == [
        ("LAMP-BR30", D("5"), "CLOSED"),
        ("LED-BOARD", D("5"), "CLOSED"),
    ]
    inspection = LotInspection.objects.get(lot__code="LED-BOARD-0001")
    assert (
        inspection.warehouse.code,
        inspection.kind,
        inspection.result,
        inspection.inspector.username,
    ) == ("FG", "FINAL", "PASS", "demo-quality")


@pytest.mark.django_db
def test_trace_of_the_finished_lot_reaches_its_chip_and_driver_lots(seeded):
    lamp = Lot.objects.get(code="LAMP-BR30-0001")
    assert flat(trace(lamp, "backward")) == [
        (1, "LAMP-BR30-0001", "D-0002", D("5"), False),
        (1, "LAMP-BR30-0001", "LED-BOARD-0001", D("5"), False),
        (2, "LED-BOARD-0001", "L-0004", D("20"), False),
    ]
    assert flat(trace(Lot.objects.get(code="L-0004"), "forward")) == [
        (1, "L-0004", "LED-BOARD-0001", D("5"), False),
        (2, "LED-BOARD-0001", "LAMP-BR30-0001", D("5"), False),
    ]


@pytest.mark.django_db
def test_the_m47_and_m54_balances_are_unchanged(seeded):
    released, hold = "RELEASED", "HOLD"
    earlier = {
        ("L-0001", "RM-A"): (D("100"), released),
        ("L-0002", "RM-A"): (D("0"), released),
        ("L-0002", "LINE-1"): (D("0"), hold),
        ("L-0003", "RM-A"): (D("12"), released),
        ("L-0003", "LINE-1"): (D("0"), hold),
        ("D-0001", "RM-A"): (D("11"), released),
        ("D-0001", "LINE-1"): (D("0"), hold),
        ("LAMP-0001", "FG"): (D("5"), hold),
        ("LAMP-0002", "FG"): (D("4"), hold),
        ("LAMP-0003", "FG"): (D("0"), hold),
    }
    table = stock_table()
    assert {pair: table[pair] for pair in earlier} == earlier
    assert {pair: value for pair, value in table.items() if pair not in earlier} == {
        ("L-0004", "RM-A"): (D("10"), released),  # 30 received, 20 issued
        ("L-0004", "LINE-1"): (D("0"), hold),  # 20 consumed
        ("D-0002", "RM-A"): (D("5"), released),  # 10 received, 5 issued
        ("D-0002", "LINE-1"): (D("0"), hold),  # 5 consumed
        ("LED-BOARD-0001", "FG"): (D("0"), released),  # 5 output, FINAL PASS, 5 issued
        ("LED-BOARD-0001", "LINE-1"): (D("0"), hold),  # 5 consumed
        ("LAMP-BR30-0001", "FG"): (D("5"), hold),
    }


@pytest.mark.django_db
def test_rerun_adds_nothing(seeded):
    before = snapshot()
    call_command("seed_production_demo", verbosity=0)
    assert snapshot() == before


@pytest.mark.django_db(transaction=True)
def test_reset_gives_the_same_end_state():
    """--reset flushes and restarts the id sequences, so even the order numbers repeat."""
    call_command("seed_production_demo", reset=True, verbosity=0)
    first = snapshot()
    call_command("seed_production_demo", reset=True, verbosity=0)
    assert snapshot() == first
