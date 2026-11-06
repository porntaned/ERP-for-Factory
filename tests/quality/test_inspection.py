# ruff: noqa: F811 (fixtures imported from sibling test modules)
"""M6.1 (Issue #96): inspection is the only way out of HOLD.

Owner rulings (2026-11-06): QUALITY at the warehouse inspects and decides in one command,
PASS -> RELEASED and FAIL -> REJECTED; kind comes from the Lot's origin (an OUTPUT posting makes
it FINAL, otherwise a receipt makes it INCOMING); the sample may not exceed the balance there;
the note is required.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from access_control.models import WarehouseRoleAssignment
from inventory.models import Lot
from inventory.services import receive_stock
from quality.models import LotDispositionEvent, LotInspection
from quality.services import (
    DispositionAuthorizationError,
    DispositionConflictError,
    InspectionConflictError,
    InspectionValidationError,
    get_lot_disposition,
    record_inspection,
)
from tests.manufacturing.conftest import mf  # noqa: F401
from tests.manufacturing.test_material_movements import (  # noqa: F401
    order,
    plant,
    stock,
)
from tests.manufacturing.test_production_postings import consume, line, output  # noqa: F401

D = Decimal


def inspect(
    mf,
    lot,
    *,
    warehouse="RM-A",
    result="PASS",
    quantity="1",
    note="Visual OK",
    actor=None,
    key=None,
):
    return record_inspection(
        lot=lot,
        warehouse=mf.wh[warehouse],
        result=result,
        sample_quantity=D(quantity),
        note=note,
        actor=actor or mf.qc,
        request_id=key or uuid4(),
    )


def received(mf, code="R1", quantity="10", warehouse="RM-A"):
    """A receipt Lot left on HOLD."""
    return stock(mf, code, D(quantity), warehouse=warehouse, release=False)


def made(mf, quantity="5"):
    """An output Lot at FG, on HOLD."""
    consume(mf, "40")
    return output(mf, quantity).posting.ledger_entry.lot


def rows():
    return LotInspection.objects.count(), LotDispositionEvent.objects.count()


@pytest.mark.django_db
def test_pass_releases_and_fail_rejects(line):
    good, bad = received(line, "R1"), received(line, "R2")
    passed = inspect(line, good)
    assert get_lot_disposition(lot=good, warehouse=line.wh["RM-A"]) == "RELEASED"
    event = LotDispositionEvent.objects.get(inspection=passed)
    assert (event.from_disposition, event.to_disposition, event.actor) == (
        "HOLD",
        "RELEASED",
        line.qc,
    )
    assert (passed.kind, passed.result, passed.inspector) == ("INCOMING", "PASS", line.qc)
    failed = inspect(line, bad, result="FAIL", note="Scratched die")
    assert get_lot_disposition(lot=bad, warehouse=line.wh["RM-A"]) == "REJECTED"
    assert failed.event.to_disposition == "REJECTED"


@pytest.mark.django_db
def test_kind_is_final_for_output_lot_and_mixed_lot(line):
    lamp = made(line)
    assert inspect(line, lamp, warehouse="FG").kind == "FINAL"
    # A later receipt into the output Lot's code does not make it INCOMING.
    receive_stock(
        lot=lamp,
        warehouse=line.wh["RM-A"],
        actor=line.staff,
        quantity=D("2"),
        reason="Synthetic receipt",
        request_id=uuid4(),
    )
    assert inspect(line, lamp, warehouse="RM-A").kind == "FINAL"


@pytest.mark.django_db
def test_lot_without_origin_is_refused(line):
    bare = Lot.objects.create(item=line.items["chip"], code="BARE")
    before = rows()
    with pytest.raises(InspectionValidationError, match="origin"):
        inspect(line, bare, quantity="1")
    assert rows() == before


@pytest.mark.django_db
@pytest.mark.parametrize(
    "change",
    [
        {"result": "MAYBE"},
        {"quantity": "0"},
        {"quantity": "-1"},
        {"quantity": "1.0000001"},
        {"quantity": "11"},
        {"note": ""},
        {"note": "  "},
        {"key": "x"},
    ],
)
def test_refusals_write_nothing(line, change):
    lot = received(line)
    before = rows()
    with pytest.raises(InspectionValidationError):
        inspect(line, lot, **change)
    assert rows() == before
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"


@pytest.mark.django_db
def test_only_a_hold_lot_can_be_inspected(line):
    lot = received(line)
    inspect(line, lot)
    before = rows()
    with pytest.raises(InspectionConflictError, match="HOLD"):
        inspect(line, lot)
    assert rows() == before


@pytest.mark.django_db
def test_quality_at_this_warehouse_is_required(line):
    lot = received(line)
    elsewhere = get_user_model().objects.create(username="qc-elsewhere")
    WarehouseRoleAssignment.objects.create(user=elsewhere, warehouse=line.wh["FG"], role="QUALITY")
    retired = get_user_model().objects.create(username="qc-retired", is_active=False)
    WarehouseRoleAssignment.objects.create(user=retired, warehouse=line.wh["RM-A"], role="QUALITY")
    for actor in (line.users["approver"], elsewhere, retired):
        with pytest.raises(DispositionAuthorizationError):
            inspect(line, lot, actor=actor)
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"


@pytest.mark.django_db
def test_replay_and_conflicts(line):
    lot = received(line)
    key = uuid4()
    first = inspect(line, lot, key=key)
    assert inspect(line, lot, key=key) == first
    assert LotInspection.objects.filter(lot=lot).count() == 1
    with pytest.raises(InspectionConflictError):
        inspect(line, lot, key=key, note="Another note")
    receipt_key = uuid4()
    receive_stock(
        lot=lot,
        warehouse=line.wh["RM-A"],
        actor=line.staff,
        quantity=D("1"),
        reason="Synthetic receipt",
        request_id=receipt_key,
    )
    other = received(line, "R2")
    with pytest.raises(InspectionConflictError):
        inspect(line, other, key=receipt_key)


# ---------------------------------------------------------------- database


def raw_inspection(mf, lot, **fields):
    values = {
        "lot": lot,
        "warehouse": mf.wh["RM-A"],
        "kind": "INCOMING",
        "result": "PASS",
        "sample_quantity": D("1"),
        "note": "Raw",
        "inspector": mf.qc,
    } | fields
    return LotInspection.objects.create(**values)


@pytest.mark.django_db(transaction=True)
def test_orphan_inspection_fails_at_commit(line):
    lot = received(line)
    with pytest.raises(IntegrityError, match="linked by its disposition event"):
        with transaction.atomic():
            raw_inspection(line, lot)
    assert not LotInspection.objects.filter(lot=lot).exists()


@pytest.mark.django_db
def test_database_refuses_wrong_kind_blank_note_and_mutation(line):
    lot = received(line)
    for fields, message in (
        ({"kind": "FINAL"}, "does not match the Lot origin"),
        ({"note": " "}, "inspection_note_nonblank"),
        ({"sample_quantity": D("0")}, "inspection_sample_quantity_valid"),
        ({"sample_quantity": D("1.0000001")}, "inspection_sample_quantity_valid"),
    ):
        with pytest.raises(IntegrityError, match=message), transaction.atomic():
            raw_inspection(line, lot, **fields)
    real = inspect(line, lot)
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        LotInspection.objects.filter(pk=real.pk).update(note="Rewritten")
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        with connection.cursor() as cursor:  # past Django's PROTECT, to reach the trigger
            cursor.execute("DELETE FROM quality_lotinspection WHERE id = %s", [real.pk])


@pytest.mark.django_db(transaction=True)
def test_inspection_migration_unapplies_and_reapplies():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("quality", "0005_register_key_after_validation")])
    finally:
        MigrationExecutor(connection).migrate(latest)
    assert LotInspection.objects.count() == 0


# ---------------------------------------------------------------- review focus (plan)


@pytest.mark.django_db
def test_transferred_lot_is_inspected_at_destination_with_origin_kind(line):
    from inventory.transfers import transfer_stock

    lot = received(line, "R1", "10")
    inspect(line, lot)
    transfer_stock(
        lot=lot,
        source_warehouse=line.wh["RM-A"],
        destination_warehouse=line.wh["FG"],
        actor=line.staff,
        quantity=D("3"),
        reason="Synthetic move",
        request_id=uuid4(),
    )
    assert get_lot_disposition(lot=lot, warehouse=line.wh["FG"]) == "HOLD"
    with pytest.raises(InspectionValidationError, match="balance"):
        inspect(line, lot, warehouse="FG", quantity="4")
    there = inspect(line, lot, warehouse="FG", quantity="3")
    assert (there.kind, there.warehouse) == ("INCOMING", line.wh["FG"])
    assert get_lot_disposition(lot=lot, warehouse=line.wh["FG"]) == "RELEASED"


@pytest.mark.django_db(transaction=True)
def test_concurrent_inspections_one_wins(line):
    from tests.inventory.test_stock_receipt_concurrency import blocked_action

    lot = received(line)
    first, outcome = blocked_action(
        lambda: inspect(line, lot, note="First"),
        lambda: inspect(line, lot, note="Second"),
    )
    assert outcome[0] == "InspectionConflictError", outcome
    assert list(LotInspection.objects.filter(lot=lot).values_list("note", flat=True)) == ["First"]
    assert first.event.to_disposition == "RELEASED"


# ---------------------------------------------------------------- Task 3: only inspection leaves HOLD


def hold_again(mf, lot, *, expected="RELEASED", target="HOLD", key=None, actor=None):
    from quality.services import transition_lot_disposition

    return transition_lot_disposition(
        lot=lot,
        warehouse=mf.wh["RM-A"],
        actor=actor or mf.qc,
        expected_disposition=expected,
        target_disposition=target,
        reason="Containment",
        request_id=key or uuid4(),
    )


def back_to_hold(mf, lot, *, actor=None, reason="Re-inspect after supplier dispute", key=None):
    from quality.services import return_rejected_to_hold

    return return_rejected_to_hold(
        lot=lot,
        warehouse=mf.wh["RM-A"],
        actor=actor or mf.users["approver"],
        reason=reason,
        request_id=key or uuid4(),
    )


@pytest.mark.django_db
@pytest.mark.parametrize("target", ["RELEASED", "REJECTED"])
def test_transition_cannot_leave_hold(line, target):
    from quality.services import DispositionValidationError

    lot = received(line)
    with pytest.raises(DispositionValidationError, match="record_inspection"):
        hold_again(line, lot, expected="HOLD", target=target)
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"


@pytest.mark.django_db
def test_transition_still_holds_a_released_lot(line):
    lot = received(line)
    inspect(line, lot)
    event = hold_again(line, lot)
    assert (event.from_disposition, event.to_disposition, event.inspection) == (
        "RELEASED",
        "HOLD",
        None,
    )


@pytest.mark.django_db
def test_transition_cannot_move_a_rejected_lot(line):
    from quality.services import DispositionValidationError

    lot = received(line)
    inspect(line, lot, result="FAIL")
    with pytest.raises(DispositionValidationError, match="return_rejected_to_hold"):
        hold_again(line, lot, expected="REJECTED")


@pytest.mark.django_db
def test_approver_returns_rejected_to_hold(line):
    lot = received(line)
    inspect(line, lot, result="FAIL")
    event = back_to_hold(line, lot)
    assert (event.from_disposition, event.to_disposition) == ("REJECTED", "HOLD")
    assert (event.actor, event.reason, event.inspection) == (
        line.users["approver"],
        "Re-inspect after supplier dispute",
        None,
    )
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "HOLD"


@pytest.mark.django_db
def test_inspector_cannot_return_even_as_approver(line):
    lot = received(line)
    WarehouseRoleAssignment.objects.create(user=line.qc, warehouse=line.wh["RM-A"], role="APPROVER")
    inspect(line, lot, result="FAIL")
    with pytest.raises(DispositionAuthorizationError, match="inspector"):
        back_to_hold(line, lot, actor=line.qc)
    with pytest.raises(IntegrityError, match="inspector"), transaction.atomic():
        LotDispositionEvent.objects.create(
            lot=lot,
            warehouse=line.wh["RM-A"],
            actor=line.qc,
            request_id=uuid4(),
            from_disposition="REJECTED",
            to_disposition="HOLD",
            reason="Raw return",
        )
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "REJECTED"


@pytest.mark.django_db
def test_quality_only_cannot_return(line):
    other_qc = get_user_model().objects.create(username="qc-two")
    WarehouseRoleAssignment.objects.create(user=other_qc, warehouse=line.wh["RM-A"], role="QUALITY")
    lot = received(line)
    inspect(line, lot, result="FAIL")
    with pytest.raises(DispositionAuthorizationError):
        back_to_hold(line, lot, actor=other_qc)
    with pytest.raises(IntegrityError, match="APPROVER"), transaction.atomic():
        LotDispositionEvent.objects.create(
            lot=lot,
            warehouse=line.wh["RM-A"],
            actor=other_qc,
            request_id=uuid4(),
            from_disposition="REJECTED",
            to_disposition="HOLD",
            reason="Raw return",
        )


@pytest.mark.django_db
def test_return_refusals(line):
    from quality.services import DispositionValidationError

    lot = received(line)
    with pytest.raises(DispositionConflictError, match="REJECTED"):
        back_to_hold(line, lot)  # still HOLD
    inspect(line, lot, result="FAIL")
    with pytest.raises(DispositionValidationError):
        back_to_hold(line, lot, reason="  ")


@pytest.mark.django_db
def test_reject_return_then_pass_releases(line):
    lot = received(line)
    inspect(line, lot, result="FAIL", note="Scratched die")
    back_to_hold(line, lot)
    inspect(line, lot, result="PASS", note="Reworked and re-inspected")
    assert get_lot_disposition(lot=lot, warehouse=line.wh["RM-A"]) == "RELEASED"
    events = LotDispositionEvent.objects.filter(lot=lot).order_by("id")
    assert [(e.from_disposition, e.to_disposition) for e in events] == [
        ("HOLD", "REJECTED"),
        ("REJECTED", "HOLD"),
        ("HOLD", "RELEASED"),
    ]


@pytest.mark.django_db
def test_return_replay_and_conflict(line):
    lot = received(line)
    inspect(line, lot, result="FAIL")
    key = uuid4()
    first = back_to_hold(line, lot, key=key)
    assert back_to_hold(line, lot, key=key) == first
    with pytest.raises(DispositionConflictError):
        back_to_hold(line, lot, key=key, reason="Another reason")


@pytest.mark.django_db
def test_database_refuses_leaving_hold_without_matching_inspection(line):
    lot, other = received(line, "R1"), received(line, "R2")

    def event(**fields):
        values = {
            "lot": lot,
            "warehouse": line.wh["RM-A"],
            "actor": line.qc,
            "request_id": uuid4(),
            "from_disposition": "HOLD",
            "to_disposition": "RELEASED",
            "reason": "Raw",
        } | fields
        return LotDispositionEvent.objects.create(**values)

    with pytest.raises(IntegrityError, match="inspection"), transaction.atomic():
        event()  # no inspection
    for to, result, target_lot in (
        ("RELEASED", "FAIL", lot),  # result does not match
        ("REJECTED", "PASS", lot),
        ("RELEASED", "PASS", other),  # inspection of another Lot
    ):
        with pytest.raises(IntegrityError, match="inspection"), transaction.atomic():
            found = raw_inspection(line, target_lot, result=result)
            event(to_disposition=to, inspection=found)
    inspect(line, lot)
    released = LotDispositionEvent.objects.get(lot=lot, to_disposition="RELEASED").inspection
    with pytest.raises(IntegrityError, match="inspection"), transaction.atomic():
        event(from_disposition="RELEASED", to_disposition="HOLD", inspection=released)


@pytest.mark.django_db(transaction=True)
def test_transition_rules_migration_unapplies_and_reapplies():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("quality", "0006_lot_inspection")])
    finally:
        MigrationExecutor(connection).migrate(latest)


# ---------------------------------------------------------------- Task 4: REJECTED is blocked
# No Inventory or Manufacturing code changes: their gates already require RELEASED at the
# side the goods leave from, so a REJECTED Lot-Warehouse is refused there. These tests guard it.


def move(mf, lot, source, destination, quantity, actor=None):
    from inventory.transfers import transfer_stock

    return transfer_stock(
        lot=lot,
        source_warehouse=mf.wh[source],
        destination_warehouse=mf.wh[destination],
        actor=actor or mf.staff,
        quantity=D(quantity),
        reason="Synthetic move",
        request_id=uuid4(),
    )


def ledger_rows():
    from inventory.models import StockLedgerEntry, StockTransfer

    return StockLedgerEntry.objects.count(), StockTransfer.objects.count()


@pytest.mark.django_db
def test_rejected_lot_cannot_be_transferred(line):
    from inventory.transfer_policy import TransferQualityError

    lot = received(line)
    inspect(line, lot, result="FAIL", note="Scratched die")
    before = ledger_rows()
    with pytest.raises(TransferQualityError, match="RELEASED"):
        move(line, lot, "RM-A", "FG", "1")
    assert ledger_rows() == before


@pytest.mark.django_db
def test_rejected_lot_cannot_be_issued_to_production(
    plant,
):  # nothing issued yet, so only Quality can refuse
    from manufacturing.models import ProductionMaterialMovement
    from manufacturing.services import MaterialQualityError
    from tests.manufacturing.test_material_movements import issue

    lot = received(plant, "R1", "10")
    inspect(plant, lot, result="FAIL", note="Wrong bin")
    before = (ledger_rows(), ProductionMaterialMovement.objects.count())
    with pytest.raises(MaterialQualityError):
        issue(plant, "1", lot=lot)
    assert (ledger_rows(), ProductionMaterialMovement.objects.count()) == before


@pytest.mark.django_db
def test_rejected_destination_blocks_transfer_reversal(line):
    from inventory.reversals import ReversalQualityError, reverse_transfer

    lot = received(line, "R1", "10")
    inspect(line, lot)
    _, credit = move(line, lot, "RM-A", "FG", "3")
    inspect(line, lot, warehouse="FG", result="FAIL", quantity="3", note="Damaged in transit")
    approver = get_user_model().objects.create(username="approver-both")
    for code in ("RM-A", "FG"):
        WarehouseRoleAssignment.objects.create(
            user=approver, warehouse=line.wh[code], role="APPROVER"
        )
    from inventory.models import StockTransfer

    transfer = StockTransfer.objects.get(destination_entry=credit)
    before = ledger_rows()
    with pytest.raises(ReversalQualityError, match="RELEASED"):
        reverse_transfer(
            transfer=transfer, actor=approver, reason="Return to stores", request_id=uuid4()
        )
    assert ledger_rows() == before
