"""M4.3.3 policy and actual PostgreSQL serialization, without transfer posting."""

from uuid import uuid4

import pytest
from django.db import connection, transaction

from access_control.models import WarehouseRoleAssignment
from facilities.models import Organization, Plant, Warehouse
from inventory.models import Lot, StockLedgerEntry
from inventory.transfer_policy import (
    TransferQualityError,
    TransferQualityValidationError,
    require_transfer_quality,
)
from quality.models import LotDispositionEvent
from quality.services import get_lot_disposition, transition_lot_disposition

from .test_stock_receipt_concurrency import blocked_action


@pytest.fixture
def scope(ledger_scope):
    for warehouse in (ledger_scope["warehouse"], ledger_scope["other"]):
        WarehouseRoleAssignment.objects.create(
            user=ledger_scope["actor"], warehouse=warehouse, role="QUALITY"
        )
    return ledger_scope


def change(scope, warehouse, target):
    return transition_lot_disposition(
        lot=scope["lot"],
        warehouse=warehouse,
        actor=scope["actor"],
        expected_disposition=get_lot_disposition(lot=scope["lot"], warehouse=warehouse),
        target_disposition=target,
        reason="ตรวจคุณภาพจำลอง — synthetic",
        request_id=uuid4(),
    )


def check(scope, **overrides):
    return require_transfer_quality(
        **(
            dict(
                lot=scope["lot"],
                source_warehouse=scope["warehouse"],
                destination_warehouse=scope["other"],
            )
            | overrides
        )
    )


def prepare(scope, warehouse, state):
    if state != "DEFAULT":
        change(scope, warehouse, "RELEASED")
        if state == "HOLD":
            change(scope, warehouse, "HOLD")


@pytest.mark.django_db
@pytest.mark.parametrize("source", ["DEFAULT", "HOLD", "RELEASED"])
@pytest.mark.parametrize("destination", ["DEFAULT", "HOLD", "RELEASED"])
def test_quality_matrix_preserves_history_and_stock(scope, source, destination):
    prepare(scope, scope["warehouse"], source)
    prepare(scope, scope["other"], destination)
    before = list(LotDispositionEvent.objects.order_by("id").values())
    with transaction.atomic():
        if source == "RELEASED":
            state = check(scope)
            assert state.source_disposition == "RELEASED"
            assert state.destination_disposition == (
                "HOLD" if destination == "DEFAULT" else destination
            )
        else:
            with pytest.raises(TransferQualityError):
                check(scope)
    assert list(LotDispositionEvent.objects.order_by("id").values()) == before
    assert StockLedgerEntry.objects.count() == 0


@pytest.mark.django_db
def test_release_of_other_pair_does_not_release_source(scope):
    change(scope, scope["other"], "RELEASED")
    LotDispositionEvent.objects.create(
        lot=scope["second"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        from_disposition="HOLD",
        to_disposition="RELEASED",
        reason="Other lot",
        request_id=uuid4(),
    )
    with pytest.raises(TransferQualityError):
        check(scope)


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["lot", "source_warehouse", "destination_warehouse"])
@pytest.mark.parametrize("invalid", ["none", "wrong_type", "unsaved", "manual_pk", "missing"])
def test_invalid_identity_is_rejected(scope, field, invalid):
    model = Lot if field == "lot" else Warehouse
    existing = scope["lot"] if model is Lot else scope["warehouse"]
    if invalid == "none":
        value = None
    elif invalid == "wrong_type":
        value = "1"
    else:
        value = model()
        if invalid == "manual_pk":
            value.pk = existing.pk
        elif invalid == "missing":
            value.pk = 999999999
            value._state.adding = False
    with pytest.raises(TransferQualityValidationError):
        check(scope, **{field: value})


@pytest.mark.django_db
def test_same_warehouse_different_instance_is_rejected(scope):
    same = Warehouse.objects.get(pk=scope["warehouse"].pk)
    with pytest.raises(TransferQualityValidationError, match="distinct"):
        check(scope, destination_warehouse=same)


@pytest.mark.django_db
@pytest.mark.parametrize("different_org", [False, True])
def test_persisted_cross_plant_overrides_cached_relations(scope, different_org):
    org = scope["organization"]
    if different_org:
        org = Organization.objects.create(code="OTHER", display_name="Other")
    plant = Plant.objects.create(organization=org, code="OTHER", display_name="Other")
    stale = scope["other"]
    assert stale.plant.pk == scope["plant"].pk
    Warehouse.objects.filter(pk=stale.pk).update(plant=plant)
    with pytest.raises(TransferQualityValidationError, match="one Plant"):
        check(scope)


@pytest.mark.django_db
def test_persisted_item_organization_overrides_cached_relation(scope):
    org = Organization.objects.create(code="OTHER", display_name="Other")
    assert scope["lot"].item.organization_id == scope["organization"].pk
    type(scope["item"]).objects.filter(pk=scope["item"].pk).update(organization=org)
    with pytest.raises(TransferQualityValidationError, match="one organization"):
        check(scope)


@pytest.mark.django_db(transaction=True)
def test_autocommit_is_rejected(scope):
    assert not connection.in_atomic_block
    with pytest.raises(TransferQualityValidationError, match="atomic"):
        check(scope)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("level", ["REPEATABLE READ", "SERIALIZABLE"])
def test_stale_snapshot_isolation_is_rejected(scope, level):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {level}")
        with pytest.raises(TransferQualityValidationError, match="READ COMMITTED"):
            check(scope)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("quality_first", [False, True])
@pytest.mark.parametrize("at_destination", [False, True])
def test_quality_transition_and_gate_serialize_until_outer_commit(
    scope,
    quality_first,
    at_destination,
):
    change(scope, scope["warehouse"], "RELEASED")
    warehouse = scope["other"] if at_destination else scope["warehouse"]
    if at_destination:
        change(scope, warehouse, "RELEASED")

    def hold():
        return change(scope, warehouse, "HOLD")

    def gate():
        state = check(scope)
        if at_destination:
            assert state.destination_disposition == ("HOLD" if quality_first else "RELEASED")
        return scope["lot"]

    _, outcome = blocked_action(hold if quality_first else gate, gate if quality_first else hold)
    if quality_first and not at_destination:
        assert outcome[0] == "TransferQualityError", outcome
    else:
        assert outcome[0] == "committed", outcome
    assert get_lot_disposition(lot=scope["lot"], warehouse=warehouse) == "HOLD"
    assert StockLedgerEntry.objects.count() == 0
