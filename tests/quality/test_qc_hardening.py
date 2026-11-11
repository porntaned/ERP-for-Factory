# ruff: noqa: F811 (fixtures imported from sibling test modules)
"""M6.4 (Issue #113): QC commands under boundary quantities, concurrent use and audit.

Owner rulings (chat, 2026-11-11): the sample quantity is checked at its boundaries in the command
and in PostgreSQL, and an inspection racing a movement that lowers the balance never commits a
sample above the balance; races use the observed-lock helpers; every QC decision records who,
when and why and cannot be changed.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, connection, transaction

from inventory.models import StockLedgerEntry
from inventory.services import get_stock_balance
from quality.models import LotDispositionEvent, LotInspection
from quality.services import InspectionValidationError, get_lot_disposition
from tests.manufacturing.conftest import mf  # noqa: F401
from tests.manufacturing.test_material_movements import order, plant, stock  # noqa: F401
from tests.manufacturing.test_production_postings import line  # noqa: F401
from tests.quality.helpers import settle
from tests.quality.test_inspection import inspect, move, received, rows

D = Decimal

FORMAT = "sample_quantity must be a positive Decimal"
BALANCE = "exceeds the balance"


# ---------------------------------------------------------------- quantities: the command


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("sample", "message"),
    [
        ("0", FORMAT),
        ("-1", FORMAT),
        ("-0.000001", FORMAT),
        ("0.0000001", FORMAT),
        ("1.0000001", FORMAT),
        ("100000000000000", FORMAT),  # 10^14
        ("100000000000001", FORMAT),
        ("10.000001", BALANCE),  # the balance is 10
        ("11", BALANCE),
    ],
)
def test_command_refuses_sample_outside_its_bounds(line, sample, message):
    lot = received(line, "R1", "10")
    before = rows()
    with pytest.raises(InspectionValidationError, match=message):
        inspect(line, lot, quantity=sample)
    assert rows() == before
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"


@pytest.mark.django_db
@pytest.mark.parametrize("sample", ["10", "10.000000", "0.000001"])
def test_command_accepts_exactly_the_balance_and_the_smallest_sample(line, sample):
    lot = received(line, "R1", "10")
    inspection = inspect(line, lot, quantity=sample)
    assert inspection.sample_quantity == D(sample)
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "RELEASED"


# ---------------------------------------------------------------- quantities: direct SQL


def sql_inspection(mf, lot, sample):
    """INSERT one inspection row with a literal sample, past Django's field handling."""
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO quality_lotinspection "
            "(lot_id, warehouse_id, kind, result, sample_quantity, note, inspector_id) "
            "VALUES (%s, %s, 'INCOMING', 'PASS', %s::numeric, 'Direct SQL sample', %s) "
            "RETURNING id",
            [lot.pk, mf.wh["RM-A"].pk, sample, mf.qc.pk],
        )
        return cursor.fetchone()[0]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "sample",
    ["0", "-1", "-0.000001", "0.0000001", "1.0000001", "100000000000000", "100000000000001"],
)
def test_database_refuses_sample_outside_its_bounds(line, sample):
    lot = received(line, "R1", "10")
    before = rows()
    with pytest.raises(IntegrityError, match="inspection_sample_quantity_valid"):
        with transaction.atomic():
            sql_inspection(line, lot, sample)
    assert rows() == before


@pytest.mark.django_db
@pytest.mark.parametrize("sample", ["10", "0.000001", "99999999999999.999999"])
def test_database_accepts_a_sample_inside_its_bounds(line, sample):
    lot = received(line, "R1", "10")
    inspection_id = sql_inspection(line, lot, sample)
    LotDispositionEvent.objects.create(
        lot=lot,
        warehouse=line.wh["RM-A"],
        actor=line.qc,
        request_id=uuid4(),
        from_disposition="HOLD",
        to_disposition="RELEASED",
        reason="Direct SQL sample",
        inspection_id=inspection_id,
    )
    settle()  # fire the deferred pairing and origin checks now: they pass
    assert LotInspection.objects.get(pk=inspection_id).sample_quantity == D(sample)


# ---------------------------------------------------------------- quantities: balance race
# A transfer out of a HOLD pair is refused by the RELEASED gate at its source, so a transfer can
# only follow the inspection. The other order is shown with a receipt reversal, the movement that
# lowers a HOLD balance (Quality is irrelevant to it, inventory.reversals.reverse_receipt).


def balance(mf, lot, code="RM-A"):
    return get_stock_balance(lot=lot, warehouse=mf.wh[code])


@pytest.mark.django_db(transaction=True)
def test_inspection_of_the_whole_balance_then_a_transfer_out(line):
    from inventory.transfer_policy import TransferQualityError
    from tests.inventory.test_stock_receipt_concurrency import blocked_action

    lot = received(line, "R1", "10")
    ledger = StockLedgerEntry.objects.count()
    with pytest.raises(TransferQualityError, match="RELEASED"):
        move(line, lot, "RM-A", "FG", "10")  # while HOLD, the transfer cannot go first
    assert StockLedgerEntry.objects.count() == ledger

    inspection, outcome = blocked_action(
        lambda: inspect(line, lot, quantity="10"),
        lambda: move(line, lot, "RM-A", "FG", "10")[0],
    )
    assert outcome[0] == "committed", outcome
    debit = StockLedgerEntry.objects.get(pk=outcome[1])
    before_debit = StockLedgerEntry.objects.filter(
        lot=lot, warehouse=line.wh["RM-A"], pk__lt=debit.pk
    )
    # The inspection committed while the balance was still 10; the transfer waited for it.
    assert inspection.sample_quantity == sum(e.quantity_delta for e in before_debit) == D("10")
    assert inspection.created_at < debit.created_at
    assert (balance(line, lot), balance(line, lot, "FG")) == (D("0"), D("10"))
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "RELEASED"


@pytest.mark.django_db(transaction=True)
def test_balance_lowered_first_then_the_waiting_inspection_is_refused(line):
    from inventory.models import StockReceipt
    from inventory.reversals import reverse_receipt
    from tests.inventory.test_stock_receipt_concurrency import blocked_action

    lot = received(line, "R1", "10")
    receipt = StockReceipt.objects.get(ledger_entry__lot=lot)
    before = rows()
    _, outcome = blocked_action(
        lambda: reverse_receipt(
            receipt=receipt,
            actor=line.users["approver"],
            reason="Delivery keyed twice",
            request_id=uuid4(),
        ),
        lambda: inspect(line, lot, quantity="10"),
    )
    assert outcome[0] == "InspectionValidationError" and BALANCE in outcome[1], outcome
    assert rows() == before
    assert balance(line, lot) == D("0")
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"
