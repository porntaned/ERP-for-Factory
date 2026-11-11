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


# ---------------------------------------------------------------- concurrency (two connections)


def assert_chain(mf, lot, code="RM-A"):
    """Each event starts from the state the previous one left: no two events from one state."""
    events = list(
        LotDispositionEvent.objects.filter(lot=lot, warehouse=mf.wh[code])
        .order_by("id")
        .values_list("from_disposition", "to_disposition")
    )
    state = "HOLD"
    for from_state, to_state in events:
        assert from_state == state, events
        state = to_state
    return events


@pytest.mark.django_db(transaction=True)
def test_two_returns_with_different_keys_record_one_event(line):
    from tests.inventory.test_stock_receipt_concurrency import blocked_action
    from tests.quality.test_inspection import back_to_hold

    lot = received(line)
    inspect(line, lot, result="FAIL", note="Scratched die")
    first, outcome = blocked_action(
        lambda: back_to_hold(line, lot, key=uuid4()),
        lambda: back_to_hold(line, lot, key=uuid4(), reason="Second tab"),
    )
    assert outcome[0] == "DispositionConflictError" and "expected REJECTED" in outcome[1], outcome
    assert assert_chain(line, lot) == [("HOLD", "REJECTED"), ("REJECTED", "HOLD")]
    assert LotDispositionEvent.objects.get(to_disposition="HOLD", lot=lot) == first


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("start", "first", "second", "outcome", "chain"),
    [
        (
            "REJECTED",
            "return",
            "PASS",
            "committed",
            [("HOLD", "REJECTED"), ("REJECTED", "HOLD"), ("HOLD", "RELEASED")],
        ),
        ("HOLD", "FAIL", "return", "committed", [("HOLD", "REJECTED"), ("REJECTED", "HOLD")]),
        ("HOLD", "PASS", "return", "DispositionConflictError", [("HOLD", "RELEASED")]),
    ],
)
def test_return_racing_an_inspection_keeps_the_chain(line, start, first, second, outcome, chain):
    from tests.inventory.test_stock_receipt_concurrency import blocked_action
    from tests.quality.test_inspection import back_to_hold

    lot = received(line)
    if start == "REJECTED":
        inspect(line, lot, result="FAIL", note="Scratched die")

    def action(name):
        if name == "return":
            return lambda: back_to_hold(line, lot)
        return lambda: inspect(line, lot, result=name, note=f"Racing {name}")

    _, result = blocked_action(action(first), action(second))
    assert result[0] == outcome, result
    assert assert_chain(line, lot) == chain


def revoked_while_waiting(lot, grant, action):
    """Hold the Lot lock, let `action` wait for it in a second connection, revoke `grant`."""
    from queue import Queue
    from threading import Thread

    from inventory.models import Lot
    from tests.inventory.test_stock_ledger_concurrency import wait_for_lock
    from tests.inventory.test_stock_receipt_concurrency import receipt_worker

    outcomes, pids = Queue(), Queue()
    thread = Thread(target=receipt_worker, args=(action, outcomes, pids))
    try:
        with transaction.atomic():
            Lot.objects.select_for_update().get(pk=lot.pk)
            thread.start()
            wait_for_lock(pids.get(timeout=5))
            grant.delete()
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    return outcomes.get(timeout=1)


@pytest.mark.django_db(transaction=True)
def test_quality_grant_revoked_while_inspection_waits(line):
    from access_control.models import WarehouseRoleAssignment

    lot = received(line)
    grant = WarehouseRoleAssignment.objects.get(
        user=line.qc, warehouse=line.wh["RM-A"], role="QUALITY"
    )
    before = rows()
    outcome = revoked_while_waiting(lot, grant, lambda: inspect(line, lot))
    assert outcome[0] == "DispositionAuthorizationError" and "QUALITY" in outcome[1], outcome
    assert rows() == before
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"


@pytest.mark.django_db(transaction=True)
def test_approver_grant_revoked_while_return_waits(line):
    from access_control.models import WarehouseRoleAssignment
    from tests.quality.test_inspection import back_to_hold

    lot = received(line)
    inspect(line, lot, result="FAIL", note="Scratched die")
    grant = WarehouseRoleAssignment.objects.get(
        user=line.users["approver"], warehouse=line.wh["RM-A"], role="APPROVER"
    )
    before = rows()
    outcome = revoked_while_waiting(lot, grant, lambda: back_to_hold(line, lot))
    assert outcome[0] == "DispositionAuthorizationError" and "APPROVER" in outcome[1], outcome
    assert rows() == before
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "REJECTED"


# ---------------------------------------------------------------- audit records
# Existing: event server time on a direct insert, event UPDATE of reason and DELETE
# (test_postgresql_constraints), inspection UPDATE of note and DELETE (test_inspection). Added here:
# the server time and attribution of every decision a command records, a client-supplied time,
# and UPDATE of the other audit fields.


@pytest.mark.django_db
def test_every_decision_records_actor_server_time_and_reason(line):
    from django.utils import timezone

    from tests.quality.test_inspection import back_to_hold, hold_again

    lot = received(line)
    approver = line.users["approver"]
    before = timezone.now()
    passed = inspect(line, lot, note="Visual OK — ผ่าน")
    held = hold_again(line, lot)
    failed = inspect(line, lot, result="FAIL", note="Scratched die")
    returned = back_to_hold(line, lot, reason="Supplier dispute")
    after = timezone.now()

    for inspection, note in ((passed, "Visual OK — ผ่าน"), (failed, "Scratched die")):
        inspection.refresh_from_db()
        assert (inspection.inspector, inspection.note) == (line.qc, note)
        assert timezone.is_aware(inspection.created_at)
        assert before <= inspection.created_at <= after
        assert (inspection.event.actor, inspection.event.reason) == (line.qc, note)
    for event, actor, reason in (
        (passed.event, line.qc, "Visual OK — ผ่าน"),
        (held, line.qc, "Containment"),
        (failed.event, line.qc, "Scratched die"),
        (returned, approver, "Supplier dispute"),
    ):
        event.refresh_from_db()
        assert (event.actor, event.reason) == (actor, reason)
        assert before <= event.created_at <= after
    assert (held.inspection, returned.inspection) == (None, None)
    assert passed.created_at <= passed.event.created_at <= held.created_at


@pytest.mark.django_db
def test_direct_insert_cannot_choose_its_time(line):
    from datetime import UTC, datetime

    from django.utils import timezone

    lot = received(line)
    past = datetime(2000, 1, 1, tzinfo=UTC)
    before = timezone.now()
    inspection = LotInspection.objects.create(
        lot=lot,
        warehouse=line.wh["RM-A"],
        kind="INCOMING",
        result="PASS",
        sample_quantity=D("1"),
        note="Backdated",
        inspector=line.qc,
        created_at=past,
    )
    event = LotDispositionEvent.objects.create(
        lot=lot,
        warehouse=line.wh["RM-A"],
        actor=line.qc,
        request_id=uuid4(),
        from_disposition="HOLD",
        to_disposition="RELEASED",
        reason="Backdated",
        inspection=inspection,
        created_at=past,
    )
    settle()
    for record in (inspection, event):
        record.refresh_from_db()
        assert record.created_at >= before


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        ("inspection", "inspector_id", "other"),
        ("inspection", "created_at", "past"),
        ("inspection", "result", "FAIL"),
        ("inspection", "sample_quantity", D("2")),
        ("event", "actor_id", "other"),
        ("event", "created_at", "past"),
        ("event", "to_disposition", "REJECTED"),
        ("event", "inspection_id", None),
    ],
)
def test_recorded_decision_cannot_be_rewritten(line, model, field, value):
    from datetime import UTC, datetime

    lot = received(line)
    inspection = inspect(line, lot)
    record = inspection if model == "inspection" else inspection.event
    value = {
        "other": line.users["approver"].pk,
        "past": datetime(2000, 1, 1, tzinfo=UTC),
    }.get(value, value)
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        type(record).objects.filter(pk=record.pk).update(**{field: value})
    original = getattr(record, field)
    record.refresh_from_db()
    assert getattr(record, field) == original
