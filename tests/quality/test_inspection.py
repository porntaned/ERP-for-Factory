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
    assert LotInspection.objects.count() == 1
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
    assert not LotInspection.objects.exists()


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
